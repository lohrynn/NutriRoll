import type { components as openapi } from "@/lib/api/schema";

export type HistoryEventRead = openapi["schemas"]["HistoryEventRead"];
export type HistoryEventCreate = openapi["schemas"]["HistoryEventCreate"];
export type HistoryEventKind = openapi["schemas"]["HistoryEventKind"];
export type HistoryRecapResponse = openapi["schemas"]["HistoryRecapResponse"];
export type RecapSchema = openapi["schemas"]["RecapSchema"];

export const HISTORY_KINDS: readonly HistoryEventKind[] = [
  "rolled",
  "cooked",
  "saved",
  "rated",
  "discarded",
];
