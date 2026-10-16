"use client";

import { AdminCommandCenter } from "@/components/admin-command-center";
import { OperationsAgent } from "@/components/operations-agent";
import { useSession } from "@/components/providers";

export default function AdminPage() {
  const { role, kitchenId } = useSession();
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
      {/* min-w-0: grid children default to min-width:auto, so the review table's
          min-content width (six columns) would otherwise widen the whole column
          and push horizontal scroll onto the page. With min-w-0 the table's own
          overflow-x-auto container takes effect and the page stays 390px clean. */}
      <div className="min-w-0">
        <p className="label text-[var(--brand)]">Admin command center</p>
        <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Operational control</h1>
        <div className="mt-4">
          <AdminCommandCenter role={role} kitchenId={kitchenId} />
        </div>
      </div>
      <aside className="min-w-0 xl:sticky xl:top-20 xl:h-fit">
        <OperationsAgent role={role} kitchenId={kitchenId} />
      </aside>
    </div>
  );
}
