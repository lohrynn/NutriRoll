# Phase 14 — Live cooking timers

**Status:** TODO (not started)

---

## Goal

The Cook page (`/cook`) currently shows static recipe steps. Add a
per-step countdown timer that runs in the background, fires a PWA
notification when done, and lets the user start/pause/reset.

This is one of the explicit unimplemented features called out in
`copilot-instructions.md`.

---

## Backend

- None. Recipe step durations already exist on the bowl snapshot.

## Frontend

- New `lib/cook/timers.ts` — small reducer-based timer registry keyed
  by step index, persisted to `sessionStorage` so a refresh doesn't lose
  state mid-cook.
- `cook-page.tsx`: a "Start" button per step that begins the
  countdown and a circular progress ring; auto-advance to next step
  optional (toggle).
- Service worker: register a notification on timer expiry (PWA already
  installed in Phase 0). Fall back to in-page audio/banner when
  notifications are denied.

## Decisions to make

- Audio cue (built-in beep vs. silent + visual)?
- Whether to allow multiple timers running in parallel (yes — parallel
  cook model already supports it).

## Out of scope

- Voice control ("Hey NutriRoll, start step 2") — needs WebSpeech +
  permissions.
