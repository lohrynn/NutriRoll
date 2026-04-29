import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/page-shell";
import { SettingsPage } from "@/components/settings-page";

export default async function SettingsRoute() {
  const t = await getTranslations("settings");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <SettingsPage />
    </PageShell>
  );
}
