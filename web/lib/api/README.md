# `lib/api/`

Generated typed client for the NutriRoll backend.

- `schema.d.ts` is **generated** by `openapi-typescript` from `openapi.json`.
  Regenerate with `make gen-client` from the repo root. The committed stub
  exists only so the project type-checks on a clean checkout before the
  backend has been booted.
- `client.ts` wires `openapi-fetch` against `NEXT_PUBLIC_API_BASE_URL`.

Never hand-write request/response types here. If you need a new shape, add
the endpoint on the server, regenerate the client, then consume it.
