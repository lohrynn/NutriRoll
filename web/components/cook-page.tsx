"use client";

import { ChefHat } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { RecipePage } from "@/components/recipe-page";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { readRolledMealFromStorage } from "@/lib/recipe/storage";

type PageState = "loading" | "missing" | "ready";

export function CookPage() {
  const t = useTranslations("cook");
  const [pageState, setPageState] = useState<PageState>("loading");

  useEffect(() => {
    const storedMeal = readRolledMealFromStorage();
    if (storedMeal && storedMeal.bowl.slots.length > 0) {
      setPageState("ready");
      return;
    }
    setPageState("missing");
  }, []);

  if (pageState === "loading") {
    return (
      <Card>
        <CardContent className="grid gap-3 animate-fade-in-up">
          <p className="text-sm text-[color:var(--color-muted)] animate-soft-pulse">{t("loading")}</p>
          <div className="grid gap-3">
            <Skeleton className="h-12 w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-[var(--radius-card)]" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (pageState === "missing") {
    return (
      <Card>
        <CardContent className="grid gap-3 animate-fade-in-up">
          <p className="text-sm text-[color:var(--color-muted)]">{t("noBowl")}</p>
          <Button asChild size="sm">
            <Link href="/roll">
              <ChefHat className="h-4 w-4" aria-hidden="true" />
              {t("goToRoll")}
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="animate-fade-in-up">
      <RecipePage />
    </div>
  );
}
