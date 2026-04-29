# Phase 7 — Directions & Flavor System

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 80/80 ✓ vitest 12/12 ✓

---

## What was built

The vision §1 *Direction* concept: cuisine + mood chips and two flavor-axis sliders that nudge the roll algorithm without acting as hard filters. Plus a per-portion nutritional summary on the rolled bowl.

## Backend

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/direction.py` | `Direction`, `FlavorAxes`, `CUISINE_BOOSTS`, `MOOD_BOOSTS`, and `translate(direction) -> dict[str, float]`. Pure data + a single pure function. |
| `server/nutriroll/domain/roll.py` | `RollRequest.tag_boosts: Mapping[str, float]` (clipped to `[-1, 1]` per tag). New `direction_match` feature in `score_component` plus a matching `_top_reasons` line. `FeatureWeights.direction_match=0.25`. `reroll_slot` propagates `tag_boosts`. |
| `server/nutriroll/api/schemas/roll.py` | `DirectionSchema` + `FlavorAxesSchema`. `RollRequestSchema.direction` reduces to `tag_boosts` via `direction.translate()`; user-provided `tag_boosts` layer additively on top. |
| `server/nutriroll/api/routers/roll.py` | `reroll_one_slot` carries `tag_boosts` from the original request into the sub-request. |
| `server/tests/test_direction.py` | 7 tests: empty input, single cuisine, stacked overlapping tags, axis polarities, bad cuisine/axis range. |

## Frontend

| Path | Change |
|---|---|
| `web/components/roll-page.tsx` | New `DirectionState` (cuisines/moods sets + two axis sliders). New "Direction" Card between Constraints and the Roll button: pill-style toggle chips (`aria-pressed`) for cuisines & moods, two range sliders, and a "Clear" button. `buildRequestBody` now sends `direction: { cuisines, moods, axes }`; selecting `surprise_me` mood bumps softmax `temperature` by 0.5 to flatten the distribution. New per-portion nutrition strip on the bowl card: sums `macros_per_100g × default_portion.value/100` across slots and renders five `Badge`s (kcal in brand variant, the rest neutral). |
| `web/messages/en.json` + `web/messages/de.json` | Added `roll.direction.*` and `roll.nutrition.*` namespaces with parity. |
| `web/lib/api/schema.d.ts` | Regenerated via `make gen-openapi gen-client`. |

## Key decisions

- **Generic `tag_boosts` in the domain.** The roll algorithm doesn't know about "cuisines" or "moods" — it only knows tags and their boost values. The Direction schema and translator live one layer up at the API boundary, keeping the algorithm reusable for future inputs (Settings presets, Roll-a-Week vibes).
- **Boosts are additive, clipped to `[-1, 1]` per component.** Stacking many chips degrades gracefully instead of saturating one dimension.
- **Axis sliders polarity:** `bold_to_mild < 0` → bold/spicy/smoky boosted, mild penalised. `heavy_to_light > 0` → tangy/crunchy/herbaceous boosted, creamy/savory penalised. Sign of the slider matches its left-end label (negative = left).
- **`surprise_me` raises temperature, not flavor boosts.** It's a meta-direction about exploration, not taste.
- **Per-portion nutrition is an honest estimate.** Only components with `default_portion.unit == "g"` contribute (ml/pc unknown densities are skipped) — under-counting is preferable to inventing numbers.

## Invariants

- A component with no overlapping tags scores `direction_match = 0` (neutral). Direction never excludes anyone.
- `Direction.translate(empty)` returns `{}`. `RollRequest.tag_boosts={}` is the default.
- `roll(request).slots` always has the same shape regardless of direction selection.
