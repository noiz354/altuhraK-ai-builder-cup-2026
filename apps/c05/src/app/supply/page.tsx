"use client";

import { useEffect, useMemo, useState } from "react";
import { c05 } from "@/lib/c05-client";
import type { SupplyLot, SupplyAnomaly } from "@/lib/c05-types";
import { useSession } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { CopyId } from "@/components/copy-id";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const EMPTY = {
  ingredient: "", supplier: "", origin: "", travel_time_min: "145",
  arrival_temp_c: "11.5", price_per_unit: "55000", quantity: "40", expires_at: "",
};

export default function SupplyPage() {
  const { role, kitchenId } = useSession();
  const [lots, setLots] = useState<SupplyLot[]>([]);
  const [anomalies, setAnomalies] = useState<SupplyAnomaly[]>([]);
  const [threshold, setThreshold] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([c05.listSupplyLots(role, kitchenId), c05.supplyAnomalies(role, kitchenId)])
      .then(([lotResult, anomalyResult]) => {
        if (!active) return;
        setLots(lotResult.lots);
        setAnomalies(anomalyResult.anomalies);
        setThreshold(anomalyResult.temperature_threshold_c);
      })
      .catch((e: unknown) => {
        if (active) setMessage(e instanceof Error ? e.message : String(e));
      });
    return () => {
      active = false;
    };
  }, [role, kitchenId]);

  const anomalyByLot = useMemo(() => {
    const map = new Map<string, SupplyAnomaly>();
    for (const a of anomalies) map.set(a.lot_id, a);
    return map;
  }, [anomalies]);

  const canWrite = role !== "CREW";

  async function submit() {
    setBusy(true);
    setMessage("");
    try {
      await c05.createSupplyLot({
        role,
        kitchen_id: kitchenId,
        ingredient: form.ingredient,
        supplier: form.supplier,
        origin: form.origin,
        travel_time_min: Number(form.travel_time_min),
        arrival_temp_c: Number(form.arrival_temp_c),
        price_per_unit: Number(form.price_per_unit),
        quantity: Number(form.quantity),
        received_at: new Date().toISOString(),
        ...(form.expires_at ? { expires_at: form.expires_at } : {}),
      });
      setForm(EMPTY);
      const [lotResult, anomalyResult] = await Promise.all([
        c05.listSupplyLots(role, kitchenId),
        c05.supplyAnomalies(role, kitchenId),
      ]);
      setLots(lotResult.lots);
      setAnomalies(anomalyResult.anomalies);
      setThreshold(anomalyResult.temperature_threshold_c);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 pb-24">
      <header>
        <p className="label text-[var(--brand)]">Supply</p>
        <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Ingredient traceability</h1>
        <p className="meta mt-1">
          Every lot records supplier, origin, transit time, arrival temperature and price. Checks are
          computed against this kitchen&apos;s own history.
        </p>
      </header>

      {anomalies.length > 0 ? (
        <section className="panel p-4">
          <h2 className="label">
            Supply insights · {anomalies.length} lot{anomalies.length === 1 ? "" : "s"} need attention
          </h2>
          {threshold !== null ? (
            <p className="meta mt-1">Cold-chain threshold {threshold} °C</p>
          ) : null}
          <ul className="mt-3 grid gap-2">
            {anomalies.map((a) => (
              <li key={a.lot_id} className="well p-3">
                <p className="text-[15px] font-medium">
                  {a.ingredient} · {a.supplier}
                </p>
                <ul className="mt-1 space-y-0.5">
                  {a.flags.map((f) => (
                    <li key={f.kind} className="text-sm text-[var(--defect)]">
                      {f.message}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {canWrite ? (
        <section className="panel p-4">
          <h2 className="label">Receive a lot</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {(
              [
                ["ingredient", "Ingredient"],
                ["supplier", "Supplier"],
                ["origin", "Origin"],
                ["travel_time_min", "Travel time (min)"],
                ["arrival_temp_c", "Arrival temperature (°C)"],
                ["price_per_unit", "Price per unit"],
                ["quantity", "Quantity"],
              ] as const
            ).map(([key, label]) => (
              <div key={key} className="flex flex-col gap-1.5">
                <Label htmlFor={key}>{label}</Label>
                <Input
                  id={key}
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                />
              </div>
            ))}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expires_at">Expires at (optional)</Label>
              <Input
                id="expires_at"
                type="date"
                value={form.expires_at}
                onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
              />
            </div>
          </div>
          {message ? <p className="mt-3 text-sm text-[var(--defect)]">{message}</p> : null}
          <Button type="button" className="mt-3 h-12 w-full" onClick={submit} disabled={busy}>
            {busy ? "Recording…" : "Record lot"}
          </Button>
        </section>
      ) : (
        <section className="panel p-4">
          <p className="meta">
            Crew has read-only access to supply records. Ask a supervisor to record a lot.
          </p>
        </section>
      )}

      <section className="panel p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="label">Lots · {lots.length}</h2>
          <Select value={status} onValueChange={(v) => setStatus(v ?? "")}>
            <SelectTrigger className="h-10 w-40">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="received">received</SelectItem>
              <SelectItem value="inspected">inspected</SelectItem>
              <SelectItem value="rejected">rejected</SelectItem>
              <SelectItem value="expired">expired</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {lots.length === 0 ? (
          <p className="meta mt-3">No lots recorded for this kitchen yet.</p>
        ) : (
          <ul className="mt-3 grid gap-2">
            {lots
              .filter((l) => !status || l.status === status)
              .map((lot) => (
                <li key={lot.lot_id} className="well p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="text-[15px] font-medium">
                      {lot.ingredient} · {lot.supplier}
                    </p>
                    <span className="mono text-sm text-[var(--ink-3)]">{lot.status}</span>
                  </div>
                  <p className="meta mt-1">
                    {lot.origin} · {lot.travel_time_min} min · {lot.arrival_temp_c} °C ·{" "}
                    {lot.price_per_unit.toLocaleString("id-ID")}
                  </p>
                  <p className="meta mt-1">
                    Lot ID: <CopyId value={lot.lot_id} />
                  </p>
                  <ul className="mt-2 flex flex-wrap gap-2 text-sm">
                    <li className={lot.checks.temp_ok ? "text-[var(--pass)]" : "text-[var(--defect)]"}>
                      cold chain {lot.checks.temp_ok ? "ok" : "failed"}
                    </li>
                    <li className={lot.checks.expiry_ok ? "text-[var(--pass)]" : "text-[var(--defect)]"}>
                      shelf life {lot.checks.expiry_ok ? "ok" : "short"}
                    </li>
                    <li className={lot.checks.price_ok ? "text-[var(--pass)]" : "text-[var(--defect)]"}>
                      price {lot.checks.price_ok ? "ok" : "above baseline"}
                    </li>
                  </ul>
                  {anomalyByLot.get(lot.lot_id) ? (
                    <p className="mt-2 text-sm text-[var(--defect)]">
                      Flagged: {anomalyByLot.get(lot.lot_id)!.flags.map((f) => f.kind).join(", ")}
                    </p>
                  ) : null}
                </li>
              ))}
          </ul>
        )}
      </section>
    </div>
  );
}