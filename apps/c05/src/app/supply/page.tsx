"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SupplyConsole } from "@/components/supply-console";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/providers";

function Console() {
  const { role, kitchenId } = useSession();
  // ?date=YYYY-MM-DD opens the trace on that meal date (linked from an illness incident).
  const date = useSearchParams().get("date");
  return <SupplyConsole role={role} kitchenId={kitchenId} initialDate={date} />;
}

export default function SupplyPage() {
  const { kitchenId } = useSession();
  return (
    <div className="flex flex-col gap-4">
      <Link href="/claims" className="text-[14px] font-medium text-[var(--action)] underline underline-offset-2">
        ← Back to illness reports
      </Link>
      <PageHeader
        stage="Ingredient trace · Opened from an illness report"
        title={`Ingredients and suppliers at ${kitchenId}`}
        gap="Nobody can say quickly where an ingredient came from, how long it travelled, how warm it arrived or whether it cost too much, so problems surface only after people eat."
        goal="Pick the meal date to see every lot used that day and where it came from. Every lot is checked for temperature, transit, use-by, stock and price, and the checks are combined into a short brief."
      />
      <Suspense fallback={<p className="meta">Loading…</p>}>
        <Console />
      </Suspense>
    </div>
  );
}
