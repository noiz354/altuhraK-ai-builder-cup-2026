import type {
  AgentReply,
  ApiError,
  Disposition,
  Inspection,
  InspectionDetail,
  InspectionSummary,
  Manifest,
  Overview,
  QcReport,
  Role,
} from "./c05-types";

/**
 * All browser traffic goes through the Next.js server-side proxy.
 * The QC service binds to loopback and rejects cross-origin callers, so the
 * browser must never address it directly.
 */
const BASE = "/api/proxy";

export class C05Error extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "C05Error";
  }
}

function describe(payload: ApiError): string {
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((d) => d.msg).join("; ");
  }
  return "Request failed";
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      cache: "no-store",
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new C05Error(
      "QC service unreachable. Start it with: python projects/common/C05-visual-defect-detection/src/c05_entry.py",
      0,
    );
  }
  if (!response.ok) {
    let payload: ApiError = { detail: response.statusText };
    try {
      payload = (await response.json()) as ApiError;
    } catch {
      /* non-JSON error body */
    }
    throw new C05Error(describe(payload), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const c05 = {
  health: () => call<{ status: string; project_id: string; mode: string }>("/health"),

  manifest: (role: Role) => call<{ manifests: Manifest[] }>(`/api/manifests?role=${role}`),

  createInspection: (input: {
    role: Role;
    kitchen_id: string;
    shift_id?: string;
    batch_id?: string;
    manifest_version: number;
    mime_type: string;
    data_base64: string;
    idempotency_key?: string;
  }) => call<Inspection>("/api/inspections", { method: "POST", body: JSON.stringify(input) }),

  listInspections: (params: { role: Role; kitchen_id?: string; review_status?: string }) => {
    const qs = new URLSearchParams({ role: params.role });
    if (params.kitchen_id) qs.set("kitchen_id", params.kitchen_id);
    if (params.review_status) qs.set("review_status", params.review_status);
    return call<{ inspections: InspectionSummary[]; count: number }>(
      `/api/inspections?${qs.toString()}`,
    );
  },

  inspection: (id: string, role: Role) =>
    call<InspectionDetail>(`/api/inspections/${id}?role=${role}`),

  run: (id: string, role: Role, mode: "baseline" | "ai") =>
    call<Inspection>(`/api/inspections/${id}/run`, {
      method: "POST",
      body: JSON.stringify({ role, mode }),
    }),

  review: (
    id: string,
    body: { role: Role; decision: "APPROVED" | "REJECTED"; qc_disposition: Disposition; comment?: string },
  ) =>
    call<Inspection>(`/api/inspections/${id}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  reinfer: (id: string, role: Role) =>
    call<Inspection>(`/api/inspections/${id}/reinfer`, {
      method: "POST",
      body: JSON.stringify({ role }),
    }),

  overview: (role: Role, kitchenId?: string) => {
    const qs = new URLSearchParams({ role });
    if (kitchenId) qs.set("kitchen_id", kitchenId);
    return call<Overview>(`/api/admin/overview?${qs.toString()}`);
  },

  report: (id: string, role: Role) => call<QcReport>(`/api/reports/${id}?role=${role}`),

  agentChat: (body: { role: Role; question: string; inspection_id?: string }) =>
    call<AgentReply>("/api/agent/chat", { method: "POST", body: JSON.stringify(body) }),

  confirmAction: (actionId: string, role: Role) =>
    call<Record<string, unknown>>(`/api/agent/actions/${actionId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ role }),
    }),
};