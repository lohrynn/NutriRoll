# Phase 17 — AI assistant (BYO LLM key)

**Status:** TODO (not started, longest-deferred)

---

## Goal

A single chat-style surface that lets the user ask the LLM to:

1. **Interpret a free-text goal** ("I want to lose 5 kg in 3 months")
   into concrete `default_macro_targets` (Phase 11) and
   `roll_weights` (M6/M10).
2. **Customize a recipe** ("make this vegan" / "swap the rice for
   cauliflower") — returns a modified bowl snapshot the user can
   accept.
3. **Plan a week** ("low-carb prep, 3 dinners, easy") — returns a
   `planned_meals` payload the user can accept.

Bring-your-own API key (OpenAI / Anthropic / local Ollama). Stored
encrypted in `user_profile.llm_provider` + `llm_api_key_ciphertext`.

---

## Backend

- New `domain/llm/` namespace — framework-free protocol
  (`LLMClient`) plus adapters in `db/` or a dedicated `services/`
  layer for the three providers.
- Strict JSON-schema responses (use OpenAI structured outputs or
  Anthropic tool use); never trust raw LLM text.
- Domain validators run on the LLM output before it touches DB.
- Rate-limit per device token; cache identical prompts.

## Frontend

- Floating "Ask" button on Roll, Recipe, and Plan pages.
- Settings: provider picker + masked API key field + a small "test
  connection" button.
- All AI suggestions are *previewed* — never auto-applied.

## Security

- API keys encrypted at rest (Fernet / age) with a key derived from
  the device token.
- Outbound LLM calls go from the *server*, not the browser, so the key
  never leaves the host.
- Strict allowlist of system prompts; no user-controlled system prompt.

## Out of scope (v1 of this phase)

- Voice input.
- Image input ("here's a photo of my fridge, suggest a bowl").
- Long-running agent loops; every interaction is a single
  request/response.
