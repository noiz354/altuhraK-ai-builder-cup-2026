"use client";

import { useEffect, useState } from "react";
import { c05 } from "@/lib/c05-client";
import type { Role } from "@/lib/c05-types";
import { Button } from "@/components/ui/button";
import { CopyId } from "@/components/copy-id";

export function DeliveryVerificationPanel({ role, kitchenId }: { role: Role; kitchenId: string }) {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [message, setMessage] = useState("");

  async function load() {
    try {
      const result = await c05.listDeliveryVerifications(role, kitchenId);
      setItems(result.verifications);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    let active = true;
    c05
      .listDeliveryVerifications(role, kitchenId)
      .then((result) => {
        if (active) setItems(result.verifications);
      })
      .catch((e: unknown) => {
        if (active) setMessage(e instanceof Error ? e.message : String(e));
      });
    return () => {
      active = false;
    };
  }, [role, kitchenId]);

  async function review(id: string, decision: "APPROVE" | "REJECT") {
    try {
      await c05.reviewDeliveryVerification(id, { role, decision });
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <section className="panel mt-4 p-4">
      <h3 className="label">Delivery verification</h3>
      <p className="meta mt-1">Visual score between approved QC image and student image.</p>
      {message ? <p className="mt-2 text-sm text-red-600">{message}</p> : null}
      {items.length === 0 ? (
        <p className="meta mt-3">No delivery verifications yet.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {items.map((item) => (
            <div key={String(item.verification_id)} className="well p-3">
              <p className="text-sm">
                <CopyId value={String(item.verification_id)} label="Verification" />
              </p>
              <p className="meta">
                Inspection: <CopyId value={String(item.inspection_id)} />
              </p>
              <p className="meta">Visual score: {String(item.visual_score)}</p>
              <p className="meta">Quality alert: {String(item.quality_alert)}</p>
              {Array.isArray(item.quality_alert_reasons) && item.quality_alert_reasons.length ? (
                <p className="text-sm text-red-600">
                  Alert: {(item.quality_alert_reasons as string[]).join(", ")}
                </p>
              ) : null}
              <p className="meta">Status: {String(item.status)}</p>
              {item.status === "PENDING_REVIEW" ? (
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={() => review(String(item.verification_id), "APPROVE")}>
                    Approve
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => review(String(item.verification_id), "REJECT")}>
                    Reject
                  </Button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}