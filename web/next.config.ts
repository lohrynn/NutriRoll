import withSerwistInit from "@serwist/next";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const pwaEnabled = process.env.NEXT_PUBLIC_PWA_ENABLED === "true";

const internalApiBase = process.env.INTERNAL_API_BASE_URL ?? "http://backend:8000";

const baseConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    return [
      {
        source: "/v1/:path*",
        destination: `${internalApiBase}/v1/:path*`,
      },
    ];
  },
};

const withSerwist = withSerwistInit({
  swSrc: "lib/pwa/sw.ts",
  swDest: "public/sw.js",
  disable: !pwaEnabled,
  cacheOnNavigation: true,
  reloadOnOnline: true,
});

export default withNextIntl(withSerwist(baseConfig));
