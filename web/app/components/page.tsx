import { getTranslations } from "next-intl/server";

import { ComponentManager } from "@/components/component-manager";
import { PageShell } from "@/components/page-shell";

export default async function ComponentsPage() {
  const t = await getTranslations("components");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <ComponentManager />
    </PageShell>
  );
}
