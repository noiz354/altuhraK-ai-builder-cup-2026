# Data contract — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

[shared contracts](../../../docs/shared/runtime-contract.md); local fixtures `SYNTHETIC_ONLY`. No external dataset required for plumbing/baseline.

## Input fields
`images:[{image_id:str,asset_path:str,width:int,height:int}]; annotations:[{image_id:str,label:str,boxes:[{x:int,y:int,w:int,h:int}]}]`

## Run params
`{image_id:str}`

## Domain result
`{predicted_label:str,regions:[{x:int,y:int,w:int,h:int}],needs_review:bool,evidence_ids:[str]}`

Notation: str/int/float/bool/arrays/object; nullable only where `|null` or BR-001 explicitly permits null. Decimal physical quantities finite >=0; counts/amounts nonnegative integers unless result delta can be signed. Currency exact uppercase code; no implicit FX. ISO dates YYYY-MM-DD; timestamps require timezone and normalize UTC.
IDs unique per collection; reference IDs must resolve unless [spec](spec.md) explicitly models unmatched records. Reject unknown fields, blank IDs, nonfinite numbers. `object` only for catalog attributes with primitive values. If a rule needs a field absent from this contract, update the canonical schema before implementing; never silently infer it.

Evidence: `C05:collection:record_id[:page_or_segment]`; input rows immutable in a snapshot. Labels/answers reserved for baseline scoring/evaluation must be omitted from generative explanation context when revealing them would violate spec (e.g. tutoring answer before success).

Storage local SQLite for runs/reviews; fixture JSON/CSV/assets local. Cloud adapters optional in [architecture](architecture.md). No application database exists yet.

## Storage policy (C05)
- Hard cap: 10 GB total for datasets, model artifacts, logs, demo assets, caches, and experiments.
- Synthetic fixtures only unless a licensed dataset is explicitly added with source and license.
- Do not commit binaries, checkpoints, image caches, or generated exports exceeding the cap.
- Remove or regenerate interim artifacts before adding new data.
