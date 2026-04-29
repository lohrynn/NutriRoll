/**
 * sessionStorage key under which the Roll page stashes the most recent
 * RolledBowl so the Recipe page can pick it up after the user clicks
 * "Cook now". The handoff is intentionally local-only — no server-side
 * session, no URL bloat.
 */
export const ROLLED_BOWL_STORAGE_KEY = "nutriroll.rolledBowl";
