"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";

// Pages only. Role, kitchen, filters and actions live on each page (see
// ViewAs in the page header). Navigation lives here and nowhere else.
const NAV = [
  { href: "/crew", label: "Check meal" },
  { href: "/admin", label: "Review" },
  { href: "/report", label: "Report illness" },
  { href: "/claims", label: "Illness reports" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // The mobile menu remembers the path it was opened on, so navigating closes it
  // without a state update inside an effect.
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const navOpen = openedAt === pathname;
  const active = (href: string) => pathname.startsWith(href);

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-[var(--hairline)] bg-[var(--raised)]/95 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-[1440px] items-center gap-3 px-4 py-2.5 lg:px-8">
          {/* min-h-11 on coarse pointers: this is the primary navigation target and
              it sits in the tap-heavy header area used one-handed on a phone. */}
          <Link href="/" className="flex min-h-11 items-center gap-2 sm:min-h-0">
            {/* eslint-disable-next-line @next/next/no-img-element -- tiny static logo, no optimisation needed */}
            <img src="/logo.png" alt="" width={32} height={32} className="size-8 rounded-[6px]" />
            <span className="text-[15px] font-semibold">Meal QC</span>
          </Link>

          <nav aria-label="Main" className="ml-auto hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active(n.href) ? "page" : undefined}
                className={
                  "rounded-[var(--r-control)] px-3 py-2 text-[14px] transition-colors duration-150 " +
                  (active(n.href)
                    ? "bg-[var(--sunken)] font-medium text-[var(--ink)]"
                    : "text-[var(--ink-2)] hover:bg-[var(--sunken)]")
                }
              >
                {n.label}
              </Link>
            ))}
          </nav>

          <Button
            type="button"
            variant="outline"
            size="sm"
            className="ml-auto md:hidden"
            aria-expanded={navOpen}
            onClick={() => setOpenedAt(navOpen ? null : pathname)}
          >
            Menu
          </Button>
        </div>

        {navOpen ? (
          <nav aria-label="Mobile" className="border-t border-[var(--hairline)] px-4 py-2 md:hidden">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active(n.href) ? "page" : undefined}
                className="block rounded-[var(--r-control)] px-3 py-2.5 text-[15px]"
              >
                {n.label}
              </Link>
            ))}
          </nav>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-5 lg:px-8">{children}</main>

      <footer className="border-t border-[var(--hairline)] px-4 py-4 lg:px-8">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1">
            <p className="text-[13px] font-medium text-[var(--ink-2)]">Meal QC · built by team altuhraK</p>
            <p className="meta">
              Visual inspection only. Does not establish microbiological safety, nutritional composition, or measured
              food weight. Demo data is synthetic.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
