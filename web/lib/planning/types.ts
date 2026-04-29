import type { components as openapi } from "@/lib/api/schema";

export type SavedMealRead = openapi["schemas"]["SavedMealRead"];
export type SavedMealCreate = openapi["schemas"]["SavedMealCreate"];
export type PlannedMealRead = openapi["schemas"]["PlannedMealRead"];
export type PlannedMealCreate = openapi["schemas"]["PlannedMealCreate"];
export type PlannedMealUpdate = openapi["schemas"]["PlannedMealUpdate"];
export type MealSlot = openapi["schemas"]["MealSlot"];
export type PlannedStatus = openapi["schemas"]["PlannedStatus"];

export const MEAL_SLOTS: readonly MealSlot[] = ["breakfast", "lunch", "dinner", "snack"];

export const PLANNED_STATUSES: readonly PlannedStatus[] = [
  "planned",
  "shopped",
  "cooked",
  "skipped",
];
