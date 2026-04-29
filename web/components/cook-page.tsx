"use client";

import { ChefHat, Star } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api/client";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import type { RolledBowl } from "@/lib/roll/types";

type Status =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "ok" }
  | {
      kind: "error";
      message: string;
    };

function StarPicker({
  value,
  onChange,
  ariaLabel,
}: {
  value: number;
  onChange: (n: number) => void;
  ariaLabel: string;
}) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => {
        const active = n <= value;
        return (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n}`}
            onClick={() => onChange(n)}
            className="grid h-9 w-9 place-items-center rounded-xl transition hover:bg-[color:var(--color-surface-2)]"
          >
            <Star
              className={`h-5 w-5 transition ${
                active
                  ? "fill-[color:var(--color-brand)] text-[color:var(--color-brand)]"
                  : "text-[color:var(--color-muted)]"
              }`}
              aria-hidden="true"
            />
          </button>
        );
      })}
    </div>
  );
}

export function CookPage() {
  const t = useTranslations("cook");
  const tCategory = useTranslations("components.category");

  const [bowl, setBowl] = useState<RolledBowl | null>(null);
  const [bowlId, setBowlId] = useState<string>("");
  const [overall, setOverall] = useState(0);
  const [perComponent, setPerComponent] = useState<Record<string, number>>({});
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(ROLLED_BOWL_STORAGE_KEY);
      if (raw) setBowl(JSON.parse(raw) as RolledBowl);
    } catch {
      // ignore
    }
    setBowlId(crypto.randomUUID());
  }, []);

  const componentNames = useMemo(() => {
    if (!bowl) return "";
    return bowl.slots.map((s) => s.component.name).join(" + ");
  }, [bowl]);

  if (!bowl) {
    return (
      <Card>
        <CardContent className="grid gap-3">
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

  const handleSave = async () => {
    if (overall < 1) return;
    setStatus({ kind: "saving" });
    try {
      const overallReq = apiClient.POST("/v1/ratings", {
        body: {
          bowl_id: bowlId,
          score: overall,
          comment: comment.trim() || null,
        },
      });
      const perCompReqs = Object.entries(perComponent)
        .filter(([, score]) => score > 0)
        .map(([component_id, score]) =>
          apiClient.POST("/v1/ratings", {
            body: { bowl_id: bowlId, component_id, score },
          }),
        );
      const historyReq = apiClient.POST("/v1/history", {
        body: {
          kind: "rated",
          bowl_id: bowlId,
          payload: {
            components: bowl.slots.map((s) => ({
              id: s.component.id,
              name: s.component.name,
              category: s.component.category,
            })),
            overall,
            comment: comment.trim() || null,
          },
        },
      });
      const results = await Promise.all([overallReq, ...perCompReqs, historyReq]);
      const failed = results.find((r) => r.error);
      if (failed) {
        setStatus({
          kind: "error",
          message: `HTTP ${failed.response.status}`,
        });
        return;
      }
      setStatus({ kind: "ok" });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  };

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{componentNames}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-1">
            <p className="text-sm font-medium">{t("score")}</p>
            <StarPicker value={overall} onChange={setOverall} ariaLabel={t("score")} />
          </div>
          <label className="grid gap-1 text-sm">
            <span>{t("comment")}</span>
            <Input
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t("commentPlaceholder")}
            />
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("componentScores")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          {bowl.slots.map((slot) => (
            <div key={slot.component.id} className="flex items-center justify-between gap-3">
              <div className="grid">
                <p className="font-medium">{slot.component.name}</p>
                <Badge variant="brand" className="w-fit">
                  {tCategory(slot.component.category)}
                </Badge>
              </div>
              <StarPicker
                value={perComponent[slot.component.id] ?? 0}
                onChange={(n) =>
                  setPerComponent((prev) => ({
                    ...prev,
                    [slot.component.id]: n,
                  }))
                }
                ariaLabel={slot.component.name}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {status.kind === "error" && (
        <Card className="border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/5">
          <CardContent>
            <output aria-live="polite" className="text-[color:var(--color-danger)]">
              {t("saveFailed", { message: status.message })}
            </output>
          </CardContent>
        </Card>
      )}
      {status.kind === "ok" && (
        <Card className="border-[color:var(--color-success)]/30 bg-[color:var(--color-success)]/5">
          <CardContent>
            <output aria-live="polite" className="text-[color:var(--color-success)]">
              {t("saved")}
            </output>
          </CardContent>
        </Card>
      )}

      <Button
        type="button"
        size="lg"
        onClick={() => void handleSave()}
        disabled={overall < 1 || status.kind === "saving"}
      >
        {status.kind === "saving" ? t("submitting") : t("submit")}
      </Button>
    </div>
  );
}
