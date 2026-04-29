import { type NextRequest, NextResponse } from "next/server";

// Paths that don't require completed onboarding. Onboarding itself plus the
// PWA manifest/SW are always allowed; the regex matcher already excludes
// static assets.
const ONBOARDING_EXEMPT_PREFIXES = ["/onboarding", "/api"];

function needsOnboardingRedirect(request: NextRequest): boolean {
  const { pathname } = request.nextUrl;
  if (ONBOARDING_EXEMPT_PREFIXES.some((p) => pathname.startsWith(p))) return false;
  return request.cookies.get("nutriroll-onboarded")?.value !== "1";
}

export function middleware(request: NextRequest): NextResponse {
  if (needsOnboardingRedirect(request)) {
    const url = request.nextUrl.clone();
    url.pathname = "/onboarding";
    url.search = "";
    return NextResponse.redirect(url);
  }

  const isDev = process.env.NODE_ENV !== "production";

  // In dev mode skip CSP entirely — nonce/style-src interactions with Safari
  // and React 19's stylesheet hoisting cause the stylesheet to be blocked.
  // Security headers are still applied; CSP is a production-only concern.
  if (isDev) {
    const response = NextResponse.next();
    response.headers.set("referrer-policy", "strict-origin-when-cross-origin");
    response.headers.set("x-content-type-options", "nosniff");
    response.headers.set("x-frame-options", "DENY");
    return response;
  }

  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' ${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"} https://api.nutriroll.app`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests",
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("content-security-policy", csp);
  response.headers.set("referrer-policy", "strict-origin-when-cross-origin");
  response.headers.set("x-content-type-options", "nosniff");
  response.headers.set("x-frame-options", "DENY");

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|manifest)$).*)",
  ],
};
