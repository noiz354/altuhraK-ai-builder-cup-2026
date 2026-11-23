"use client";

import Link from "next/link";
import type { ReactNode } from "react";

// Quadrant layout of the stainless tray artwork (percent of a 640x480 frame).
export const QUAD_BOX: Record<string, { left: string; top: string; width: string; height: string }> = {
  Q1: { left: "10.6%", top: "12.9%", width: "39.7%", height: "35.4%" },
  Q2: { left: "52.8%", top: "12.9%", width: "36.6%", height: "35.4%" },
  Q3: { left: "10.6%", top: "52.5%", width: "39.7%", height: "34.6%" },
  Q4: { left: "52.8%", top: "52.5%", width: "36.6%", height: "34.6%" },
};

export function GeminiBadge({ reviewed }: { reviewed?: string }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className="badge-ai">
        <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2c.6 4.7 4.3 9.4 10 10-5.7.6-9.4 5.3-10 10-.6-4.7-4.3-9.4-10-10 5.7-.6 9.4-5.3 10-10z" fill="currentColor" />
        </svg>
        Gemini
      </span>
      <span className="t-label-s muted">{reviewed ? `ditinjau ${reviewed}` : "belum ditinjau manusia"}</span>
    </span>
  );
}

export function ModeSwitch({ current }: { current: "scan" | "analisa" }) {
  return (
    <nav aria-label="Mode" className="seg">
      <Link href="/proto/scan" aria-current={current === "scan" ? "page" : undefined}>
        Scan · HP
      </Link>
      <Link href="/proto/analisa" aria-current={current === "analisa" ? "page" : undefined}>
        Analisa · Web
      </Link>
    </nav>
  );
}

export function Snackbar({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      className="snack fixed bottom-24 left-1/2 z-50 flex min-h-12 max-w-[min(560px,calc(100vw-32px))] -translate-x-1/2 items-center gap-3 rounded-[4px] px-4 py-3 t-body shadow-[var(--m3-shadow-3)]"
      style={{ background: "var(--m3-inverse-surface)", color: "var(--m3-inverse-on-surface)" }}
    >
      {children}
    </div>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2">
      {/* eslint-disable-next-line @next/next/no-img-element -- static logo */}
      <img src="/logo.png" alt="" width={28} height={28} className="size-7 rounded-[8px]" />
      <span className="t-title">Meal QC</span>
    </span>
  );
}
