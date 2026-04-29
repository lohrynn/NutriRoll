import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { headers } from "next/headers";
import type { ReactNode } from "react";

import { BottomNav } from "@/components/bottom-nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "NutriRoll",
  description: "Roll a cheap, tasty bowl in seconds.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang={locale}>
      <head>
        <script
          {...(nonce ? { nonce } : {})}
          // Set the theme attribute before paint to avoid flashes.
          // biome-ignore lint/security/noDangerouslySetInnerHtml: pre-paint init
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("nutriroll.theme");if(t==="light"||t==="dark"){document.documentElement.setAttribute("data-theme",t);}}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
          <BottomNav />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
