import type { components as openapi } from "@/lib/api/schema";

export type UserProfileRead = openapi["schemas"]["UserProfileRead"];
export type UserProfileUpdate = openapi["schemas"]["UserProfileUpdate"];
export type LLMConfigRead = openapi["schemas"]["LLMConfigRead"];
export type LLMConfigUpdate = openapi["schemas"]["LLMConfigUpdate"];
export type DietaryMode = UserProfileRead["dietary_mode"];
export type LLMProvider = LLMConfigRead["provider"];
export type LLMFeature = NonNullable<LLMConfigRead["enabled_features"]>[number];

export const DIETARY_MODES: readonly DietaryMode[] = ["", "vegan", "vegetarian", "pescatarian"];
export const LLM_FEATURES: readonly LLMFeature[] = [
  "component_creation",
  "prompt_rolls",
  "recipe_polish",
  "weekly_recaps",
];
export const LLM_PROVIDERS: readonly LLMProvider[] = [
  "openai",
  "anthropic",
  "google",
  "ollama",
  "custom",
];

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
