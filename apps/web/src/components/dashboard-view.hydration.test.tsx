import { act } from "react";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DashboardGreeting,
  useHydrationSafeCurrentTime,
} from "@/components/dashboard-greeting";

function HydrationSafeGreeting() {
  const currentTime = useHydrationSafeCurrentTime();
  return <DashboardGreeting name="Alex Morgan" currentTime={currentTime} />;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("DashboardView hydration", () => {
  it("keeps the greeting stable when server and client render at different times", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 6, 17, 8));
    const container = document.createElement("div");
    container.innerHTML = renderToString(<HydrationSafeGreeting />);

    expect(container).toHaveTextContent("Hello, Alex!");

    vi.setSystemTime(new Date(2026, 6, 17, 20));
    const hydrationErrors: unknown[] = [];
    let root: Root | undefined;

    await act(async () => {
      root = hydrateRoot(container, <HydrationSafeGreeting />, {
        onRecoverableError: (error) => hydrationErrors.push(error),
      });
    });

    expect(hydrationErrors).toEqual([]);
    expect(container).toHaveTextContent("Good evening, Alex!");

    await act(async () => {
      root?.unmount();
    });
  });
});
