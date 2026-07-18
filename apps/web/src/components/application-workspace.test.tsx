import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  createLegacyWorkspaceApplication,
  createV3WorkspaceApplication,
  createWorkspaceApplicationWithoutGuide,
  installApplicationWorkspaceApiMock,
  renderApplicationWorkspace,
} from "@/test/application-workspace-harness";

describe("ApplicationWorkspace", () => {
  it("shows an empty state when the route has no application ID", () => {
    renderApplicationWorkspace(null);

    expect(
      screen.getByRole("heading", { name: "No application selected" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Back to applications" }),
    ).toBeInTheDocument();
  });

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

  it("warns before downloading an outdated and unvalidated document", async () => {
    installApplicationWorkspaceApiMock({
      documents: [
        {
          id: "document-resume",
          type: "tailored_resume",
          title: "Tailored CV",
          jobId: "job-product-designer",
          applicationIds: ["application-v3"],
          currentVersion: 1,
          createdAt: "2026-07-17T10:00:00.000Z",
          updatedAt: "2026-07-17T10:00:00.000Z",
          generationFingerprint: "a".repeat(64),
          generationModel: "test-model",
          inputVersions: {},
          versions: [
            {
              id: "document-resume-v1",
              version: 1,
              content: "Tailored resume content",
              createdAt: "2026-07-17T10:00:00.000Z",
              hasRenderedDocx: false,
              factualValidation: { status: "pending" },
              visualValidation: { status: "pending" },
              diff: [],
            },
          ],
        },
      ],
    });
    const confirmDownload = vi.spyOn(window, "confirm").mockReturnValue(false);

    renderApplicationWorkspace(createV3WorkspaceApplication());

    expect(await screen.findByText("Outdated · v1")).toBeInTheDocument();
    const downloadLink = screen
      .getAllByRole("link", { name: "DOCX" })
      .find((link) => !link.getAttribute("href")?.includes("?version="));

    expect(downloadLink).toBeDefined();
    if (!downloadLink)
      throw new Error("Current document download link is missing");
    expect(fireEvent.click(downloadLink)).toBe(false);
    expect(confirmDownload).toHaveBeenCalledWith(
      expect.stringMatching(
        /fingerprint is outdated.*factual validation has not passed.*visual validation has not passed.*rendered DOCX is not available/,
      ),
    );
  });

  it("does not loop fingerprint updates when the application guide is missing", async () => {
    const fetchMock = installApplicationWorkspaceApiMock();

    renderApplicationWorkspace(createWorkspaceApplicationWithoutGuide());

    expect(
      screen.getByText(/does not have a complete application guide v3/),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getAllByRole("button", { name: "Select source first" }),
      ).toHaveLength(2);
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
