/**
 * Pantry expiry / freshness helpers (frontend only).
 *
 * `EXPIRY_WARNING_DAYS` is now the single source of truth — it lives in
 * `server/nutriroll/domain/category_meta.py` and is exposed by
 * `GET /v1/meta/components` as `expiry_warning_days`. The frontend reads
 * this value from `ComponentMetaProvider` at runtime instead of
 * maintaining its own copy (modularity-audit M9).
 *
 * The fallback constant (3) is kept here only for environments where the
 * meta endpoint has not yet loaded (e.g. while the provider is still
 * fetching). Callers should prefer the `expiryWarningDays` helper from
 * `@/lib/components/meta` which returns the server value once available.
 */

/** Fallback used before meta loads. Do not use directly in logic — use `expiryWarningDays()`. */
export const DEFAULT_EXPIRY_WARNING_DAYS = 3;

function todayUtcMidnight(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

export function daysUntilExpiry(expiresAt: string | null | undefined): number | null {
  if (!expiresAt) return null;
  const target = new Date(`${expiresAt}T00:00:00Z`);
  if (Number.isNaN(target.getTime())) return null;
  const today = todayUtcMidnight();
  return Math.round((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export function isExpiringSoon(
  expiresAt: string | null | undefined,
  warningDays: number = DEFAULT_EXPIRY_WARNING_DAYS,
): boolean {
  const days = daysUntilExpiry(expiresAt);
  if (days === null) return false;
  return days <= warningDays;
}
