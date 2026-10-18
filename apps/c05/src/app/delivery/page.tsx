"use client";

import { useState } from "react";
import { c05 } from "@/lib/c05-client";
import type { Role } from "@/lib/c05-types";
import { useSession } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const MAX_BYTES = 4 * 1024 * 1024;

export default function DeliveryPage() {
  const { role, kitchenId } = useSession();
  const [inspectionId, setInspectionId] = useState("");
  const [file, setFile] = useState<{ mime: string; b64: string; width: number; height: number; size: number } | null>(null);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  function onPick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    if (!picked) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result);
      const img = new Image();
      img.onload = () => {
        if (picked.size > MAX_BYTES) {
          setMessage("Image is too large.");
          return;
        }
        setFile({
          mime: picked.type,
          b64: dataUrl.split(",")[1] ?? "",
          width: img.naturalWidth,
          height: img.naturalHeight,
          size: picked.size,
        });
        setMessage("");
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(picked);
  }

  async function submit() {
    if (!file || !inspectionId.trim()) {
      setMessage("Inspection ID and image are required.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const created = await c05.createDeliveryVerification({
        role,
        kitchen_id: kitchenId,
        inspection_id: inspectionId.trim(),
        mime_type: file.mime,
        data_base64: file.b64,
        idempotency_key: crypto.randomUUID(),
      });
      setResult(created);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
      <h1 className="text-2xl font-semibold">Student delivery verification</h1>
      <p className="text-sm text-muted-foreground">
        Scoped to kitchen <span className="font-mono font-semibold">{kitchenId}</span>. Capture or upload
        the meal you received. Visual comparison only — this is not proof of food safety.
      </p>
      <p className="text-xs text-muted-foreground">
        Demo role switch: no authentication is implemented. Role and kitchen are in-app demo state.
      </p>

      <div className="flex flex-col gap-2">
        <Label htmlFor="inspection-id">Approved inspection ID</Label>
        <Input
          id="inspection-id"
          value={inspectionId}
          onChange={(e) => setInspectionId(e.target.value)}
          placeholder="Paste inspection ID from kitchen"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="delivery-image">Received meal photo</Label>
        <Input id="delivery-image" type="file" accept="image/jpeg,image/png" onChange={onPick} />
      </div>

      {file ? (
        <img
          src={`data:${file.mime};base64,${file.b64}`}
          alt="Received meal preview"
          className="w-full rounded border"
        />
      ) : null}

      {message ? <p className="text-sm text-red-600">{message}</p> : null}

      <Button type="button" onClick={submit} disabled={busy || !file || !inspectionId.trim()}>
        {busy ? "Verifying..." : "Submit for AI scoring"}
      </Button>

      {result ? (
        <div className="rounded border p-4">
          <p className="font-medium">Delivery verification result</p>
          <p className="text-sm">Status: {String(result.status)}</p>
          <p className="text-sm">Visual score: {String(result.visual_score)}</p>
          <p className="text-sm">Quality alert: {String(result.quality_alert)}</p>
          {Array.isArray(result.quality_alert_reasons) && result.quality_alert_reasons.length ? (
            <p className="text-sm text-red-600">
              Reasons: {result.quality_alert_reasons.join(", ")}
            </p>
          ) : null}
          <p className="text-sm">QC quality: {JSON.stringify(result.qc_quality)}</p>
          <p className="text-sm">Student quality: {JSON.stringify(result.student_quality)}</p>
          <p className="text-sm">Verification ID: {String(result.verification_id)}</p>
        </div>
      ) : null}
    </div>
  );
}