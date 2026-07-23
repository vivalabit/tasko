import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { JobsToolbar } from "@/components/jobs-toolbar";

afterEach(() => {
  vi.unstubAllGlobals();
});

it("renders the requested action order and opens auto-searches locally", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    }),
  );

  render(
    <JobsToolbar
      savedJobsCount={2}
      archivedJobsCount={3}
      showSavedJobs={false}
      showArchivedJobs={false}
      isAnalysisMenuOpen={false}
      bulkAnalysisScope={null}
      recentAnalysisCount={4}
      missingAnalysisCount={5}
      onAddVacancy={vi.fn()}
      onSearchVacancies={vi.fn()}
      onToggleSavedJobs={vi.fn()}
      onToggleArchivedJobs={vi.fn()}
      onAnalysisMenuOpenChange={vi.fn()}
      onRunAnalysis={vi.fn()}
    />,
  );

  const toolbar = screen.getByLabelText("Jobs actions");
  expect(
    within(toolbar)
      .getAllByRole("button")
      .map((button) => button.getAttribute("aria-label") || button.textContent?.trim()),
  ).toEqual([
    "Add vacancy",
    "Search vacancies",
    "Saved Jobs (2)",
    "Archived (3)",
    "Jobs settings",
    "Analysis",
  ]);

  fireEvent.click(within(toolbar).getByRole("button", { name: "Jobs settings" }));
  expect(
    screen.getByRole("dialog", { name: "Automatic searches" }),
  ).toBeInTheDocument();

  fireEvent.keyDown(window, { key: "Escape" });
  expect(
    screen.queryByRole("dialog", { name: "Automatic searches" }),
  ).not.toBeInTheDocument();
});
