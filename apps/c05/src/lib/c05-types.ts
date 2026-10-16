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