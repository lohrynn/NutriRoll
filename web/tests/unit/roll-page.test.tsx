import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import enMessages from "@/messages/en.json";

const postMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    POST: (...args: unknown[]) => {
      const path = args[0] as string;
      // Fire-and-forget telemetry endpoints should not consume queued mocks.
      if (path === "/v1/history") {
        return Promise.resolve({ data: undefined, error: undefined, response: { status: 204 } });
      }
      return postMock(...args);
    },
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

import { RollPage } from "@/components/roll-page";

function wrap(node: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {node}
    </NextIntlClientProvider>
  );
}

const SAMPLE_COMPONENT = {
  id: "11111111-1111-1111-1111-111111111111",
  category: "base",
  name: "Brown rice",
  image_url: null,
  default_portion: { value: 80, unit: "g" },
  macros_per_100g: { kcal: 123, carbs_g: 25, protein_g: 3, fat_g: 1, fiber_g: 2 },
  default_cooking_method: "boil",
  cooking_methods: [
    { method: "boil", approx_minutes: 25, can_cook_with_others: true, notes: null },
  ],
  flavor_tags: [],
  dietary_tags: [],
  allergens: [],
  shelf_life_days: null,
  blacklisted: false,
};

const SAMPLE_BOWL = {
  slots: [
    {
      component: SAMPLE_COMPONENT,
      score: 0.42,
      reasons: ["balanced macros for a base", "cooks in ~25 min"],
    },
  ],
};

beforeEach(() => {
  postMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("RollPage", () => {
  it("rolls a bowl and renders slots with reasons", async () => {
    postMock.mockResolvedValueOnce({
      data: SAMPLE_BOWL,
      error: undefined,
      response: { status: 200 },
    });

    render(wrap(<RollPage />));

    fireEvent.click(screen.getByRole("button", { name: enMessages.roll.rollButton }));

    expect(await screen.findByText("Brown rice")).toBeInTheDocument();
    expect(screen.getByText("balanced macros for a base")).toBeInTheDocument();
    expect(postMock).toHaveBeenCalledWith(
      "/v1/roll",
      expect.objectContaining({
        body: expect.objectContaining({
          slots: expect.any(Array),
          time_budget_min: 30,
        }),
      }),
    );
  });

  it("shows an error when the roll endpoint fails", async () => {
    postMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: { code: "empty_candidate_pool" } },
      response: { status: 422 },
    });

    render(wrap(<RollPage />));
    fireEvent.click(screen.getByRole("button", { name: enMessages.roll.rollButton }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/empty_candidate_pool/);
    });
  });

  it("re-rolls a single slot via the slot endpoint", async () => {
    postMock
      .mockResolvedValueOnce({
        data: SAMPLE_BOWL,
        error: undefined,
        response: { status: 200 },
      })
      .mockResolvedValueOnce({
        data: {
          component: { ...SAMPLE_COMPONENT, name: "Quinoa" },
          score: 0.5,
          reasons: ["you haven't had this recently"],
        },
        error: undefined,
        response: { status: 200 },
      });

    render(wrap(<RollPage />));
    fireEvent.click(screen.getByRole("button", { name: enMessages.roll.rollButton }));
    await screen.findByText("Brown rice");

    fireEvent.click(screen.getByRole("button", { name: enMessages.roll.rerollSlot }));
    expect(await screen.findByText("Quinoa")).toBeInTheDocument();
    expect(postMock).toHaveBeenLastCalledWith(
      "/v1/roll/slot",
      expect.objectContaining({
        body: expect.objectContaining({
          slot_category: "base",
          exclude_component_ids: ["11111111-1111-1111-1111-111111111111"],
        }),
      }),
    );
  });
});
