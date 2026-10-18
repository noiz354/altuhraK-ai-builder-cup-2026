"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { c05, C05Error } from "@/lib/c05-client";
import type { AgentReply, Role } from "@/lib/c05-types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

const SUGGESTIONS = [
  "Rangkum inspeksi dapur ini",
  "Kenapa inspeksi ini perlu review?",
  "Tampilkan inspeksi saya yang masih pending",
  "Buat tindak lanjut untuk inspeksi uncertain",
];

/**
 * Minimalist surface: warm neutral, no gradients, no shadow lift.
 * Every tool call is visible, and writes are never executed without a
 * separate explicit confirm step.
 */
export function OperationsAgent({
  role,
  kitchenId,
  inspectionId,
}: {
  role: Role;
  kitchenId: string;
  inspectionId?: string;
}) {
  const [question, setQuestion] = useState("");
  const [reply, setReply] = useState<AgentReply | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>(SUGGESTIONS);
  const [rating, setRating] = useState<"up" | "down" | null>(null);
  const [feedback, setFeedback] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");

  useEffect(() => {
    let active = true;
    c05
      .agentSuggestions(role)
      .then((result) => {
        if (active && result.suggestions.length) setSuggestions(result.suggestions);
      })
      .catch(() => {
        if (active) setSuggestions(SUGGESTIONS);
      });
    return () => {
      active = false;
    };
  }, [role]);

  async function ask(text: string) {
    const q = text.trim();
    if (!q) return;
    setLastQuestion(q);
    setBusy(true);
    setError("");
    try {
      setRating(null);
      setFeedback("");
      setFeedbackStatus("");
      setReply(
        await c05.agentChat({
          role,
          question: q,
          ...(inspectionId ? { inspection_id: inspectionId } : {}),
        }),
      );
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!pendingAction) return;
    setBusy(true);
    try {
      await c05.confirmAction(pendingAction, role);
      setNote("Follow-up task created and written to the audit trail.");
      setPendingAction(null);
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel flex h-full min-h-[420px] flex-col p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-[20px] leading-[26px] font-semibold">Operations agent</h2>
        <Badge variant="outline" className="font-mono">
          {role}
        </Badge>
      </div>
      <p className="meta mt-1">
        {kitchenId} · read-only retrieval unless a write is explicitly confirmed
      </p>

      <ScrollArea className="mt-3 max-h-[420px]">
        <div className="flex flex-col gap-3 pr-3">
          {!reply && !busy ? (
            <div className="well p-4">
              <p className="text-[15px] leading-[22px]">
                Ask about real inspection records. The agent retrieves from this kitchen scope only and
                never invents counts or evidence IDs.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {suggestions.map((s) => (
                  <Button key={s} type="button" size="sm" variant="outline" onClick={() => ask(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          ) : null}

          <AnimatePresence initial={false}>
            {busy ? (
              <motion.div
                key="busy"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.12 }}
                className="well px-3 py-2"
              >
                <p className="meta">Retrieving authorized records…</p>
              </motion.div>
            ) : null}
          </AnimatePresence>

          {reply ? (
            <motion.div
              key="reply"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.12 }}
              className="flex flex-col gap-3"
            >
              <div className="rounded-[var(--r-control)] border border-[var(--hairline)] p-3">
                <p className="text-[15px] leading-[22px]">{reply.answer}</p>
                <p className="meta mt-2">{reply.disclaimer}</p>
              </div>

              {reply.tool_calls.length > 0 ? (
                <div>
                  <p className="label">Tool execution</p>
                  <ul className="mt-1.5 space-y-1">
                    {reply.tool_calls.map((t, i) => (
                      <li key={`${t.tool}-${i}`} className="well mono px-3 py-2">
                        <span className="text-[var(--ink)]">{t.tool}</span>{" "}
                        <span className="text-[var(--ink-3)]">
                          {Object.entries(t.args)
                            .map(([k, v]) => `${k}=${String(v)}`)
                            .join(" ") || "(no args)"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {reply.proposed_actions.map((a, i) => (
                <div key={i} className="rounded-[var(--r-control)] border border-[var(--review)] p-3">
                  <p className="label text-[var(--review)]">PROPOSED WRITE — needs your confirmation</p>
                  <p className="mt-1 text-[15px] leading-[22px]">{a.description}</p>
                  <p className="mono mt-1 text-[var(--ink-3)]">
                    {a.inspection_ids.length} inspection(s): {a.inspection_ids.join(", ") || "none"}
                  </p>
                  {pendingAction ? (
                    <p className="meta mt-2">Open the admin queue to confirm this action.</p>
                  ) : role === "ADMIN" ? (
                    <Button type="button" className="mt-2 h-11" onClick={confirm} disabled={busy}>
                      Confirm and create task
                    </Button>
                  ) : (
                    <p className="meta mt-2">Only ADMIN may execute this write.</p>
                  )}
                </div>
              ))}

              <div className="well p-3">
                <p className="label">Rate this answer</p>
                <div className="mt-2 flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant={rating === "up" ? "default" : "outline"}
                    onClick={() => setRating("up")}
                  >
                    👍 Helpful
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={rating === "down" ? "default" : "outline"}
                    onClick={() => setRating("down")}
                  >
                    👎 Not helpful
                  </Button>
                </div>
                <Textarea
                  className="mt-2"
                  placeholder="Optional feedback to improve the agent"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                />
                <Button
                  type="button"
                  size="sm"
                  className="mt-2"
                  disabled={!rating || busy}
                  onClick={async () => {
                    if (!rating || !reply) return;
                    setBusy(true);
                    try {
                      await c05.agentFeedback({
                        role,
                        question: lastQuestion,
                        answer: reply.answer,
                        rating,
                        feedback,
                      });
                      setFeedbackStatus("Feedback saved. Thank you.");
                      setFeedback("");
                    } catch (e) {
                      setError(e instanceof C05Error ? e.message : String(e));
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Submit feedback
                </Button>
                {feedbackStatus ? <p className="meta mt-2">{feedbackStatus}</p> : null}
              </div>
            </motion.div>
          ) : null}
        </div>
      </ScrollArea>

      {note ? <p className="mt-2 text-[13px] text-[var(--pass)]">{note}</p> : null}
      {error ? <p className="mt-2 text-[13px] text-[var(--defect)]">{error}</p> : null}

      <form
        className="mt-3 flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          placeholder="Ask about inspections in your scope…"
          aria-label="Ask the operations agent"
        />
        <Button type="submit" className="h-12" disabled={busy || question.trim().length === 0}>
          Ask
        </Button>
      </form>
    </div>
  );
}