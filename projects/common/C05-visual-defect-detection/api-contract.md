# API — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Use [shared runtime](../../../docs/shared/runtime-contract.md) for endpoint/state/error envelopes.
POST /api/datasets: `{"project_id":"C05","data": INPUT}`, INPUT from [data](data-design.md).
POST /api/runs: `{"dataset_id":"...","mode":"baseline|ai","params": {image_id:str}}`.
Successful domain result: `{predicted_label:str,regions:[{x:int,y:int,w:int,h:int}],needs_review:bool,evidence_ids:[str]}`; see shared envelope for evidence/status/revision.
Do not trust submitted result IDs/claims in review: review operates on existing stored run revision. Server owns evidence lookup and access checks. Domain validation/error cases in [spec](spec.md).
UI displays baseline, AI status, evidence and limitations separately. Empty/partial states must be visible; model unavailable is not success.
