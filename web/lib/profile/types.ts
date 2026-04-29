import type { components as openapi } from "@/lib/api/schema";

export type UserProfileRead = openapi["schemas"]["UserProfileRead"];
export type UserProfileUpdate = openapi["schemas"]["UserProfileUpdate"];
export type DietaryMode = UserProfileRead["dietary_mode"];

export const DIETARY_MODES: readonly DietaryMode[] = ["", "vegan", "vegetarian", "pescatarian"];

export const COMMON_ALLERGENS: readonly string[] = [
  "dairy",
  "eggs",
  "gluten",
  "nuts",
  "peanuts",
  "soy",
  "fish",
  "shellfish",
  "sesame",
];
