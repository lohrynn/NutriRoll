import type { components as openapi } from "@/lib/api/schema";

export type Category = openapi["schemas"]["Category"];
export type CookingMethod = openapi["schemas"]["CookingMethod"];
export type PortionUnit = openapi["schemas"]["PortionUnit"];
export type ComponentRead = openapi["schemas"]["ComponentRead"];
export type ComponentCreate = openapi["schemas"]["ComponentCreate"];
export type CookingMethodSpec = openapi["schemas"]["CookingMethodSpecSchema"];

export const CATEGORIES: readonly Category[] = ["base", "vegetable", "sauce", "topping"];

export const PORTION_UNITS: readonly PortionUnit[] = ["g", "ml", "pc"];

export const ALLOWED_METHODS: Readonly<Record<Category, readonly CookingMethod[]>> = {
  base: [
    "boil",
    "steam",
    "blanch",
    "pan_fry",
    "roast",
    "air_fry",
    "grill",
    "bake",
    "toast",
    "raw",
    "no_prep",
    "custom",
  ],
  vegetable: [
    "boil",
    "steam",
    "blanch",
    "pan_fry",
    "roast",
    "air_fry",
    "grill",
    "bake",
    "toast",
    "raw",
    "no_prep",
    "custom",
  ],
  sauce: [
    "blend_cold",
    "blend_hot",
    "heat",
    "whisk_cold",
    "whisk_hot",
    "reduce",
    "saute_simmer",
    "no_prep",
    "custom",
  ],
  topping: ["boil", "toast", "pan_fry", "roast", "grill", "crumble", "no_prep", "custom"],
};

export function parseCsvList(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}
