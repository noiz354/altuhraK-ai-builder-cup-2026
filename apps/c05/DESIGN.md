# C05 Field Crew + Admin + Agent — Design System

Direction: **calm industrial QC**. Evidence before opinion. One calm surface, four restrained semantic
colors, motion only where it reports state.

## Color tokens

| Token | Value | Use |
|---|---|---|
| `--surface-canvas` | `#F6F7F5` | page background |
| `--surface-raised` | `#FFFFFF` | panels, cards, tables |
| `--surface-sunken` | `#EEF1ED` | wells, code blocks, table headers |
| `--border-subtle` | `#E2E6E0` | hairlines, card edges |
| `--text-primary` | `#16211C` | headings, values |
| `--text-secondary` | `#55635B` | body, labels |
| `--text-tertiary` | `#8A968E` | meta, timestamps |
| `--brand-deep` | `#1F5B45` | product identity, admin chrome |
| `--action-primary` | `#2F6FED` | one primary action per view |
| `--state-review` | `#B7791F` | pending review, uncertainty |
| `--state-defect` | `#C0392B` | missing component, failure |
| `--state-pass` | `#2F855A` | approved, completed |

Rules: exactly one `--action-primary` element per viewport. Semantic colors never carry meaning alone,
always paired with a text label. No gradients. No glassmorphism.

## Typography scale

Base 16px, system sans (`ui-sans-serif` stack, Geist fallback). Mono for hashes, IDs and code.

| Token | Size / line | Use |
|---|---|---|
| `display` | 28/34 | screen title |
| `title` | 20/26 | panel heading |
| `body` | 15/22 | content |
| `label` | 13/18 uppercase-ish, `0.02em` | field labels, column heads |
| `meta` | 12/16 | timestamps, hashes |
| `mono` | 12/18 | IDs, hashes, JSON |

## Spacing scale

`4 · 8 · 12 · 16 · 24 · 32 · 48`. Dense tables use 8/12. Screen padding 16 on crew (360px), 32 on admin.

## Surfaces, radius, elevation

Radius: `8px` controls and cards, `12px` panels, `999px` badges only. Elevation is a single level:
`0 1px 2px rgba(22,33,28,.06)` plus a 1px `--border-subtle` edge. No shadows on hover.

## Motion

Only four permitted motions, all ≤ 200ms, all transform/opacity:
1. panel entry fade (120ms)
2. run-state change highlight (160ms)
3. progress bar width (200ms)
4. overlay box draw-in (160ms)

`prefers-reduced-motion` disables all. No decorative loops, no card-hover lift.

## Breakpoints

| Breakpoint | Layout |
|---|---|
| < 640px | Crew: single column, 48px bottom action bar, 64px targets |
| 640–1024px | Crew tablet: two-up capture + manifest |
| ≥ 1024px | Admin: fixed sidebar 240px, content max 1440px, tables at 12px meta |

## Component patterns

- **StatusBadge**: label + dot. `UNVERIFIED` always amber-outline, never filled green.
- **PredictionBlock**: bordered, `AI PREDICTION — UNVERIFIED` eyebrow, never inside a green card.
- **EvidenceRow**: mono ID, monospace hash truncated to 12 chars, click to copy.
- **StatCard**: label, value, and real record count. Zero state says "0 records", never a fake delta.
- **AgentToolRow**: tool name, args, and result count. Writes require an explicit confirm step.

## Accessibility

Focus-visible ring 2px `--action-primary`. All controls ≥ 44px (crew 48px). Text contrast ≥ 4.5:1.
Status never conveyed by color alone. Camera capture always has a file-input fallback.
`aria-live` on run state and agent answers.

## Boundaries that are design decisions, not policy

No confidence percentage is ever rendered (`confidence_score` is null by design).
Approved review and model prediction never share a visual treatment.