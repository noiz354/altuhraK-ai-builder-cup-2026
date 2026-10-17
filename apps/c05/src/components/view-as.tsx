"use client";

import { useEffect, useState } from "react";
import { useSession } from "@/components/providers";
import { c05 } from "@/lib/c05-client";
import type { Role } from "@/lib/c05-types";

const ROLES: Role[] = ["CREW", "SUPERVISOR", "ADMIN"];

/**
 * Demo controls that used to live in the global header. They belong to the
 * working pages: which role you act as, which kitchen you look at, and whether
 * the QC service behind the page is reachable.
 */
export function ViewAs() {
  const { role, setRole, kitchenId, setKitchenId } = useSession();
  const [health, setHealth] = useState<"checking" | "up" | "down">("checking");

  useEffect(() => {
    let alive = true;
    const ping = () =>
      c05
        .health()
        .then(() => alive && setHealth("up"))
        .catch(() => alive && setHealth("down"));
    void ping();
    const t = setInterval(ping, 10000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const select =
    "h-8 rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-1.5 text-[13px]";

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
      <div className="flex items-center gap-1 rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-2 py-1">
        <span className="meta">Demo as</span>
        <select value={role} onChange={(e) => setRole(e.target.value as Role)} className={select} aria-label="Active role">
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <span className="meta">at</span>
        <select
          value={kitchenId}
          onChange={(e) => setKitchenId(e.target.value)}
          className={select + " font-mono"}
          aria-label="Active kitchen"
        >
          <option value="KITCHEN-A">KITCHEN-A</option>
          <option value="KITCHEN-B">KITCHEN-B</option>
        </select>
      </div>
      <span className="flex items-center gap-1.5" aria-live="polite" title="Status of the inspection service">
        <span
          aria-hidden
          className={
            "size-2 rounded-full " +
            (health === "up" ? "bg-[var(--pass)]" : health === "down" ? "bg-[var(--defect)]" : "bg-[var(--ink-3)]")
          }
        />
        <span className="meta">
          {health === "up" ? "QC service up" : health === "down" ? "QC service down" : "checking"}
        </span>
      </span>
    </div>
  );
}
