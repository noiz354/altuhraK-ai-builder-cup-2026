"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { c05, C05Error } from "@/lib/c05-client";
import type {
  InsightCategory,
  Role,
  Severity,
  SupplyCatalog,
  SupplyLot,
  SupplyOverview,
  SupplyTrace,
} from "@/lib/c05-types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

const SEVERITY_COLOR: Record<Severity, string> = {
  high: "var(--defect)",
  medium: "var(--review)",
  low: "var(--ink-3)",
};

const CATEGORY_TEXT: Record<InsightCategory, string> = {
  food_safety: "Food safety",
  stock: "Stock",
  cost: "Cost",
  logistics: "Distance & time",
  supplier: "Supplier",
};

export function idr(n: number | null | undefined) {
  if (n == null) return "—";
  return "Rp" + Math.round(n).toLocaleString("id-ID");
}

function hours(min: number | null | undefined) {
  if (min == null) return "—";
  return min < 60 ? `${min} min` : `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, "0")} min`;
}

function shortDate(iso: string) {
  return new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div className="panel p-3">
      <p className="label">{label}</p>
      <p className="mt-1 text-[24px] leading-[30px] font-semibold tabular-nums" style={tone ? { color: tone } : undefined}>
        {value}
      </p>
      {hint ? <p className="meta mt-0.5">{hint}</p> : null}
    </div>
  );
}

function SeverityDot({ severity }: { severity: Severity }) {
  return (
    <span
      aria-label={`${severity} priority`}
      className="mt-1.5 size-2.5 shrink-0 rounded-full"
      style={{ background: SEVERITY_COLOR[severity] }}
    />
  );
}

function FlagList({ lot }: { lot: SupplyLot }) {
  if (!lot.flags.length) return <span className="meta">All checks passed</span>;
  return (
    <ul className="flex flex-col gap-0.5">
      {lot.flags.map((f) => (
        <li key={f.code} className="text-[12px] leading-[16px]" style={{ color: SEVERITY_COLOR[f.severity] }}>
          {f.title}
        </li>
      ))}
    </ul>
  );
}

function TempCell({ lot }: { lot: SupplyLot }) {
  if (lot.arrival_temp_c == null) return <span className="meta">n/a</span>;
  const warm = lot.chilled && lot.arrival_temp_c > 5;
  return (
    <span className="tabular-nums" style={warm ? { color: "var(--defect)", fontWeight: 600 } : undefined}>
      {lot.arrival_temp_c}°C
    </span>
  );
}

export function SupplyConsole({
  role,
  kitchenId,
  initialDate,
}: {
  role: Role;
  kitchenId: string;
  initialDate?: string | null;
}) {
  const [data, setData] = useState<SupplyOverview | null>(null);
  const [traceDate, setTraceDate] = useState<string | null>(initialDate ?? null);
  const [traced, setTraced] = useState<SupplyTrace | null>(null);
  const [busy, setBusy] = useState<"" | "ai">("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"suppliers" | "prices" | "stock" | "deliveries">("suppliers");

  // Bumping the key refetches, e.g. after a delivery is recorded.
  const [reloadKey, setReloadKey] = useState(0);
  const load = useCallback(() => setReloadKey((n) => n + 1), []);

  useEffect(() => {
    let alive = true;
    c05
      .supplyOverview(role, kitchenId)
      .then((d) => {
        if (!alive) return;
        setData(d);
        setError("");
      })
      .catch((e) => {
        if (!alive) return;
        setData(null);
        setError(e instanceof C05Error ? e.message : "Could not load supply data");
      });
    return () => {
      alive = false;
    };
  }, [role, kitchenId, reloadKey]);

  const days = useMemo(() => {
    if (!data) return [];
    const end = new Date(`${data.as_of}T12:00:00`);
    return Array.from({ length: data.kpis.window_days }, (_, i) => {
      const d = new Date(end);
      d.setDate(end.getDate() - i);
      return d.toISOString().slice(0, 10);
    });
  }, [data]);
  const activeDate = traceDate ?? days[1] ?? days[0] ?? null;

  useEffect(() => {
    if (!activeDate) return;
    let alive = true;
    c05
      .supplyTrace(role, kitchenId, activeDate)
      .then((t) => alive && setTraced(t))
      .catch(() => alive && setTraced(null));
    return () => {
      alive = false;
    };
  }, [role, kitchenId, activeDate, data]);

  async function generate() {
    setBusy("ai");
    try {
      setData(await c05.supplyInsights(role, kitchenId));
      setError("");
    } catch (e) {
      setError(e instanceof C05Error ? e.message : "Could not prepare the brief");
    } finally {
      setBusy("");
    }
  }

  if (error && !data) {
    return <p className="panel p-4 text-[14px] text-[var(--defect)]">{error}</p>;
  }
  if (!data) return <p className="meta">Loading supply records…</p>;

  const k = data.kpis;
  const high = data.insights.filter((i) => i.severity === "high").length;
  const canAi = role !== "CREW";
  const ai = data.ai;

  return (
    <div className="flex flex-col gap-5">
      {/* KPIs */}
      <section aria-label="Last 7 days" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Ingredient cost / portion" value={idr(k.cost_per_portion_idr)} hint={`${k.portions.toLocaleString("id-ID")} portions in ${k.window_days} days`} />
        <Kpi label={`Spend, last ${k.window_days} days`} value={idr(k.spend_idr)} hint={`${k.lots} deliveries`} />
        <Kpi label="Avg supplier distance" value={k.avg_distance_km != null ? `${k.avg_distance_km} km` : "—"} hint={`${k.local_share_pct ?? 0}% of spend within 50 km`} />
        <Kpi label="Avg transit, fresh items" value={hours(k.avg_perishable_transit_min)} hint="Dispatch → kitchen door" />
        <Kpi
          label="On-time deliveries"
          value={k.on_time_pct != null ? `${k.on_time_pct}%` : "—"}
          hint={`${k.rejected_lots} lot(s) rejected at the door`}
          tone={k.on_time_pct != null && k.on_time_pct < 90 ? "var(--review)" : undefined}
        />
        <Kpi label="Needs action now" value={String(high)} hint="High-priority insights" tone={high ? "var(--defect)" : "var(--pass)"} />
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        {/* Insights */}
        <section className="flex min-w-0 flex-col gap-3" aria-labelledby="insights-h">
          <div className="panel p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 id="insights-h" className="text-[18px] font-semibold">
                  Priority brief
                </h2>
                <p className="meta">What matters most this week, combined from every check below, with actions.</p>
              </div>
              <Button onClick={generate} disabled={!canAi || busy === "ai"} title={canAi ? undefined : "Supervisors and admins only"}>
                {busy === "ai" ? "Preparing…" : ai ? "Refresh brief" : "Prepare brief"}
              </Button>
            </div>
            {ai?.summary ? (
              <div className="mt-3 flex flex-col gap-2">
                <p className="text-[15px] leading-[22px]">{ai.summary}</p>
                <ol className="flex flex-col gap-2">
                  {ai.insights.map((i, n) => (
                    <li key={n} className="well p-3">
                      <p className="meta">{CATEGORY_TEXT[i.category]}</p>
                      <p className="text-[14px] font-semibold">{i.title}</p>
                      <p className="text-[13px] leading-[18px] text-[var(--ink-2)]">{i.detail}</p>
                      <p className="mt-1 text-[13px] leading-[18px]">
                        <strong>Do:</strong> {i.action}
                      </p>
                      {i.lot_ids.length || i.supplier_ids.length ? (
                        <p className="meta mt-1 font-mono">{[...i.supplier_ids, ...i.lot_ids].join(" · ")}</p>
                      ) : null}
                    </li>
                  ))}
                </ol>
                <p className="meta">
                  Prepared {new Date(ai.generated_at).toLocaleString()}. The checks below remain the record.
                </p>
              </div>
            ) : ai ? (
              <p className="well mt-3 p-3 text-[13px] leading-[18px]">
                The brief is not available right now. The checks below still apply and are listed in priority
                order.
              </p>
            ) : (
              <p className="well mt-3 p-3 text-[13px] leading-[18px] text-[var(--ink-2)]">
                {canAi
                  ? "No brief yet. The automatic checks below are already ranked: food safety first, then stock, cost and logistics."
                  : "Switch to SUPERVISOR or ADMIN to prepare the brief."}
              </p>
            )}
          </div>

          <div className="panel p-4">
            <h2 className="text-[18px] font-semibold">Automatic checks ({data.insights.length})</h2>
            <p className="meta">Temperature, cold chain, transit time, use-by date, stock cover, price vs reference, punctuality.</p>
            <ul className="mt-3 flex flex-col gap-2">
              {data.insights.map((i) => (
                <li key={i.insight_id} className="flex gap-2.5 rounded-[var(--r-control)] border border-[var(--hairline)] p-3">
                  <SeverityDot severity={i.severity} />
                  <div className="min-w-0">
                    <p className="meta">
                      {CATEGORY_TEXT[i.category]} · {i.severity}
                    </p>
                    <p className="text-[14px] leading-[20px] font-medium">{i.title}</p>
                    <p className="text-[13px] leading-[18px] text-[var(--ink-2)]">{i.detail}</p>
                    <p className="mt-0.5 text-[13px] leading-[18px]">
                      <strong>Do:</strong> {i.action}
                    </p>
                    {i.meal_dates.length ? (
                      <p className="mt-1 flex flex-wrap gap-1">
                        {i.meal_dates.map((d) => (
                          <button
                            key={d}
                            type="button"
                            onClick={() => setTraceDate(d)}
                            className="rounded-full border border-[var(--hairline)] px-2 py-0.5 text-[12px] text-[var(--action)] hover:bg-[var(--sunken)]"
                          >
                            Trace meals of {shortDate(d)}
                          </button>
                        ))}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
              {!data.insights.length ? <li className="meta">No checks failed in the last 7 days.</li> : null}
            </ul>
          </div>
        </section>

        {/* Trace */}
        <section className="panel flex min-w-0 flex-col gap-3 p-4 xl:sticky xl:top-20 xl:h-fit" aria-labelledby="trace-h">
          <div>
            <h2 id="trace-h" className="text-[18px] font-semibold">
              Trace a meal back to its ingredients
            </h2>
            <p className="meta">Pick a meal date: every lot used that day, where it came from and how it arrived.</p>
          </div>
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Meal date">
            {days.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setTraceDate(d)}
                aria-pressed={d === activeDate}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-[13px]",
                  d === activeDate
                    ? "border-[var(--action)] bg-[var(--action)] text-white"
                    : "border-[var(--hairline)] hover:bg-[var(--sunken)]",
                )}
              >
                {shortDate(d)}
              </button>
            ))}
          </div>
          {traced && traced.meal_date === activeDate ? (
            traced.lots.length ? (
              <>
                <p className="text-[14px] leading-[20px]">
                  <strong>{traced.lots.length} lots</strong> from <strong>{traced.suppliers} suppliers</strong>
                  {traced.batch ? ` went into ${traced.batch.portions.toLocaleString("id-ID")} portions` : ""}. Farthest
                  source {traced.max_distance_km} km.{" "}
                  {traced.high_flags ? (
                    <span className="font-semibold text-[var(--defect)]">{traced.high_flags} high-priority problem(s).</span>
                  ) : (
                    <span className="text-[var(--pass)]">No high-priority problems.</span>
                  )}
                </p>
                <ul className="flex flex-col gap-2">
                  {traced.lots.map((l) => (
                    <li
                      key={l.lot_id}
                      className="rounded-[var(--r-control)] border p-3"
                      style={{
                        borderColor: l.flags.some((f) => f.severity === "high") ? "var(--defect)" : "var(--hairline)",
                      }}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-[15px] font-semibold">
                          {l.label} <span className="meta font-normal">· {l.qty_used} {l.unit} used</span>
                        </p>
                        <span className="meta font-mono">{l.lot_id}</span>
                      </div>
                      <p className="text-[13px] leading-[18px]">
                        {l.supplier.name} · {l.supplier.location}
                      </p>
                      <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-[13px] sm:grid-cols-4">
                        <div>
                          <dt className="meta">Distance</dt>
                          <dd className="tabular-nums">{l.supplier.distance_km} km</dd>
                        </div>
                        <div>
                          <dt className="meta">On the road</dt>
                          <dd className="tabular-nums">{hours(l.transit_min)}</dd>
                        </div>
                        <div>
                          <dt className="meta">Arrived at</dt>
                          <dd>
                            <TempCell lot={l} />
                          </dd>
                        </div>
                        <div>
                          <dt className="meta">Price / {l.unit}</dt>
                          <dd className="tabular-nums">{idr(l.unit_price)}</dd>
                        </div>
                      </dl>
                      <div className="mt-1.5">
                        <FlagList lot={l} />
                      </div>
                      {l.receiving_note ? <p className="meta mt-1">Receiving note: {l.receiving_note}</p> : null}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="well p-3 text-[13px]">No ingredient lots are recorded for meals on this date.</p>
            )
          ) : (
            <p className="meta">Loading trace…</p>
          )}
        </section>
      </div>

      {/* Detail tables */}
      <section className="panel p-4" aria-label="Supply details">
        <div className="flex flex-wrap gap-1" role="tablist">
          {(
            [
              ["suppliers", "Suppliers"],
              ["prices", "Prices"],
              ["stock", "Stock"],
              ["deliveries", "Deliveries"],
            ] as const
          ).map(([key, text]) => (
            <button
              key={key}
              role="tab"
              type="button"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={cn(
                "rounded-[var(--r-control)] px-3 py-1.5 text-[14px]",
                tab === key ? "bg-[var(--sunken)] font-medium" : "text-[var(--ink-2)] hover:bg-[var(--sunken)]",
              )}
            >
              {text}
            </button>
          ))}
        </div>

        <div className="mt-3 overflow-x-auto">
          {tab === "suppliers" ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Supplies</TableHead>
                  <TableHead className="text-right">Distance</TableHead>
                  <TableHead className="text-right">Avg transit</TableHead>
                  <TableHead className="text-right">On time</TableHead>
                  <TableHead className="text-right">Price index</TableHead>
                  <TableHead className="text-right">Warm arrivals</TableHead>
                  <TableHead className="text-right">Spend</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.suppliers.map((s) => (
                  <TableRow key={s.supplier_id}>
                    <TableCell>
                      <p className="font-medium">{s.name}</p>
                      <p className="meta">
                        {s.type} · {s.location}
                        {s.cold_chain ? " · cold chain" : ""}
                        {s.certifications.length ? ` · ${s.certifications.join(", ")}` : ""}
                      </p>
                    </TableCell>
                    <TableCell>{s.ingredients.join(", ")}</TableCell>
                    <TableCell className="text-right tabular-nums">{s.distance_km} km</TableCell>
                    <TableCell className="text-right tabular-nums">{hours(s.avg_transit_min)}</TableCell>
                    <TableCell
                      className="text-right tabular-nums"
                      style={s.on_time_pct != null && s.on_time_pct < 80 ? { color: "var(--review)" } : undefined}
                    >
                      {s.on_time_pct != null ? `${s.on_time_pct}%` : "—"}
                    </TableCell>
                    <TableCell
                      className="text-right tabular-nums"
                      title="100 = reference price. Above 115 is expensive; below 80 is suspiciously cheap."
                      style={s.price_index > 115 || s.price_index < 80 ? { color: "var(--review)" } : undefined}
                    >
                      {s.price_index}
                    </TableCell>
                    <TableCell
                      className="text-right tabular-nums"
                      style={s.temp_breaches ? { color: "var(--defect)", fontWeight: 600 } : undefined}
                    >
                      {s.temp_breaches}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{idr(s.spend_idr)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}

          {tab === "prices" ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ingredient</TableHead>
                  <TableHead className="text-right">Latest</TableHead>
                  <TableHead className="text-right">Reference</TableHead>
                  <TableHead className="text-right">vs reference</TableHead>
                  <TableHead className="text-right">7-day change</TableHead>
                  <TableHead>Trend</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.price_trends.map((t) => {
                  const gap = Math.round((t.latest / t.reference - 1) * 100);
                  const max = Math.max(...t.points.map((p) => p.price), t.reference);
                  return (
                    <TableRow key={t.ingredient}>
                      <TableCell className="font-medium">{t.label}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {idr(t.latest)}/{t.unit}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{idr(t.reference)}</TableCell>
                      <TableCell
                        className="text-right tabular-nums"
                        style={gap > 15 || gap < -20 ? { color: "var(--review)", fontWeight: 600 } : undefined}
                      >
                        {gap > 0 ? "+" : ""}
                        {gap}%
                      </TableCell>
                      <TableCell
                        className="text-right tabular-nums"
                        style={t.change_pct > 10 ? { color: "var(--review)", fontWeight: 600 } : undefined}
                      >
                        {t.change_pct > 0 ? "+" : ""}
                        {t.change_pct}%
                      </TableCell>
                      <TableCell>
                        <div className="flex h-6 items-end gap-0.5" aria-label={`${t.points.length} deliveries`}>
                          {t.points.map((p, n) => (
                            <span
                              key={n}
                              title={`${p.date}: ${idr(p.price)}`}
                              className="w-1.5 rounded-sm bg-[var(--brand)]"
                              style={{ height: `${Math.max(15, (p.price / max) * 100)}%` }}
                            />
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : null}

          {tab === "stock" ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ingredient</TableHead>
                  <TableHead className="text-right">On hand</TableHead>
                  <TableHead className="text-right">Daily use</TableHead>
                  <TableHead className="text-right">Days of cover</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.stock.map((s) => (
                  <TableRow key={s.ingredient}>
                    <TableCell className="font-medium">{s.label}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.on_hand} {s.unit}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.daily_use} {s.unit}
                    </TableCell>
                    <TableCell
                      className="text-right tabular-nums"
                      style={s.days_cover != null && s.days_cover < 1.5 ? { color: "var(--defect)", fontWeight: 600 } : undefined}
                    >
                      {s.fresh_daily ? <span className="meta">bought fresh daily</span> : s.days_cover ?? "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{idr(s.value_idr)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}

          {tab === "deliveries" ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Received</TableHead>
                  <TableHead>Ingredient</TableHead>
                  <TableHead>Supplier</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">Transit</TableHead>
                  <TableHead className="text-right">Temp</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Checks</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.lots.map((l) => (
                  <TableRow key={l.lot_id}>
                    <TableCell className="whitespace-nowrap">
                      {shortDate(l.received_at)}
                      <p className="meta font-mono">{l.lot_id}</p>
                    </TableCell>
                    <TableCell>{l.label}</TableCell>
                    <TableCell>
                      {l.supplier.name}
                      <p className="meta">{l.supplier.distance_km} km</p>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {l.quantity} {l.unit}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{hours(l.transit_min)}</TableCell>
                    <TableCell className="text-right">
                      <TempCell lot={l} />
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          l.receiving_status === "REJECTED"
                            ? "border-[var(--defect)] text-[var(--defect)]"
                            : "border-[var(--hairline)] text-[var(--ink-2)]"
                        }
                      >
                        {l.receiving_status === "REJECTED" ? "Rejected" : "Accepted"}
                      </Badge>
                    </TableCell>
                    <TableCell className="min-w-[200px]">
                      <FlagList lot={l} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </div>
        <p className="meta mt-3">{data.reference_note}</p>
      </section>

      <DeliveryForm role={role} kitchenId={kitchenId} onSaved={load} />
    </div>
  );
}

function localInput(d: Date) {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function DeliveryForm({ role, kitchenId, onSaved }: { role: Role; kitchenId: string; onSaved: () => void }) {
  const [catalog, setCatalog] = useState<SupplyCatalog | null>(null);
  const [form, setForm] = useState(() => {
    const now = new Date();
    const out = new Date(now.getTime() - 60 * 60 * 1000);
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    return {
      ingredient: "chicken",
      supplier_id: "SUP-04",
      quantity: "20",
      unit_price: "38000",
      dispatched_at: localInput(out),
      received_at: localInput(now),
      arrival_temp_c: "4",
      use_by: tomorrow.toISOString().slice(0, 10),
      receiving_status: "ACCEPTED" as "ACCEPTED" | "REJECTED",
      receiving_note: "",
    };
  });
  const [saved, setSaved] = useState<SupplyLot | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    c05.supplyCatalog(role).then(setCatalog).catch(() => setCatalog(null));
  }, [role]);

  const spec = catalog?.ingredients.find((i) => i.ingredient === form.ingredient);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const lot = await c05.recordDelivery({
        role,
        kitchen_id: kitchenId,
        ingredient: form.ingredient,
        supplier_id: form.supplier_id,
        quantity: Number(form.quantity),
        unit_price: Number(form.unit_price),
        dispatched_at: new Date(form.dispatched_at).toISOString(),
        received_at: new Date(form.received_at).toISOString(),
        arrival_temp_c: form.arrival_temp_c === "" ? null : Number(form.arrival_temp_c),
        use_by: form.use_by,
        receiving_status: form.receiving_status,
        receiving_note: form.receiving_note,
      });
      setSaved(lot);
      onSaved();
    } catch (err) {
      setError(err instanceof C05Error ? err.message : "Could not record the delivery");
    } finally {
      setBusy(false);
    }
  }

  const field = "h-10 w-full rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-2 text-[14px]";

  return (
    <details className="panel group p-0">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3">
        <span>
          <span className="block text-[16px] font-semibold">Record a delivery</span>
          <span className="meta">At the kitchen door: what arrived, from whom, how long it travelled and how warm it was.</span>
        </span>
        <span className="meta group-open:hidden">Open</span>
        <span className="meta hidden group-open:inline">Close</span>
      </summary>
      <form onSubmit={submit} className="grid gap-3 border-t border-[var(--hairline)] p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-ing">Ingredient</Label>
          <select id="d-ing" className={field} value={form.ingredient} onChange={set("ingredient")}>
            {catalog?.ingredients.map((i) => (
              <option key={i.ingredient} value={i.ingredient}>
                {i.label}
                {i.chilled ? " (chilled)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-sup">Supplier</Label>
          <select id="d-sup" className={field} value={form.supplier_id} onChange={set("supplier_id")}>
            {catalog?.suppliers.map((s) => (
              <option key={s.supplier_id} value={s.supplier_id}>
                {s.name} ({s.distance_km} km)
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-qty">Quantity ({spec?.unit ?? "kg"})</Label>
          <input id="d-qty" type="number" min="0" step="0.1" className={field} value={form.quantity} onChange={set("quantity")} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-price">Price per {spec?.unit ?? "kg"} (Rp)</Label>
          <input id="d-price" type="number" min="0" className={field} value={form.unit_price} onChange={set("unit_price")} />
          {spec ? <span className="meta">Reference {idr(spec.ref)}</span> : null}
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-out">Left the supplier</Label>
          <input id="d-out" type="datetime-local" className={field} value={form.dispatched_at} onChange={set("dispatched_at")} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-in">Arrived at the kitchen</Label>
          <input id="d-in" type="datetime-local" className={field} value={form.received_at} onChange={set("received_at")} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-temp">Arrival temperature (°C){spec?.chilled ? " · required" : ""}</Label>
          <input id="d-temp" type="number" step="0.1" className={field} value={form.arrival_temp_c} onChange={set("arrival_temp_c")} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-use">Use by</Label>
          <input id="d-use" type="date" className={field} value={form.use_by} onChange={set("use_by")} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="d-status">Receiving decision</Label>
          <select id="d-status" className={field} value={form.receiving_status} onChange={set("receiving_status")}>
            <option value="ACCEPTED">Accept</option>
            <option value="REJECTED">Reject and return</option>
          </select>
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-3">
          <Label htmlFor="d-note">Note (optional)</Label>
          <input id="d-note" className={field} value={form.receiving_note} onChange={set("receiving_note")} placeholder="e.g. smell, packaging, seal" />
        </div>
        <div className="flex flex-col gap-2 sm:col-span-2 lg:col-span-4">
          <div>
            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save delivery"}
            </Button>
          </div>
          {error ? <p className="text-[14px] text-[var(--defect)]">{error}</p> : null}
          {saved ? (
            <div className="well p-3 text-[14px]">
              <p>
                Saved as <span className="font-mono">{saved.lot_id}</span>: {saved.label} from {saved.supplier.name},{" "}
                {hours(saved.transit_min)} on the road.
              </p>
              <div className="mt-1">
                <FlagList lot={saved} />
              </div>
            </div>
          ) : null}
        </div>
      </form>
    </details>
  );
}
