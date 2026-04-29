import type { components as openapi } from "@/lib/api/schema";

export type RollRequest = openapi["schemas"]["RollRequestSchema"];
export type RolledBowl = openapi["schemas"]["RolledBowlSchema"];
export type RolledSlot = openapi["schemas"]["RolledSlotSchema"];
export type SlotSpec = openapi["schemas"]["SlotSpecSchema"];

export const DEFAULT_SLOTS: readonly SlotSpec[] = [
  { category: "base", count: 1 },
  { category: "vegetable", count: 1 },
  { category: "sauce", count: 1 },
  { category: "topping", count: 1 },
];
