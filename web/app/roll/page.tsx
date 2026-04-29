import { getTranslations } from "next-intl/server";

import { RollPage } from "@/components/roll-page";

export default async function RollRoute() {
  const t = await getTranslations("roll");
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-6">
      <nav className="text-sm opacity-70">
        <a href="/">← NutriRoll</a>
      </nav>
      <h1 className="sr-only">{t("title")}</h1>
      <RollPage />
    </main>
  );
}
