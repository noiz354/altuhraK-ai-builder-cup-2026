"use client";

import { createContext, useContext, useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import type { Role } from "@/lib/c05-types";

const Ctx = createContext<{
  role: Role;
  setRole: (r: Role) => void;
  kitchenId: string;
  setKitchenId: (k: string) => void;
} | null>(null);

export function useSession() {
  const value = useContext(Ctx);
  if (!value) throw new Error("useSession must be used inside Providers");
  return value;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<Role>("SUPERVISOR");
  const [kitchenId, setKitchenId] = useState("KITCHEN-A");
  const value = useMemo(
    () => ({ role, setRole, kitchenId, setKitchenId }),
    [role, kitchenId],
  );
  return (
    <Ctx.Provider value={value}>
      <AppShell>{children}</AppShell>
    </Ctx.Provider>
  );
}