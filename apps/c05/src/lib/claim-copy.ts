import type { HealthPriority, IncidentStatus } from "./c05-types";

/**
 * Plain-language copy for claim signals. The code stays visible in small
 * type for audit; the title is what a supervisor reads first.
 */
export const SIGNAL_COPY: Record<string, { title: string; short: string; explain: string }> = {
  CLAIMS_EXCEED_PORTIONS: {
    title: "More people sick than meals served",
    short: "Over portions",
    explain: "The reported number of affected people at a school is higher than the portions this kitchen delivered there.",
  },
  NO_SERVICE_RECORD: {
    title: "School was not served that day",
    short: "Not served",
    explain: "The report names a school that has no delivery record from this kitchen on that date.",
  },
  ONSET_BEFORE_MEAL: {
    title: "Sick before the meal arrived",
    short: "Before meal",
    explain: "The reported symptom time is earlier than when the meal was served. Could be a typing mistake — check with the school.",
  },
  ONSET_OUTSIDE_WINDOW: {
    title: "Symptoms started very late",
    short: "Late onset",
    explain: "Symptoms began more than 72 hours after the meal, which is unusual for food poisoning from a cooked meal.",
  },
  DUPLICATE_CONTACT: {
    title: "Same phone, many reports",
    short: "Same phone",
    explain: "Several reports came from the same phone number.",
  },
  DUPLICATE_PHOTO: {
    title: "Same photo reused",
    short: "Same photo",
    explain: "The same (or almost the same) picture was attached to several reports.",
  },
  TEMPLATED_TEXT: {
    title: "Copy-paste wording",
    short: "Copy-paste",
    explain: "Several reports use nearly identical sentences.",
  },
  SUBMISSION_BURST: {
    title: "Many reports in minutes",
    short: "Burst",
    explain: "A large number of reports arrived within 15 minutes. Real outbreaks can do this too once news spreads, so it counts the least.",
  },
  MEDICAL_VISIT_REPORTED: {
    title: "Clinic or hospital visits",
    short: "Clinic visit",
    explain: "Reports (not flagged above) say someone saw a clinic, Puskesmas or doctor.",
  },
  HOSPITALIZATION_REPORTED: {
    title: "Hospital admissions",
    short: "Hospital",
    explain: "Reports (not flagged above) say someone was admitted to hospital.",
  },
  MULTI_SCHOOL_SPREAD: {
    title: "Several schools affected",
    short: "Multi-school",
    explain: "Unflagged reports come from more than one school served by this kitchen, which fits a problem in the kitchen itself.",
  },
  QC_FLAG_SAME_DAY: {
    title: "Visual QC flagged that day",
    short: "QC flag",
    explain: "Some tray inspections that day were incomplete or uncertain. Visual QC cannot detect contamination; treat as context only.",
  },
};

export function signalCopy(code: string) {
  return SIGNAL_COPY[code] ?? { title: code.replace(/_/g, " ").toLowerCase(), short: code, explain: "" };
}

export const HEALTH_COPY: Record<HealthPriority, string> = {
  URGENT: "Someone was hospitalised or several people needed a doctor. Act on health now.",
  HIGH: "Medical visits or 10+ affected. Contact the health office today.",
  ROUTINE: "Mild, few cases. Follow up and keep watching.",
};

export const STATUS_COPY: Record<IncidentStatus, { label: string; explain: string }> = {
  OPEN: { label: "Open", explain: "Nobody has decided yet." },
  ESCALATED_HEALTH: { label: "Escalated to health office", explain: "The health office has been told and leads the response." },
  FIELD_VERIFICATION: { label: "Field verification", explain: "Staff are checking delivery records and calling reporters back." },
  CLOSED_CONFIRMED: { label: "Closed · confirmed illness", explain: "Investigation found a real food-related illness." },
  CLOSED_UNSUBSTANTIATED: {
    label: "Closed · unsubstantiated",
    explain: "Records contradict the reports and medical follow-up is complete. Cannot be undone.",
  },
};
