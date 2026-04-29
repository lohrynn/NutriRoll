import type { components as openapi } from "@/lib/api/schema";

export type Recipe = openapi["schemas"]["RecipeSchema"];
export type RecipeBlock = openapi["schemas"]["RecipeBlockSchema"];
export type RecipeStep = openapi["schemas"]["RecipeStepSchema"];
export type BuildRecipeRequest = openapi["schemas"]["BuildRecipeRequestSchema"];
