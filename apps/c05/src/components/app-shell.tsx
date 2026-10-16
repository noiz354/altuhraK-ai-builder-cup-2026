"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { c05 } from "@/lib/c05-client";
import type { Role } from "@/lib/c05-types";

const NAV = [
  { href: "/crew", label: "Crew" },
  { href: "/admin", label: "Admin" },
  { href: "/agent", label: "Agent" },
];

const ROLES: Role[] = ["CREW", "SUPERVISOR", "ADMIN"];

export function AppShell({
  role,
  setRole,
  kitchenId,
  setKitchenId,
  children,
}: {
  role: Role;
  setRole: (r: Role) => void;
  kitchenId: string;
  setKitchenId: (k: string) => void;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [health, setHealth] = useState<"checking" | "up" | "down">("checking");
  const [navOpen, setNavOpen] = useState(false);

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

  useEffect(() => setNavOpen(false), [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-[var(--hairline)] bg-[var(--raised)]/95 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-[1440px] items-center gap-3 px-4 py-2.5 lg:px-8">
          {/* min-h-11 on coarse pointers: this is the primary navigation target and
              it sits in the tap-heavy header area used one-handed on a phone. */}
          <Link href="/crew" className="flex min-h-11 items-center gap-2 sm:min-h-0">
            <span
              aria-hidden
              className="flex size-7 items-center justify-center rounded-[6px] bg-[var(--brand)] text-[13px] font-bold text-white"
            >
              C5
            </span>
            <span className="text-[15px] font-semibold">Visual QC</span>
          </Link>

          <nav aria-label="Main" className="ml-2 hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={pathname.startsWith(n.href) ? "page" : undefined}
                className={
                  "rounded-[var(--r-control)] px-3 py-2 text-[14px] transition-colors duration-150 " +
                  (pathname.startsWith(n.href)
                    ? "bg-[var(--sunken)] font-medium text-[var(--ink)]"
                    : "text-[var(--ink-2)] hover:bg-[var(--sunken)]")
                }
              >
                {n.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <Badge
              variant="outline"
              className={
                health === "up"
                  ? "border-[var(--pass)] text-[var(--pass)]"
                  : health === "down"
                    ? "border-[var(--defect)] text-[var(--defect)]"
                    : "border-[var(--hairline)] text-[var(--ink-3)]"
              }
              aria-live="polite"
            >
              {health === "up" ? "QC service up" : health === "down" ? "QC service down" : "checking"}
            </Badge>

            <label className="hidden items-center gap-1.5 sm:flex">
              <span className="label">Role</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
                className="h-9 rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-2 text-[13px]"
                aria-label="Active role"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>

            <label className="hidden items-center gap-1.5 md:flex">
              <span className="label">Kitchen</span>
              <select
                value={kitchenId}
                onChange={(e) => setKitchenId(e.target.value)}
                className="h-9 rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-2 text-[13px] font-mono"
                aria-label="Active kitchen"
              >
                <option value="KITCHEN-A">KITCHEN-A</option>
                <option value="KITCHEN-B">KITCHEN-B</option>
              </select>
            </label>

            <Button
              type="button"
              variant="outline"
              size="sm"
              className="md:hidden"
              aria-expanded={navOpen}
              onClick={() => setNavOpen((v) => !v)}
            >
              Menu
            </Button>
          </div>
        </div>

        {navOpen ? (
          <nav aria-label="Mobile" className="border-t border-[var(--hairline)] px-4 py-2 md:hidden">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className="block rounded-[var(--r-control)] px-3 py-2.5 text-[15px]">
                {n.label}
              </Link>
            ))}
          </nav>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-5 lg:px-8">{children}</main>

      <footer className="border-t border-[var(--hairline)] px-4 py-4 lg:px-8">
        <p className="mx-auto max-w-[1440px] meta">
          Visual inspection only. Does not establish microbiological safety, nutritional composition, or measured
          food weight. Demo data is synthetic.
        </p>
      </footer>
    </div>
  );
}