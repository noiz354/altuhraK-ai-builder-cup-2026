"use client";

import { useState } from "react";
import { c05, C05Error } from "@/lib/c05-client";
import type { ReporterType, Symptom } from "@/lib/c05-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const SYMPTOMS: Array<{ key: Symptom; label: string }> = [
  { key: "nausea", label: "Nausea" },
  { key: "vomiting", label: "Vomiting" },
  { key: "diarrhea", label: "Diarrhea" },
  { key: "abdominal_pain", label: "Stomach pain" },
  { key: "fever", label: "Fever" },
  { key: "headache", label: "Headache" },
  { key: "dizziness", label: "Dizziness" },
  { key: "other", label: "Other" },
];

const REPORTERS: Array<{ key: ReporterType; label: string }> = [
  { key: "parent", label: "Parent / guardian" },
  { key: "student", label: "Student" },
  { key: "teacher", label: "Teacher" },
  { key: "school_staff", label: "School staff" },
  { key: "health_worker", label: "Health worker" },
  { key: "other", label: "Other" },
];

const MAX_PHOTO = 1_500_000;

const fieldClass =
  "h-11 rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-3 text-[15px]";

export function ClaimReportForm() {
  const [kitchenId, setKitchenId] = useState("KITCHEN-A");
  const [schoolId, setSchoolId] = useState("");
  const [mealDate, setMealDate] = useState("");
  const [reporter, setReporter] = useState<ReporterType>("parent");
  const [contact, setContact] = useState("");
  const [affected, setAffected] = useState(1);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [onset, setOnset] = useState("");
  const [medical, setMedical] = useState(false);
  const [hospital, setHospital] = useState(false);
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<{ name: string; b64: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<{ claim_id: string; message: string } | null>(null);

  // Prototype helper: a realistic report, so the form can be tried end to end.
  function fillExample() {
    const pad = (n: number) => String(n).padStart(2, "0");
    const d = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const day = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    setKitchenId("KITCHEN-A");
    setSchoolId("SDN-02");
    setMealDate(day);
    setReporter("parent");
    setContact("081200000001");
    setAffected(2);
    setSymptoms(["vomiting", "abdominal_pain"]);
    setOnset(`${day}T14:10`);
    setMedical(true);
    setHospital(false);
    setDescription(
      "My son came home at two and started vomiting about an hour later. His sister has stomach cramps too. He said the chicken tasted sour.",
    );
  }

  function toggle(s: Symptom) {
    setSymptoms((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));
  }

  function onPhoto(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    if (!picked) return setPhoto(null);
    if (!["image/jpeg", "image/png"].includes(picked.type)) return setError("Photo must be JPEG or PNG.");
    if (picked.size > MAX_PHOTO) return setError("Photo must be smaller than 1.5 MB.");
    const reader = new FileReader();
    reader.onload = () => {
      setPhoto({ name: picked.name, b64: String(reader.result).split(",")[1] ?? "" });
      setError("");
    };
    reader.readAsDataURL(picked);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (symptoms.length === 0) return setError("Select at least one symptom.");
    if (!onset) return setError("Tell us roughly when symptoms started.");
    setBusy(true);
    setError("");
    try {
      const res = await c05.submitClaim({
        kitchen_id: kitchenId,
        school_id: schoolId,
        meal_date: mealDate,
        reporter_type: reporter,
        contact,
        affected_count: affected,
        symptoms,
        onset_at: new Date(onset).toISOString(),
        sought_medical: medical || hospital,
        hospitalized: hospital,
        description,
        ...(photo ? { photo_base64: photo.b64 } : {}),
      });
      setReceipt(res);
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (receipt) {
    return (
      <div className="panel p-5" role="status">
        <p className="label text-[var(--pass)]">Report received</p>
        <p className="mt-2 text-[15px] leading-[22px]">{receipt.message}</p>
        <p className="mono mt-3 text-[var(--ink-3)]">Reference {receipt.claim_id.slice(0, 12)}</p>
        <Button type="button" variant="outline" className="mt-4" onClick={() => setReceipt(null)}>
          File another report
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div
        role="note"
        className="rounded-[var(--r-panel)] border border-[var(--defect)] bg-[var(--raised)] p-4 text-[14px] leading-[20px]"
      >
        <strong>Someone unwell right now?</strong> Go to the nearest Puskesmas or call <strong>119</strong> first.
        This form helps the kitchen and health office investigate; it is not emergency care.
      </div>

      <div className="well flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-[13px] leading-[18px]">
          <strong>Trying the prototype?</strong> Fill the form with an example: a parent whose two children were sick
          after yesterday&rsquo;s lunch at SDN-02.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={fillExample} className="shrink-0">
          Fill with an example
        </Button>
      </div>

      <section className="panel grid gap-3 p-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="kitchen">Meal kitchen (SPPG)</Label>
          <select id="kitchen" value={kitchenId} onChange={(e) => setKitchenId(e.target.value)} className={fieldClass}>
            <option value="KITCHEN-A">KITCHEN-A</option>
            <option value="KITCHEN-B">KITCHEN-B</option>
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="school">School code</Label>
          <Input
            id="school"
            required
            value={schoolId}
            onChange={(e) => setSchoolId(e.target.value.toUpperCase())}
            placeholder="e.g. SDN-02"
            className="h-11 font-mono"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="meal-date">Date the meal was eaten</Label>
          <Input
            id="meal-date"
            type="date"
            required
            value={mealDate}
            onChange={(e) => setMealDate(e.target.value)}
            className="h-11"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="onset">When did symptoms start?</Label>
          <Input
            id="onset"
            type="datetime-local"
            required
            value={onset}
            onChange={(e) => setOnset(e.target.value)}
            className="h-11"
          />
        </div>
      </section>

      <fieldset className="panel p-4">
        <legend className="label px-1">Symptoms</legend>
        <div className="mt-1 flex flex-wrap gap-2">
          {SYMPTOMS.map((s) => (
            <Button
              key={s.key}
              type="button"
              size="sm"
              variant={symptoms.includes(s.key) ? "default" : "outline"}
              aria-pressed={symptoms.includes(s.key)}
              onClick={() => toggle(s.key)}
              className="h-10"
            >
              {s.label}
            </Button>
          ))}
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="affected">How many people are affected?</Label>
            <Input
              id="affected"
              type="number"
              min={1}
              max={50}
              required
              value={affected}
              onChange={(e) => setAffected(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
              className="h-11"
            />
          </div>
          <div className="flex flex-col justify-end gap-2 text-[14px]">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={medical} onChange={(e) => setMedical(e.target.checked)} className="size-4" />
              Visited a clinic, Puskesmas or doctor
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={hospital}
                onChange={(e) => setHospital(e.target.checked)}
                className="size-4"
              />
              Admitted to hospital
            </label>
          </div>
        </div>
      </fieldset>

      <section className="panel grid gap-3 p-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="reporter">You are</Label>
          <select
            id="reporter"
            value={reporter}
            onChange={(e) => setReporter(e.target.value as ReporterType)}
            className={fieldClass}
          >
            {REPORTERS.map((r) => (
              <option key={r.key} value={r.key}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="contact">Phone number for follow-up</Label>
          <Input
            id="contact"
            type="tel"
            required
            autoComplete="tel"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            placeholder="08xx..."
            className="h-11"
          />
          <p className="meta">Stored only as a one-way hash; staff call back through the health office.</p>
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="description">What happened? (optional)</Label>
          <Textarea
            id="description"
            rows={4}
            maxLength={1000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What was eaten, who is affected, what symptoms and when."
          />
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="photo">Photo of the meal (optional)</Label>
          <input
            id="photo"
            type="file"
            accept="image/jpeg,image/png"
            onChange={onPhoto}
            className="text-[14px] file:mr-3 file:h-10 file:rounded-[var(--r-control)] file:border file:border-[var(--hairline)] file:bg-[var(--raised)] file:px-3"
          />
          <p className="meta">Only a fingerprint of the photo is kept, to spot the same picture reused across reports.</p>
        </div>
      </section>

      {error ? (
        <p role="alert" className="text-[14px] text-[var(--defect)]">
          {error}
        </p>
      ) : null}
      <Button type="submit" disabled={busy} className="h-12 text-[15px]">
        {busy ? "Sending…" : "Send report"}
      </Button>
    </form>
  );
}
