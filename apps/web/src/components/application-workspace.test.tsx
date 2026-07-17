import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createLegacyWorkspaceApplication,
  createV3WorkspaceApplication,
  installApplicationWorkspaceApiMock,
  renderApplicationWorkspace,
} from "@/test/application-workspace-harness";

describe("ApplicationWorkspace", () => {
  it("renders a legacy application and asks for a refreshed analysis", async () => {
    installApplicationWorkspaceApiMock();

    renderApplicationWorkspace(createLegacyWorkspaceApplication());

    expect(
      screen.getByRole("heading", { name: "Senior Product Designer" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Update analysis" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/legacy ai-match-v1 percentage/),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getAllByRole("button", { name: "Select source first" }),
      ).toHaveLength(2);
    });
  });

  it("renders the current v3 application guide", async () => {
    installApplicationWorkspaceApiMock();

    renderApplicationWorkspace(createV3WorkspaceApplication());

    expect(
      screen.getByRole("heading", { name: "Senior Product Designer" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Turn complex B2B workflows into clear, validated product experiences.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Position Alex as a research-led designer/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tablist", { name: "Application analysis" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Refresh analysis" }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getAllByRole("button", { name: "Select source first" }),
      ).toHaveLength(2);
    });
  });
});
