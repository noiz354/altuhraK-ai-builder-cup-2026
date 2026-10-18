"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

/**
 * Renders an ID with a one-click copy button. Used everywhere an ID has to be
 * moved from one screen to another (e.g. inspection ID from the admin queue to
 * the student delivery page), so the value is never typed by hand.
 */
export function CopyId({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-1">
      {label ? <span className="meta">{label}</span> : null}
      <span className="mono break-all">{value}</span>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-7 px-2 text-xs"
        onClick={copy}
        aria-label={`Copy ${value}`}
      >
        {copied ? "Copied" : "Copy"}
      </Button>
    </span>
  );
}