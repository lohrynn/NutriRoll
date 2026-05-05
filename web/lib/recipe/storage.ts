import type { RolledBowl } from "@/lib/roll/types";

/**
 * sessionStorage key under which the Roll page stashes the most recent
 * rolled meal so downstream pages can resume the user's flow without any
 * server-side session state.
 */
export const ROLLED_BOWL_STORAGE_KEY = "nutriroll.rolledBowl";

const DEFAULT_ROLLED_PORTIONS = 1;

export interface StoredRolledMeal {
  bowl: RolledBowl;
  portions: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isRolledBowl(value: unknown): value is RolledBowl {
  return (
    isRecord(value) &&
    Array.isArray(value.slots) &&
    value.slots.every(
      (slot) =>
        isRecord(slot) &&
        isRecord(slot.component) &&
        typeof slot.component.id === "string" &&
        typeof slot.component.name === "string",
    )
  );
}

function normalizePortions(value: unknown): number {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric) || numeric < 1) return DEFAULT_ROLLED_PORTIONS;
  return Math.max(1, Math.floor(numeric));
}

export function parseStoredRolledMeal(value: unknown): StoredRolledMeal | null {
  if (isRolledBowl(value)) {
    return {
      bowl: value,
      portions: DEFAULT_ROLLED_PORTIONS,
    };
  }
  if (
    isRecord(value) &&
    "bowl" in value &&
    isRolledBowl(value.bowl)
  ) {
    return {
      bowl: value.bowl,
      portions: normalizePortions(value.portions),
    };
  }
  return null;
}

export function readRolledMealFromStorage(): StoredRolledMeal | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(ROLLED_BOWL_STORAGE_KEY);
  if (!raw) return null;
  try {
    return parseStoredRolledMeal(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function writeRolledMealToStorage(meal: StoredRolledMeal): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(
    ROLLED_BOWL_STORAGE_KEY,
    JSON.stringify({
      bowl: meal.bowl,
      portions: normalizePortions(meal.portions),
    }),
  );
}
