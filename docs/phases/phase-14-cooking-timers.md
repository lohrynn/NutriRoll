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

## Implementation log (built)

The phase doc said "Cook page" but the actual recipe steps live on the
Recipe page (`/recipe`). The Cook page (`/cook`) is the post-cook rating
page. Phase 14 therefore wired per-step timers into `recipe-page.tsx`.

Backend:

- None. Step durations are derived client-side from
  `step[i+1].offset_min - step[i].offset_min`, with the final step using
  `block.total_minutes - lastStep.offset_min`.

Frontend:

- New `web/lib/cook/timers.ts`:
  - `useCookTimer({ key, durationSec, notificationTitle, notificationBody,
    onExpireFallback })` — a per-step persisted countdown. State is
    mirrored to `sessionStorage` under the `nutriroll.cookTimers` key
    (separate from `nutriroll.rolledBowl` per the workflow's
    "sessionStorage key ownership" rule), so a tab refresh mid-cook
    resumes the countdown instead of resetting it.
  - `requestNotificationPermission()` — lazily asks for the Notification
    permission on the first Start tap.
  - On expiry the hook fires a `Notification` with a stable `tag` so
    repeat alerts collapse, then falls back to the existing in-page beep
    (`playDoneTone`) when notifications are denied or unsupported.
- `web/components/recipe-page.tsx`:
  - New `StepTimer` component placed next to every recipe step. Renders
    the existing `mm:ss` label plus Play/Pause/Reset using the existing
    `Button` icon variants — visually consistent with the block-level
    `BlockTimer` already shipped.
  - Block-level `BlockTimer` is preserved unchanged for the per-block
    overview countdown.
- i18n: `recipe.timer.notify.title` (en + de) so notification copy
  follows the user's locale.
- Vitest: `tests/unit/cook-timers.test.ts` exercises start/persist/tick,
  expiry-fallback, and reset/storage-cleanup with fake timers.

`make check` is green: 108 server tests, 16 web tests (cook-timers added),
ruff/biome clean, pyright + tsc strict at zero errors.
