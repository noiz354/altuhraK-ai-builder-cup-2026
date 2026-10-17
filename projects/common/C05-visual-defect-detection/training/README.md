# C05 tuning pipeline

Scaffold for supervised tuning of Gemini on Vertex AI using collected meal photos,
including MBG portions served on households' own plates.

```
collected photos ─► manifest.jsonl ─► prepare ─► upload ─► tune ─► status ─► eval ─► serve
                                     validate     GCS      Vertex   endpoint  test split  C05_GEMINI_ENDPOINT
                                     dedupe
                                     group split
                                     SFT export
```

## 1. Dataset contract

One directory with `manifest.jsonl` and the images it references. One line per photo:

```json
{"image": "images/0001.jpg", "label": "missing_component", "missing": ["vegetable"],
 "plate_type": "home_plate", "group_id": "household-017", "source": "field_crew",
 "uncertain_reason": null, "boxes": []}
```

| field | values |
|---|---|
| `label` | `meal_complete`, `missing_component`, `uncertain` |
| `missing` | subset of `carbohydrate`, `protein`, `vegetable`; required for `missing_component`, empty for `meal_complete` |
| `plate_type` | `tray_compartment`, `home_plate`, `bowl`, `lunchbox`, `banana_leaf`, `other` |
| `group_id` | anything that makes photos look alike: household, kitchen-day, capture session |
| `source` | `synthetic`, `field_crew`, `parent_upload`, `other` |
| `uncertain_reason` | required for `uncertain`: `occluded_component`, `poor_lighting`, `label_ambiguous`, `blurred_image`, `component_out_of_frame`, `manifest_mismatch` |
| `boxes` | optional `[{x,y,w,h}]` in image pixels |

`group_id` matters most. Photos of the same family's plates are near-copies of each other.
If they land in both the train and test splits, every metric is inflated. Splits are made
per group, and near-duplicate photos across groups are dropped.

## 2. Run it

From `projects/common/C05-visual-defect-detection/`:

```bash
# synthetic stand-in data (pipeline test only; never report quality on it)
python training/pipeline.py synth --out training/data/synthetic

# validate + split + export Gemini SFT JSONL (train/validation; test is held out)
python training/pipeline.py prepare --data training/data/synthetic --build training/build/run1 \
    --gcs-prefix gs://YOUR_BUCKET/c05-tuning/run1

python training/pipeline.py upload --build training/build/run1 --gcs-prefix gs://YOUR_BUCKET/c05-tuning/run1

# dry run prints the request; --submit creates the billed job
python training/pipeline.py tune --gcs-prefix gs://YOUR_BUCKET/c05-tuning/run1 --base-model MODEL_ID
python training/pipeline.py tune --gcs-prefix gs://YOUR_BUCKET/c05-tuning/run1 --base-model MODEL_ID --submit
python training/pipeline.py status --job projects/P/locations/us-central1/tuningJobs/ID

# floor to beat, then the live model (base via GEMINI_MODEL, tuned via C05_GEMINI_ENDPOINT)
python training/pipeline.py eval --data training/data/synthetic --build training/build/run1 --predictor majority
python training/pipeline.py eval --data training/data/synthetic --build training/build/run1 --predictor gemini
```

Every step writes JSON into the build directory: `validation_report.json`, `prepare.json`,
`splits/*.jsonl`, `eval_*.json`.

## 3. Serve the tuned model

When `status` reports `JOB_STATE_SUCCEEDED`, it prints the endpoint. Set
`C05_GEMINI_ENDPOINT=projects/P/locations/us-central1/endpoints/ID` on the backend.
Inspections then call the tuned endpoint with no code change. Unset the variable to
roll back to the base model.

## Training/serving parity

Training examples are built from the same code that live requests use:
`shared_mvp.provider.build_prompt` for the prompt, `shared_mvp.domain.evidence` for
evidence IDs, and the same EXIF-upright, 4 MP-capped PNG preparation. The target is the
C05 output contract, the one the live domain validator enforces. If you change the prompt
or the output contract, re-export the dataset before tuning again.

## Before a real run

- **Base model.** Choose a Gemini model that Vertex supports for tuning in your region.
  `gemini-2.5-flash` retires on 2026-10-20, so don't tune on it.
- **Volume.** Aim for at least 100–500 examples, with every label at 10% or more. The
  validation report warns when the data falls short.
- **What to watch.** Check `missing_component_recall` per `plate_type` in the eval report.
  A missed incomplete meal is the costly error, and household plates are where it hides.
- **Privacy.** Parent-uploaded photos may show faces or homes. Crop or blur them before
  they enter the manifest; the pipeline does not do this for you.
