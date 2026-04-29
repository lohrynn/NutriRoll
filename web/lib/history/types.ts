import type { components as openapi } from "@/lib/api/schema";

export type HistoryEventRead = openapi["schemas"]["HistoryEventRead"];
export type HistoryEventCreate = openapi["schemas"]["HistoryEventCreate"];
export type HistoryEventKind = openapi["schemas"]["HistoryEventKind"];

export const HISTORY_KINDS: readonly HistoryEventKind[] = [
  "rolled",
  "cooked",
  "saved",
  "rated",
  "discarded",
];
