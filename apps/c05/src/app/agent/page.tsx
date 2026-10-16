"use client";

import { useState } from "react";
import { OperationsAgent } from "@/components/operations-agent";
import { useSession } from "@/components/providers";
import { Label } from "@/components/ui/label";

export default function AgentPage() {
  const { role, kitchenId } = useSession();
  const [inspectionId, setInspectionId] = useState("");

  return (
    <div className="mx-auto w-full max-w-[720px]">
      <p className="label text-[var(--brand)]">Operations agent</p>
      <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Grounded assistant</h1>
      <p className="mt-1 text-[15px] leading-[22px] text-[var(--ink-2)]">
        Read-only retrieval limited to {kitchenId}. Write actions require an explicit confirmation step.
      </p>

      <div className="mt-4 flex flex-col gap-1.5 sm:max-w-[420px]">
        <Label htmlFor="inspection">Inspection id (optional)</Label>
        <input
          id="inspection"
          value={inspectionId}
          onChange={(e) => setInspectionId(e.target.value.trim())}
          placeholder="paste an inspection id"
          className="mono h-12 rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-3"
        />
      </div>

      <div className="mt-4">
        <OperationsAgent role={role} kitchenId={kitchenId} inspectionId={inspectionId || undefined} />
      </div>
    </div>
  );
}
