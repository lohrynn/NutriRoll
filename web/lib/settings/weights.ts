/**
 * Client-side persistence of user-tunable scoring weights.
 *
 * Weights are stored in localStorage under `WEIGHTS_KEY`. The keys mirror
 * the backend `FeatureWeights` dataclass; defaults must be kept in sync
 * with `server/nutriroll/domain/roll.py`.
 */

export const WEIGHTS_KEY = "nutriroll.weights";

export const WEIGHT_KEYS = [
  "taste_match",
  "novelty",
  "price_fit",
  "nutrition_fit",
  "time_fit",
  "pantry_bonus",
  "direction_match",
  "macro_target_fit",
] as const satisfies readonly string[];

export type WeightKey = (typeof WEIGHT_KEYS)[number];

export const DEFAULT_WEIGHTS: Readonly<Record<WeightKey, number>> = Object.freeze({
  taste_match: 0.3,
  novelty: 0.2,
  price_fit: 0.2,
  nutrition_fit: 0.15,
  time_fit: 0.1,
  pantry_bonus: 0.05,
  direction_match: 0.25,
  macro_target_fit: 0.5,
});

export function loadWeights(): Record<WeightKey, number> {
  if (typeof window === "undefined") return { ...DEFAULT_WEIGHTS };
  const raw = window.localStorage.getItem(WEIGHTS_KEY);
  if (!raw) return { ...DEFAULT_WEIGHTS };
  try {
    const parsed = JSON.parse(raw) as Partial<Record<WeightKey, number>>;
    const merged: Record<WeightKey, number> = { ...DEFAULT_WEIGHTS };
    for (const k of WEIGHT_KEYS) {
      const v = parsed[k];
      if (typeof v === "number" && Number.isFinite(v) && v >= 0) {
        merged[k] = v;
      }
    }
    return merged;
  } catch {
    return { ...DEFAULT_WEIGHTS };
  }
}

export function saveWeights(weights: Record<WeightKey, number>): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(WEIGHTS_KEY, JSON.stringify(weights));
}

export function clearWeights(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(WEIGHTS_KEY);
}

/**
 * Returns the stored weights iff any differ from defaults, otherwise null.
 * Use this when building roll requests so we omit `weights` entirely when
 * the user has never customized them (keeps server-defaulted behavior).
 */
export function loadWeightsForRoll(): Record<WeightKey, number> | null {
  const w = loadWeights();
  for (const k of WEIGHT_KEYS) {
    if (w[k] !== DEFAULT_WEIGHTS[k]) return w;
  }
  return null;
}
