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

  it("sends only candidate answers when saving confirmations", async () => {
    const application = createV3WorkspaceApplication();
    application.job.aiMatch?.applicationGuide?.clarificationQuestions?.push({
      id: "production-research",
      requirement: "Production research",
      question: "Have you run research for a production product?",
      why: "The role requires evidence from shipped products.",
      claimIfConfirmed: "Led production product research.",
      blocking: true,
    });
    const fetchMock = installApplicationWorkspaceApiMock({
      confirmationPutResponse: [
        {
          questionId: "production-research",
          requirement: "Production research",
          response: "yes",
          exampleText: "Led customer interviews before two production launches.",
          blocking: true,
          updatedAt: "2026-07-18T10:00:00.000Z",
        },
      ],
    });

    renderApplicationWorkspace(application);

    expect(
      await screen.findByText("Have you run research for a production product?"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "yes" }));
    fireEvent.change(
      screen.getByPlaceholderText("Add a true, concrete example"),
      {
        target: {
          value: "Led customer interviews before two production launches.",
        },
      },
    );

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([, init]) => init?.method === "PUT"),
      ).toBe(true);
    });
    const putCall = fetchMock.mock.calls.find(
      ([, init]) => init?.method === "PUT",
    );
    expect(putCall).toBeDefined();
    expect(JSON.parse(String(putCall?.[1]?.body))).toEqual({
      confirmations: [
        {
          questionId: "production-research",
          response: "yes",
          exampleText: "Led customer interviews before two production launches.",
        },
      ],
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
          currentGenerationFingerprint: "c".repeat(64),
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
        /fingerprint is outdated.*factual validation has not passed.*automated structural checks have not passed.*rendered DOCX is not available/,
      ),
    );
  });

  it("labels CV content as changes and explains the automated structural checks", async () => {
    installApplicationWorkspaceApiMock({
      documents: [
        {
          id: "validated-resume",
          type: "tailored_resume",
          title: "Validated CV",
          jobId: "job-product-designer",
          applicationIds: ["application-v3"],
          currentVersion: 1,
          createdAt: "2026-07-17T10:00:00.000Z",
          updatedAt: "2026-07-17T10:00:00.000Z",
          generationFingerprint: "b".repeat(64),
          currentGenerationFingerprint: "b".repeat(64),
          generationModel: "test-model",
          inputVersions: {},
          versions: [
            {
              id: "validated-resume-v1",
              version: 1,
              content: JSON.stringify({
                replacements: [
                  {
                    blockId: "summary",
                    replacement: "Research-led product designer",
                    reason: "Matches the role positioning",
                  },
                ],
              }),
              createdAt: "2026-07-17T10:00:00.000Z",
              hasRenderedDocx: true,
              factualValidation: { status: "passed" },
              visualValidation: {
                status: "passed",
                sourcePageCount: 2,
                renderedPageCount: 2,
                sourceLinkCount: 3,
                renderedLinkCount: 3,
                linksPreserved: true,
                tableOverflow: false,
              },
              diff: [],
            },
          ],
        },
      ],
    });

    renderApplicationWorkspace(createV3WorkspaceApplication());

    expect(await screen.findByText("CV change list")).toBeInTheDocument();
    expect(screen.getByText(/not a visual DOCX preview/)).toBeInTheDocument();
    expect(screen.getByText("Automated structural checks")).toBeInTheDocument();
    expect(screen.getByText("2 source → 2 rendered")).toBeInTheDocument();
    expect(
      screen.getByText("3 source → 3 rendered · preserved"),
    ).toBeInTheDocument();
    expect(screen.getByText("No overflow detected")).toBeInTheDocument();
    expect(screen.queryByText(/Visual validation/i)).not.toBeInTheDocument();
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
