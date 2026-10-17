"use client";

import { ClaimsConsole } from "@/components/claims-console";
import { HowItWorks } from "@/components/how-it-works";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/providers";

export default function ClaimsPage() {
  const { role, kitchenId } = useSession();
  return (
    <div>
      <PageHeader
        step={4}
        stage="After serving · Supervisor or admin"
        title="Triage illness reports"
        gap="Real outbreaks arrive mixed with inflated or copy-pasted claims, and nobody checks them against what the kitchen actually served."
        goal="Open an incident, see where reports conflict with delivery records, trace that day's ingredients back to their suppliers, read the pattern summary, then escalate or verify with a reason. Health priority is never lowered."
      />
      <div className="mt-4">
        <HowItWorks
          tip={role === "ADMIN" ? "Empty list? Press “Load demo scenario”." : "Switch Role to ADMIN to load the demo scenario."}
          steps={[
            { title: "Pick an incident", body: "One kitchen, one meal date. Red badge = health priority." },
            { title: "Read the signals", body: "Each one shows a conflict with delivery records. Click it to see the reports." },
            { title: "Read the summary", body: "A plain-English summary of the pattern and suggested checks." },
            { title: "Decide with a reason", body: "Escalate, verify, or (Admin) close. Health follow-up always comes first." },
          ]}
        />
      </div>
      <section className="mt-4 grid gap-3 md:grid-cols-2" aria-label="Examples">
        {[
          {
            tone: "var(--defect)",
            tag: "Example A · looks like a real outbreak",
            title: "11 reports after one day's lunch, mostly from SDN-02",
            facts: [
              "Parents, a teacher and the Puskesmas all report, each in their own words",
              "Vomiting and diarrhoea 2–7 hours after lunch, one child admitted to hospital",
              "Nothing conflicts with what the kitchen served",
            ],
            action: "Escalate to the health office now, then trace that day's ingredients: the chicken arrived warm.",
          },
          {
            tone: "var(--review)",
            tag: "Example B · does not add up, verify first",
            title: "35 reports, 340 people sick, but only 230 portions served",
            facts: [
              "The same sentence sent from 3 phone numbers, one photo reused",
              "32 reports arrived within 12 minutes late at night",
              "Some say symptoms started before the meal was served",
            ],
            action: "Health priority stays URGENT: check on anyone sick, then verify by phone or a field visit before concluding.",
          },
        ].map((e) => (
          <div key={e.tag} className="panel p-4" style={{ borderLeft: `4px solid ${e.tone}` }}>
            <p className="meta">{e.tag}</p>
            <p className="mt-1 text-[16px] leading-[22px] font-semibold">{e.title}</p>
            <ul className="mt-2 flex flex-col gap-1 text-[13px] leading-[18px] text-[var(--ink-2)]">
              {e.facts.map((f) => (
                <li key={f}>• {f}</li>
              ))}
            </ul>
            <p className="mt-2 text-[13px] leading-[18px]">
              <strong>What to do:</strong> {e.action}
            </p>
          </div>
        ))}
      </section>
      <p className="meta mt-2">
        Both examples are in the demo data: switch to ADMIN and press &ldquo;Load demo scenario&rdquo; below to open them.
      </p>
      <div className="mt-4">
        <ClaimsConsole role={role} kitchenId={kitchenId} />
      </div>
    </div>
  );
}
