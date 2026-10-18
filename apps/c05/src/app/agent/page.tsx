"use client";

import { OperationsAgent } from "@/components/operations-agent";
import { useSession } from "@/components/providers";

export default function AgentPage() {
  const { role, kitchenId } = useSession();
  return (
    <div className="mx-auto w-full max-w-[1120px]">
      <p className="label text-[var(--brand)]">Operations agent</p>
      <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Grounded assistant</h1>
      <p className="meta mt-1">
        Read-only retrieval limited to your kitchen. Write actions require an explicit confirmation step.
      </p>
      <div className="mt-4">
        <OperationsAgent role={role} kitchenId={kitchenId} />
      </div>
    </div>
  );
}