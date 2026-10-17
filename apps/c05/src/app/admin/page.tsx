"use client";

import { AdminCommandCenter } from "@/components/admin-command-center";
import { HowItWorks } from "@/components/how-it-works";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/providers";

export default function AdminPage() {
  const { role, kitchenId } = useSession();
  return (
    <div className="grid gap-5">
      {/* min-w-0: grid children default to min-width:auto, so the review table's
          min-content width (six columns) would otherwise widen the whole column
          and push horizontal scroll onto the page. With min-w-0 the table's own
          overflow-x-auto container takes effect and the page stays 390px clean. */}
      <div className="min-w-0">
        <PageHeader
          step={2}
          stage="Before serving · Supervisor"
          title="Review meal checks"
          gap="An automatic check is not a decision. Someone accountable has to accept, hold or reject each batch."
          goal="Open a pending check, compare the result with the meal list, and record your decision. It is final and audited."
        />
        <div className="mt-4">
          <HowItWorks
            open={false}
            steps={[
              { title: "Scan the tiles", body: "Counts by state. Amber means waiting for a person." },
              { title: "Open a row", body: "Filter the review queue and press Open." },
              { title: "Check the evidence", body: "Check result vs the expected components." },
              { title: "Decide", body: "Pick ACCEPT, HOLD or REJECT, then approve or reject. Final and audited." },
            ]}
          />
        </div>
        <div className="mt-4">
          <AdminCommandCenter role={role} kitchenId={kitchenId} />
        </div>
      </div>
    </div>
  );
}
