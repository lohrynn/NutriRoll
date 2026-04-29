import type { components as openapi } from "@/lib/api/schema";

export type Category = openapi["schemas"]["Category"];
export type CookingMethod = openapi["schemas"]["CookingMethod"];
export type PortionUnit = openapi["schemas"]["PortionUnit"];
export type ComponentRead = openapi["schemas"]["ComponentRead"];
export type ComponentCreate = openapi["schemas"]["ComponentCreate"];
export type CookingMethodSpec = openapi["schemas"]["CookingMethodSpecSchema"];
export type Macros = openapi["schemas"]["MacrosSchema"];

/**
 * Well-known macro keys mirrored from the backend ``Macros.WELL_KNOWN_KEYS``.
 * The on-the-wire payload is open: clients may send additional numeric fields
 * (the backend persists them in the JSONB column). The form renders one input
 * per key in this array — adding a new well-known macro means appending here
 * plus an i18n key in ``messages/{en,de}.json#components.form.<key>``.
 */
export type MacroKey = "kcal" | "carbs_g" | "protein_g" | "fat_g" | "fiber_g";
export const MACRO_KEYS: readonly MacroKey[] = ["kcal", "carbs_g", "protein_g", "fat_g", "fiber_g"];

export const PORTION_UNITS: readonly PortionUnit[] = ["g", "ml", "pc"];

export function parseCsvList(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}
