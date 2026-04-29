import { getTranslations } from "next-intl/server";

import { OnboardingPage } from "@/components/onboarding-page";
import { PageShell } from "@/components/page-shell";

export default async function OnboardingRoute() {
  const t = await getTranslations("onboarding");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <OnboardingPage />
    </PageShell>
  );
}
