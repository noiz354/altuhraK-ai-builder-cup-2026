export type Role = "CREW" | "SUPERVISOR" | "ADMIN";

export type Label = "meal_complete" | "missing_component" | "uncertain";

export type ReviewStatus = "UNVERIFIED" | "REVIEW_PENDING" | "APPROVED" | "REJECTED";

export type ExecutionStatus = "CREATED" | "RUNNING" | "COMPLETED" | "FAILED";

export type Disposition = "ACCEPT" | "HOLD" | "REJECT";

export interface Prediction {
  predicted_label: Label | string;
  regions: Array<{ x: number; y: number; w: number; h: number }>;
  needs_review: boolean;
  confidence_score: null;
  evidence_ids: string[];
}

export interface Manifest {
  manifest_id: string;
  version: number;
  name: string;
  components: Array<{ key: string; label: string }>;
  note: string;
}

export interface Inspection {
  inspection_id: string;
  revision: number;
  role: Role;
  actor_id: string;
  tenant_id: string;
  kitchen_id: string;
  shift_id: string;
  batch_id: string;
  manifest_id: string;
  manifest_version: number;
  image_id: string;
  image_sha256: string;
  analysis_sha256: string;
  size_bytes: number;
  image_width: number;
  image_height: number;
  storage_path: string;
  execution_status: ExecutionStatus;
  review_status: ReviewStatus;
  qc_disposition: Disposition | null;
  prediction: Prediction | null;
  evidence_ids: string[];
  model_version: string | null;
  prompt_version: string;
  schema_version: string;
  created_at: string;
  latency_ms?: number;
  reviewed_by?: string;
  reviewed_at?: string;
  review_comment?: string;
  run_id?: string;
  errors?: Array<{ code: string; message: string }>;
  /** Provenance. Absent on records written before the classification existed. */
  inference_status?: InferenceStatus;
  prediction_source?: PredictionSource;
  provider_http_status?: number | null;
  provider_request_id?: string | null;
}

export interface AuditEvent {
  seq: number;
  event: string;
  payload: Record<string, unknown>;
}

export interface InspectionDetail extends Inspection {
  audit: AuditEvent[];
  manifest: Manifest;
}

export interface InspectionSummary {
  inspection_id: string;
  revision: number;
  kitchen_id: string;
  shift_id: string;
  batch_id: string;
  image_id: string;
  execution_status: ExecutionStatus;
  review_status: ReviewStatus;
  qc_disposition: Disposition | null;
  created_at: string;
}

/**
 * Milestone vocabulary agreed with the backend. The UI must never render a
 * deterministic baseline as a model finding: INFERENCE_SUCCEEDED is the only
 * status that licenses "the model produced this".
 */
export type InferenceStatus =
  | "NOT_REQUESTED"
  | "INFERENCE_BLOCKED"
  | "PROVIDER_INVOKED"
  | "PROVIDER_RESPONDED"
  | "INFERENCE_SUCCEEDED"
  | "INFERENCE_FAILED"
  | "NOT_RECORDED";

export type PredictionSource = "model" | "baseline" | "none";

export interface Overview {
  inspections_total: number;
  today: number;
  unverified: number;
  pending_review: number;
  approved: number;
  rejected: number;
  uncertain_predictions: number;
  failed_inference: number;
  labels: Record<string, number>;
  inference_status: Record<string, number>;
  failure_categories: Record<string, number>;
  model_inference_count: number;
  baseline_only_count: number;
  storage_bytes: number;
  storage_budget_bytes: number;
  storage_measured: boolean;
  activity: Array<{
    inspection_id: string;
    event: string;
    inference_status: InferenceStatus;
    prediction_source: PredictionSource;
    model_version: string | null;
    at: string;
  }>;
}

export interface AgentToolCall {
  tool: string;
  args: Record<string, unknown>;
}

export interface ProposedAction {
  kind: "create_followup_task";
  description: string;
  inspection_ids: string[];
}

export interface AgentReply {
  answer: string;
  tool_calls: AgentToolCall[];
  proposed_actions: ProposedAction[];
  grounded: boolean;
  disclaimer: string;
  /** Who produced the answer: Gemini function calling, or the deterministic fallback. */
  engine?: "gemini" | "rules";
  model_id?: string | null;
  latency_ms?: number | null;
  fallback_reason?: string | null;
}

export interface QcReport {
  inspection_id: string;
  inspection_revision: number;
  image_sha256: string;
  manifest_version: number;
  prediction: Prediction | null;
  evidence_ids: string[];
  model_version: string | null;
  prompt_version: string;
  schema_version: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
  review_decision: ReviewStatus | null;
  qc_disposition: Disposition | null;
  report_generated_at: string;
  report_status: string;
  report_snapshot_hash: string;
  disclaimer: string;
}

export interface ApiError {
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
}
/* ------------------------------------------------------------ illness claims */

export type Symptom =
  | "nausea"
  | "vomiting"
  | "diarrhea"
  | "abdominal_pain"
  | "fever"
  | "headache"
  | "dizziness"
  | "other";

export type ReporterType = "parent" | "student" | "teacher" | "school_staff" | "health_worker" | "other";

export type HealthPriority = "URGENT" | "HIGH" | "ROUTINE";

export type IncidentStatus =
  | "OPEN"
  | "ESCALATED_HEALTH"
  | "FIELD_VERIFICATION"
  | "CLOSED_CONFIRMED"
  | "CLOSED_UNSUBSTANTIATED";

export interface ClaimSignal {
  code: string;
  kind: "integrity" | "corroborating";
  weight: number;
  summary: string;
  detail: string;
  claim_ids: string[];
}

export interface ClaimAiAssessment {
  summary: string | null;
  pattern_assessment?: "consistent_with_outbreak" | "mixed" | "inconsistent_with_records" | "insufficient_data";
  observations?: Array<{ text: string; claim_ids: string[] }>;
  verification_steps?: string[];
  health_actions?: string[];
  source: "model" | "none";
  inference_status: InferenceStatus;
  error: string | null;
  model_id: string | null;
  http_status: number | null;
  latency_ms: number | null;
  generated_at: string;
}

export interface ClaimDecision {
  status: IncidentStatus;
  comment: string;
  actor: string;
  at: string;
  integrity_score: number;
  health_priority: HealthPriority;
}

export interface ClaimIncident {
  incident_id: string;
  kitchen_id: string;
  meal_date: string;
  status: IncidentStatus;
  integrity_score: number;
  integrity_level: "low" | "medium" | "high";
  health_priority: HealthPriority;
  signals: ClaimSignal[];
  corroborating: ClaimSignal[];
  stats: {
    claims: number;
    affected_reported: number;
    portions_served: number;
    schools_claimed: string[];
    schools_served: string[];
    sought_medical: number;
    hospitalized: number;
    first_submitted: string | null;
    last_submitted: string | null;
  };
  next_steps: string[];
  ai: ClaimAiAssessment | null;
  decisions: ClaimDecision[];
}

export interface ClaimRecord {
  claim_id: string;
  school_id: string;
  reporter_type: ReporterType;
  affected_count: number;
  symptoms: Symptom[];
  onset_at: string;
  sought_medical: boolean;
  hospitalized: boolean;
  description: string;
  channel: string;
  submitted_at: string;
  contact_ref: string;
  photo: { ref: string } | null;
}

export interface ClaimIncidentDetail extends ClaimIncident {
  services: Array<{ school_id: string; portions_served: number; served_at: string; batch_id: string }>;
  claims: ClaimRecord[];
  audit: AuditEvent[];
}

export interface ClaimSubmission {
  kitchen_id: string;
  school_id: string;
  meal_date: string;
  reporter_type: ReporterType;
  contact: string;
  affected_count: number;
  symptoms: Symptom[];
  onset_at: string;
  sought_medical: boolean;
  hospitalized: boolean;
  description: string;
  photo_base64?: string;
}

// ---------------------------------------------------------------- supply

export type InsightCategory = "food_safety" | "stock" | "cost" | "logistics" | "supplier";
export type Severity = "high" | "medium" | "low";

export interface Supplier {
  supplier_id: string;
  name: string;
  type: string;
  location: string;
  distance_km: number;
  cold_chain: boolean;
  certifications: string[];
}

export interface LotFlag {
  code: string;
  category: InsightCategory;
  severity: Severity;
  title: string;
  detail: string;
  action: string;
}

export interface SupplyLot {
  lot_id: string;
  kitchen_id: string;
  ingredient: string;
  label: string;
  category: string;
  chilled: boolean;
  quantity: number;
  unit: string;
  unit_price: number;
  reference_price: number;
  dispatched_at: string;
  received_at: string;
  promised_at: string | null;
  arrival_temp_c: number | null;
  use_by: string;
  receiving_status: "ACCEPTED" | "REJECTED";
  receiving_note: string;
  used_in: Array<{ meal_date: string; batch_id: string; qty: number }>;
  transit_min: number;
  stock_remaining: number;
  supplier: Supplier;
  flags: LotFlag[];
  qty_used?: number;
}

export interface SupplyInsight extends LotFlag {
  insight_id: string;
  lot_ids: string[];
  supplier_ids: string[];
  meal_dates: string[];
}

export interface SupplierScore extends Supplier {
  ingredients: string[];
  lots: number;
  rejected: number;
  spend_idr: number;
  avg_transit_min: number;
  on_time_pct: number | null;
  temp_breaches: number;
  price_index: number;
}

export interface SupplyAi {
  summary: string | null;
  insights: Array<{
    category: InsightCategory;
    title: string;
    detail: string;
    action: string;
    lot_ids: string[];
    supplier_ids: string[];
  }>;
  source: "model" | "none";
  inference_status: string;
  error: string | null;
  model_id: string | null;
  latency_ms: number | null;
  generated_at: string;
}

export interface SupplyOverview {
  kitchen_id: string;
  as_of: string;
  kpis: {
    window_days: number;
    lots: number;
    suppliers: number;
    portions: number;
    spend_idr: number;
    cost_per_portion_idr: number | null;
    avg_distance_km: number | null;
    local_share_pct: number | null;
    avg_perishable_transit_min: number | null;
    on_time_pct: number | null;
    stock_value_idr: number;
    rejected_lots: number;
  };
  insights: SupplyInsight[];
  suppliers: SupplierScore[];
  stock: Array<{
    ingredient: string;
    label: string;
    unit: string;
    on_hand: number;
    daily_use: number;
    days_cover: number | null;
    value_idr: number;
    fresh_daily: boolean;
  }>;
  price_trends: Array<{
    ingredient: string;
    label: string;
    unit: string;
    reference: number;
    latest: number;
    change_pct: number;
    points: Array<{ date: string; price: number }>;
  }>;
  lots: SupplyLot[];
  reference_note: string;
  ai: SupplyAi | null;
}

export interface SupplyTrace {
  kitchen_id: string;
  meal_date: string;
  batch: { batch_id: string; portions: number } | null;
  lots: SupplyLot[];
  suppliers: number;
  flags_total: number;
  high_flags: number;
  max_distance_km: number | null;
}

export interface SupplyCatalog {
  suppliers: Supplier[];
  ingredients: Array<{ ingredient: string; label: string; unit: string; chilled: boolean; ref: number }>;
}

export interface DeliveryInput {
  role: Role;
  kitchen_id: string;
  ingredient: string;
  supplier_id: string;
  quantity: number;
  unit_price: number;
  dispatched_at: string;
  received_at: string;
  arrival_temp_c?: number | null;
  use_by: string;
  receiving_status: "ACCEPTED" | "REJECTED";
  receiving_note?: string;
}
