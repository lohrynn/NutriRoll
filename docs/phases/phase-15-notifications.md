# Phase 15 — Notifications & reminders

**Status:** TODO (not started)

---

## Goal

PWA push notifications for:
- Planned meal reminders ("Time to roll your dinner")
- Pantry items expiring within `EXPIRY_WARNING_DAYS`
- Weekly plan summary (Sunday evening: "Roll your week?")

---

## Backend

- New `subscriptions` table — push endpoint + keys per device token.
- `POST /v1/me/push-subscription` (upsert) and DELETE.
- A small scheduler (APScheduler in-process is enough for single-user
  v1; cron-like daily tick) that queries pantry expiries and planned
  meals and sends notifications via `pywebpush`.

## Frontend

- Settings → Notifications card with three toggles (planner / pantry /
  weekly summary) and a "Subscribe" button that calls
  `Notification.requestPermission()` and registers with the service
  worker.
- Service worker: `push` event handler.

## Decisions to make

- Whether to ship a VAPID keypair with the app or require BYO (BYO is
  cleaner for a self-hosted single-user app).
- Hosting: in-process scheduler vs. external cron hitting an internal
  endpoint.

## Out of scope

- Email / SMS notifications.
- Per-meal "start cooking now" alarm tied to estimated prep start time.
