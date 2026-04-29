import { getTranslations } from "next-intl/server";

import { ComponentManager } from "@/components/component-manager";

export default async function ComponentsPage() {
  const t = await getTranslations("components");
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-6">
      <nav className="text-sm opacity-70">
        <a href="/">← NutriRoll</a>
      </nav>
      <h1 className="sr-only">{t("title")}</h1>
      <ComponentManager />
    </main>
  );
}
