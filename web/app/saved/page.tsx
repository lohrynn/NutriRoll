import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/page-shell";
import { SavedPage } from "@/components/saved-page";

export default async function SavedRoute() {
  const t = await getTranslations("saved");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <SavedPage />
    </PageShell>
  );
}
