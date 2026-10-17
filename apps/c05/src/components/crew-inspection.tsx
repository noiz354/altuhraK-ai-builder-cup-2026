"use client";

import { useEffect, useRef, useState } from "react";
import { SAMPLE_PHOTOS } from "@/components/photo-guide";
import { c05 } from "@/lib/c05-client";
import type { AuditEvent, Inspection, Manifest, Role } from "@/lib/c05-types";
import { ExecutionBadge, PredictionBlock } from "@/components/c05-status";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const MAX_BYTES = 4 * 1024 * 1024;
const MIN_HEIGHT = 240;
const MIN_WIDTH = 320;

function humanBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

type Stage = "idle" | "capturing" | "submitting" | "running" | "done" | "error";

export function CrewInspection({ role, kitchenId }: { role: Role; kitchenId: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [shift, setShift] = useState("SHIFT-AM");
  const [batch, setBatch] = useState("BATCH-DEMO");
  const [file, setFile] = useState<{ name: string; mime: string; b64: string; width: number; height: number; size: number } | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [message, setMessage] = useState("");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [camera, setCamera] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  // Stable per mounted screen; created lazily on the client so SSR prerender stays deterministic.
  const idempotencyKeyRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    c05
      .manifest(role)
      .then((r) => setManifest(r.manifests[0] ?? null))
      .catch((e: Error) => setMessage(e.message));
    // Release the camera on unmount; no state update is needed then.
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
  }, [role]);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCamera(false);
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCamera(true);
      setStage("capturing");
      setMessage("");
    } catch {
      setMessage("Camera unavailable. Use the file picker instead.");
      setStage("idle");
      fileInputRef.current?.click();
    }
  }

  function grabFrame() {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const url = canvas.toDataURL("image/jpeg", 0.9);
    adopt({
      name: "capture.jpg",
      mime: "image/jpeg",
      b64: url.split(",")[1] ?? "",
      width: canvas.width,
      height: canvas.height,
      size: Math.floor((url.length - url.indexOf(",") - 1) * 0.75),
    });
    stopCamera();
  }

  function adopt(input: { name: string; mime: string; b64: string; width: number; height: number; size: number }) {
    if (!input.mime.startsWith("image/")) {
      setMessage("Only JPEG or PNG is accepted.");
      setStage("error");
      return;
    }
    if (input.size > MAX_BYTES) {
      setMessage(`Image is ${humanBytes(input.size)}. The limit is 4 MiB.`);
      setStage("error");
      return;
    }
    if (input.width < MIN_WIDTH || input.height < MIN_HEIGHT) {
      setMessage(
        `Image is ${input.width}x${input.height}. Minimum is ${MIN_WIDTH}x${MIN_HEIGHT} so findings stay reviewable.`,
      );
      setStage("error");
      return;
    }
    setFile(input);
    setStage("idle");
    setMessage("");
  }

  function onPick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    if (!picked) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result);
      const img = new Image();
      img.onload = () =>
        adopt({
          name: picked.name,
          mime: picked.type,
          b64: dataUrl.split(",")[1] ?? "",
          width: img.naturalWidth,
          height: img.naturalHeight,
          size: picked.size,
        });
      img.onerror = () => {
        setMessage("That file could not be decoded as an image.");
        setStage("error");
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(picked);
  }

  // Prototype helper: load one of the example photos as if it had been captured.
  async function loadSample(src: string, name: string) {
    try {
      const blob = await (await fetch(src)).blob();
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
      const img = new Image();
      img.onload = () =>
        adopt({
          name: `${name}.jpg`,
          mime: blob.type || "image/jpeg",
          b64: dataUrl.split(",")[1] ?? "",
          width: img.naturalWidth,
          height: img.naturalHeight,
          size: blob.size,
        });
      img.src = dataUrl;
    } catch {
      setMessage("The sample photo could not be loaded.");
    }
  }

  async function submit() {
    if (!file || !manifest) return;
    idempotencyKeyRef.current ??=
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `key-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setStage("submitting");
    setMessage("");
    try {
      const created = await c05.createInspection({
        role,
        kitchen_id: kitchenId,
        shift_id: shift,
        batch_id: batch,
        manifest_version: manifest.version,
        mime_type: file.mime,
        data_base64: file.b64,
        idempotency_key: idempotencyKeyRef.current,
      });
      setStage("running");
      const result = await c05.run(created.inspection_id, role, "ai");
      setInspection(result);
      setStage("done");
      try {
        const detail = await c05.inspection(result.inspection_id, role);
        setAuditEvents(detail.audit ?? []);
      } catch {
        setAuditEvents([]);
      }
    } catch (e) {
      setMessage((e as Error).message);
      setStage("error");
    }
  }

  const busy = stage === "submitting" || stage === "running";

  return (
    <div className="flex flex-col gap-4 pb-24">
      <section className="panel p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-[20px] leading-[26px] font-semibold">New inspection</h2>
          <Badge variant="outline" className="font-mono">
            {manifest?.manifest_id ?? "—"}
          </Badge>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="shift">Shift</Label>
            <Select value={shift} onValueChange={(v) => setShift(v ?? "SHIFT-AM")}>
              <SelectTrigger id="shift" className="h-12 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SHIFT-AM">Morning shift</SelectItem>
                <SelectItem value="SHIFT-PM">Afternoon shift</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="batch">Production batch</Label>
            <Select value={batch} onValueChange={(v) => setBatch(v ?? "BATCH-DEMO")}>
              <SelectTrigger id="batch" className="h-12 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BATCH-DEMO">BATCH-DEMO</SelectItem>
                <SelectItem value="BATCH-002">BATCH-002</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="mt-4">
          <p className="label">Expected meal components</p>
          <ul className="mt-2 grid gap-1.5">
            {(manifest?.components ?? []).map((c) => (
              <li key={c.key} className="well flex items-center gap-2 px-3 py-2 text-[15px]">
                <span aria-hidden className="size-1.5 rounded-full bg-[var(--brand)]" />
                {c.label}
              </li>
            ))}
            {!manifest ? <li className="meta">Loading manifest…</li> : null}
          </ul>
          <p className="meta mt-2">{manifest?.note}</p>
        </div>
      </section>

      <section className="panel p-4">
        <h3 className="label">1 · Capture</h3>
        <p className="mt-1 text-[13px] leading-[18px] text-[var(--ink-2)]">
          Whole tray in frame, good light, nothing covering the food.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          onChange={onPick}
          className="sr-only"
          aria-label="Upload meal photo"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button type="button" onClick={startCamera} disabled={camera} className="h-12 px-5">
            Open camera
          </Button>
          <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()} className="h-12 px-5">
            Choose file
          </Button>
        </div>

        <div className="mt-3">
          <p className="meta">No camera nearby? Try a sample photo:</p>
          <div className="mt-1.5 grid grid-cols-3 gap-2">
            {SAMPLE_PHOTOS.map((s) => (
              <button
                key={s.src}
                type="button"
                onClick={() => void loadSample(s.src, s.name)}
                className="flex flex-col gap-1 rounded-[var(--r-control)] border border-[var(--hairline)] p-1.5 text-left hover:bg-[var(--sunken)]"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={s.src} alt="" className="aspect-[4/3] w-full rounded-[4px] object-cover" />
                <span className="text-[12px] leading-[16px] font-medium">{s.name}</span>
              </button>
            ))}
          </div>
        </div>

        {camera ? (
          <div className="mt-3 flex flex-col gap-2">
            <video ref={videoRef} playsInline muted className="w-full rounded-[var(--r-control)]" />
            <div className="flex gap-2">
              <Button type="button" onClick={grabFrame} className="h-12 flex-1">
                Capture frame
              </Button>
              <Button type="button" variant="outline" onClick={stopCamera} className="h-12">
                Cancel
              </Button>
            </div>
          </div>
        ) : null}

        {file ? (
          <div className="mt-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:${file.mime};base64,${file.b64}`}
              alt="Captured meal preview"
              className="w-full rounded-[var(--r-control)] border border-[var(--hairline)]"
            />
            <p className="meta mt-2">
              {file.name} · {file.width}x{file.height} · {humanBytes(file.size)} (limit 4 MiB)
            </p>
          </div>
        ) : null}
      </section>

      <section className="panel p-4">
        <h3 className="label">2 · Run the check</h3>
        <p className="meta mt-1">The tray is compared with today&rsquo;s meal list. A supervisor confirms every result.</p>
        <Button type="button" onClick={submit} disabled={!file || !manifest || busy} className="mt-3 h-12 w-full">
          {stage === "running" ? "Inspecting…" : stage === "submitting" ? "Uploading…" : "Run inspection"}
        </Button>
        <div aria-live="polite" className="mt-2">
          {message ? (
            <Alert variant="destructive">
              <AlertTitle>Cannot continue</AlertTitle>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          ) : null}
        </div>
      </section>

      {inspection ? (
        <section className="panel p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="label">3 · Result</h3>
            <ExecutionBadge status={inspection.execution_status} />
          </div>
          <Tabs defaultValue="finding" className="mt-3">
            <TabsList>
              <TabsTrigger value="finding">Finding</TabsTrigger>
              <TabsTrigger value="evidence">Evidence</TabsTrigger>
              <TabsTrigger value="audit">Audit</TabsTrigger>
            </TabsList>
            <TabsContent value="finding" className="mt-3">
              <PredictionBlock
                label={inspection.prediction?.predicted_label ?? null}
                regions={inspection.prediction?.regions ?? []}
                evidenceIds={inspection.evidence_ids}
              />
              {inspection.execution_status === "FAILED" ? (
                <Alert variant="destructive" className="mt-3">
                  <AlertTitle>The check could not finish</AlertTitle>
                  <AlertDescription>
                    This inspection stays unverified. Retake the photo or check the tray by hand.
                  </AlertDescription>
                </Alert>
              ) : null}
            </TabsContent>
            <TabsContent value="evidence" className="mt-3">
              <ul className="mono space-y-1 break-all">
                <li>image_sha256: {inspection.image_sha256}</li>
                <li>analysis_sha256: {inspection.analysis_sha256}</li>
                <li>manifest: {inspection.manifest_id} v{inspection.manifest_version}</li>
                <li>schema: {inspection.schema_version}</li>
              </ul>
            </TabsContent>
            <TabsContent value="audit" className="mt-3">
              <ul className="space-y-1">
                {auditEvents.map((e) => (
                  <li key={e.seq} className="meta">
                    #{e.seq} {e.event}
                  </li>
                ))}
              </ul>
            </TabsContent>
          </Tabs>
        </section>
      ) : null}
    </div>
  );
}