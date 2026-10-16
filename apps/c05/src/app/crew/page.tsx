"use client";

import { CrewInspection } from "@/components/crew-inspection";
import { useSession } from "@/components/providers";

export default function CrewPage() {
  const { role, kitchenId } = useSession();
  return (
    <div className="mx-auto w-full max-w-[560px]">
      <p className="label text-[var(--brand)]">Field crew</p>
      <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Today at {kitchenId}</h1>
      <p className="mt-1 text-[15px] leading-[22px] text-[var(--ink-2)]">
        One capture, one inspection request. Everything below is required before review.
      </p>
      <div className="mt-4">
        <CrewInspection role={role} kitchenId={kitchenId} />
      </div>
    </div>
  );
}
