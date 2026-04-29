import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/page-shell";
import { ShopPage } from "@/components/shop-page";

export default async function ShopRoute() {
  const t = await getTranslations("shop");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <ShopPage />
    </PageShell>
  );
}
