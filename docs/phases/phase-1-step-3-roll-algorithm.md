# Phase 1 Step 3 — Roll Algorithm

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 34/34 ✓ vitest 6/6 ✓

---

## What was built

The deterministic roll algorithm from vision §"Logic 2. Roll Algorithm". Pure functions only — no FastAPI, no SQLAlchemy, no LLM (vision §6 forbids LLM-as-recommender). Input: a list of `Component` + a `RollRequest`. Output: a `RolledBowl` with per-slot scores and top-2 reason strings.

Steps implemented:
- **A** Hard filters (category, blacklist, dietary mode, allergens, time budget, forced cooking method)
- **B** Feature scoring `s = Σ wᵢ · fᵢ` over `taste_match`, `novelty`, `price_fit`, `nutrition_fit`, `time_fit`, `pantry_bonus`. Implements with-data features (`novelty`, `nutrition_fit`, `time_fit`); neutralises others until profile data exists.
- **C** Greedy assembly with numerically-stable softmax sampling at temperature `T`.
- **D** Pairing rules as a soft validator (too many bold/spicy; topping without crunchy element). On violation, drop the lowest-scoring slot and resample, up to `max_resamples` times.
- **E** `reroll_slot(...)` re-rolls a single slot, excluding the previously-chosen component to bias for novelty.
- **F** Top-2 contributing features per chosen component → human-readable reason strings.

## Files created

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/roll.py` | Public types: `SlotSpec`, `FeatureWeights`, `RollRequest`, `ChosenComponent`, `RolledBowl`, `EmptyCandidatePoolError`. Public functions: `filter_candidates`, `score_component`, `check_pairing`, `roll`, `reroll_slot`. |
| `server/tests/test_roll_algorithm.py` | 12 tests. Hypothesis property tests: blacklisted never passes filter, allergen-excluded never passes, time-budget eliminates slow components, filtered pool only contains requested category. Pairing rule tests for too-many-bold and topping-without-crunch. Concrete tests: one-per-slot with explanations, deterministic with seed, raises on empty pool, reroll changes only target slot, score uses weights. |

## Key technical decisions

| Decision | Reason |
|---|---|
| Frozen slotted dataclasses for all I/O types | Matches Step 1 component domain. Cheap, immutable, hashable, no framework. |
| Numerically-stable softmax (`exp(s - max(s))`) | Avoids overflow when scores or `1/T` get large. |
| `random.Random(request.seed)` (with `# noqa: S311`) | Recommendation rolls are not cryptographic. The S311 noqa is annotated with the rationale. |
| Step D as soft post-validator (not hard filter) | Per vision: pairing is preference, not constraint. Resampling lowest-scoring slot is the simplest path to a clean bowl without restarting the whole roll. |
| Neutral-score (0.5) for taste/price features | We don't have user-profile data yet. Setting them neutral lets weights still influence ordering once profile data ships, without faking values. |
| No LLM entry point | Vision §6 hard rule: LLM is generative and explanatory only, never the recommender. |

## Invariants added (must not be regressed)

- `roll(...)` is deterministic when `RollRequest.seed` is set.
- A blacklisted component (either via `Component.blacklisted` or `RollRequest.blacklisted_ids`) must never appear in any rolled bowl.
- A component with allergens in `RollRequest.allergens_excluded` must never appear in any rolled bowl.
- The roll algorithm has zero dependencies on FastAPI, SQLAlchemy, or any LLM client.

## What's next (Phase 2)

- Expose `roll(...)` via a `POST /v1/roll` API endpoint with a Pydantic request schema.
- Frontend "Roll a bowl" page that calls the endpoint and renders slots + per-slot explanations.
- Persist user-profile data (taste/price/pantry) so the corresponding scoring features get real signal.
