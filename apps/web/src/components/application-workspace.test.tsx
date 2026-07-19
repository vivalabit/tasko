import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  createLegacyWorkspaceApplication,
  createV3WorkspaceApplication,
  createWorkspaceProfile,
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
    expect(screen.getByText("match-revision-v3")).toBeInTheDocument();
    expect(
      screen.getByText(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      ),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getAllByRole("button", { name: "Select source first" }),
      ).toHaveLength(2);
    });
  });

  it("stops hung loaders, reports API unavailable, and retries", async () => {
    vi.useFakeTimers();
    let apiUnavailable = true;
    installApplicationWorkspaceApiMock({
      requestHandler: (_url, _method, init) => {
        if (!apiUnavailable) return undefined;
        return new Promise<Response>((_, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      },
    });

    renderApplicationWorkspace(createV3WorkspaceApplication());

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(screen.getAllByText("API unavailable").length).toBeGreaterThan(0);
    expect(screen.queryByText("Loading answers")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Retry loading history" })).toHaveLength(2);

    apiUnavailable = false;
    fireEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    await act(async () => {
      await Promise.resolve();
    });
    vi.useRealTimers();

    expect(await screen.findByText("API online")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Select source first" })).toHaveLength(2);
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

  it("persists an incomplete required confirmation as a draft", async () => {
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
          exampleText: "",
          blocking: true,
          updatedAt: "2026-07-18T10:00:00.000Z",
        },
      ],
    });

    renderApplicationWorkspace(application);
    fireEvent.click(await screen.findByRole("button", { name: "yes" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([, init]) => {
          if (init?.method !== "PUT") return false;
          return JSON.stringify(JSON.parse(String(init.body))) === JSON.stringify({
            confirmations: [
              {
                questionId: "production-research",
                response: "yes",
                exampleText: "",
              },
            ],
          });
        }),
      ).toBe(true);
    });
    expect(screen.getByText(/Add a specific example/)).toBeInTheDocument();
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
                    spanId: "summary-span-0001",
                    replacement: "Research-led product designer",
                    reason: "Matches the role positioning",
                    evidenceIds: ["profile:headline"],
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
                pageCountChanged: false,
                sourceTextBoxCount: 48,
                renderedTextBoxCount: 49,
                missingTextCount: 0,
                disappearedSourceTextCount: 0,
                textGeometryChangedCount: 0,
                textOutsidePageCount: 0,
                sourceImageCount: 2,
                renderedImageCount: 2,
                sourceImageBoxCount: 2,
                renderedImageBoxCount: 2,
                missingSourceImageCount: 0,
                missingPdfImageCount: 0,
                imageGeometryChangedCount: 0,
                imageOutsidePageCount: 0,
                sourceLinkCount: 3,
                renderedLinkCount: 3,
                missingLinkCount: 0,
                addedLinkCount: 0,
                sourcePdfLinkCount: 3,
                renderedPdfLinkCount: 3,
                missingPdfLinkCount: 0,
                addedPdfLinkCount: 0,
                linkLocationChangedCount: 0,
                linksPreserved: true,
                tableOverflow: false,
                cellOverflowCount: 0,
                tableStructureIssueCount: 0,
                issues: [],
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
    expect(screen.getByText("Rendered geometry checks")).toBeInTheDocument();
    expect(screen.getByText("2 source → 2 rendered · unchanged")).toBeInTheDocument();
    expect(screen.getByText("48 → 49 boxes · 0 PDF missing · 0 source lost · 0 moved · 0 outside")).toBeInTheDocument();
    expect(screen.getByText("DOCX 2 → 2 · PDF boxes 2 → 2 · 0 DOCX missing · 0 PDF missing · 0 moved · 0 outside")).toBeInTheDocument();
    expect(screen.getByText("DOCX 3 → 3 · PDF 3 → 3 · 0 moved")).toBeInTheDocument();
    expect(screen.getByText("0 page · 0 cell overflow · 0 table structure")).toBeInTheDocument();
    expect(screen.getByText("0 issues")).toBeInTheDocument();
    expect(screen.queryByText(/Visual validation/i)).not.toBeInTheDocument();
  });

  it("shows the AI provider, revokes versioned consent, and deletes stored artifacts", async () => {
    window.localStorage.setItem("tasko.ai-consent", JSON.stringify({
      version: "2026-07-18.v2",
      providerName: "OpenAI",
      acceptedAt: "2026-07-18T10:00:00.000Z",
    }));
    const fetchMock = installApplicationWorkspaceApiMock({
      documents: [{
        id: "document-delete",
        type: "tailored_resume",
        title: "Tailored CV",
        jobId: "job-product-designer",
        applicationIds: ["application-v3"],
        currentVersion: 1,
        createdAt: "2026-07-18T10:00:00.000Z",
        updatedAt: "2026-07-18T10:00:00.000Z",
        generationFingerprint: null,
        currentGenerationFingerprint: null,
        generationModel: null,
        inputVersions: {},
        versions: [{
          id: "document-delete-v1",
          version: 1,
          content: "CV content",
          createdAt: "2026-07-18T10:00:00.000Z",
          hasRenderedDocx: false,
          factualValidation: {},
          visualValidation: {},
          diff: [],
        }],
      }],
      templates: [{
        id: "template-delete",
        type: "tailored_resume",
        name: "Stored CV",
        fileName: "resume.docx",
        createdAt: "2026-07-18T10:00:00.000Z",
        updatedAt: "2026-07-18T10:00:00.000Z",
      }],
      requestHandler: async (url, method) => {
        if (url.pathname === "/documents/document-delete" && method === "DELETE") {
          return new Response(null, { status: 204 });
        }
        if (url.pathname === "/documents/templates/template-delete" && method === "DELETE") {
          return new Response(null, { status: 204 });
        }
        return undefined;
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderApplicationWorkspace(createV3WorkspaceApplication());

    expect(await screen.findByText("AI provider:")).toBeInTheDocument();
    expect(screen.getByText("OpenAI")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revoke consent" }));
    expect(window.localStorage.getItem("tasko.ai-consent")).toBeNull();
    expect(screen.getByText("Consent required")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete Tailored CV" }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Delete Tailored CV" })).not.toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete template Stored CV" }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Delete template Stored CV" })).not.toBeInTheDocument();
    });
    expect(fetchMock.mock.calls.some(([input, init]) => String(input).includes("/documents/document-delete") && init?.method === "DELETE")).toBe(true);
  });

  it("reuses the resume artifact and recovers a committed pack after response loss", async () => {
    window.localStorage.setItem("tasko.ai-consent", JSON.stringify({
      version: "2026-07-18.v2",
      providerName: "OpenAI",
      acceptedAt: "2026-07-18T10:00:00.000Z",
    }));
    const uploadedAt = "2026-07-18T10:00:00.000Z";
    const sources = [
      {
        id: "resume-source",
        title: "Main CV",
        category: "CV / Resume",
        language: "English",
        file_name: "resume.docx",
        file_size: "20 KB",
        file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        uploaded_at: uploadedAt,
        data_url: "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,cv",
      },
      {
        id: "cover-source",
        title: "Main cover",
        category: "Cover Letter",
        language: "English",
        file_name: "cover.docx",
        file_size: "16 KB",
        file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        uploaded_at: uploadedAt,
        data_url: "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,cover",
      },
    ];
    const templates = [
      { id: "resume-template", type: "tailored_resume", name: `Main CV · ${uploadedAt}`, fileName: "resume.docx", createdAt: uploadedAt, updatedAt: uploadedAt },
      { id: "cover-template", type: "cover_letter", name: `Main cover · ${uploadedAt}`, fileName: "cover.docx", createdAt: uploadedAt, updatedAt: uploadedAt },
    ];
    const savedDocuments = [
      {
        id: "saved-resume",
        type: "tailored_resume",
        title: "Tailored CV",
        jobId: "job-product-designer",
        applicationIds: ["application-v3"],
        currentVersion: 1,
        createdAt: uploadedAt,
        updatedAt: uploadedAt,
        generationFingerprint: "a".repeat(64),
        currentGenerationFingerprint: "a".repeat(64),
        generationModel: "test-model",
        inputVersions: {},
        versions: [],
      },
      {
        id: "saved-cover",
        type: "cover_letter",
        title: "Cover letter",
        jobId: "job-product-designer",
        applicationIds: ["application-v3"],
        currentVersion: 1,
        createdAt: uploadedAt,
        updatedAt: uploadedAt,
        generationFingerprint: "b".repeat(64),
        currentGenerationFingerprint: "b".repeat(64),
        generationModel: "test-model",
        inputVersions: {},
        versions: [],
      },
    ];
    const recoveredPack = {
      packJobId: "server-uses-request-id",
      status: "completed",
      persistenceMode: "atomic",
      documents: savedDocuments,
      stages: [],
      message: "Application pack saved atomically",
    };
    let assistantCalls = 0;
    let packPostCalls = 0;
    let submittedResume: Record<string, unknown> | undefined;
    installApplicationWorkspaceApiMock({
      templates,
      requestHandler: async (url, method, init) => {
        if (url.pathname === "/assistant/chat" && method === "POST") {
          assistantCalls += 1;
          return Response.json({
            message: assistantCalls === 1
              ? JSON.stringify({ replacements: [] })
              : "Dear Hiring Team,\n\nVerified experience.\n\nKind regards,",
            metadata: { metrics: { model: "test-model" } },
          });
        }
        if (url.pathname === "/documents/packs/validate-resume" && method === "POST") {
          return Response.json({
            status: "passed",
            validation: {},
            validationArtifactId: "artifact-1",
            expiresAt: "2026-07-18T10:30:00.000Z",
          });
        }
        if (url.pathname === "/documents/packs" && method === "POST") {
          packPostCalls += 1;
          submittedResume = (JSON.parse(String(init?.body)) as { resume: Record<string, unknown> }).resume;
          throw new TypeError("response lost");
        }
        if (/^\/documents\/packs\/application-pack-/.test(url.pathname) && method === "GET") {
          return Response.json(recoveredPack);
        }
        return undefined;
      },
    });

    const { props } = renderApplicationWorkspace(
      createV3WorkspaceApplication(),
      { profile: createWorkspaceProfile({ documents: JSON.stringify(sources) }) },
    );

    const generatePack = await screen.findByRole("button", { name: "Generate both documents" });
    await waitFor(() => expect(generatePack).toBeEnabled());
    fireEvent.click(generatePack);

    expect(
      await screen.findByText(/recovered after response loss/, {}, { timeout: 4_000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/No pack documents were saved/)).not.toBeInTheDocument();
    expect(submittedResume?.validationArtifactId).toBe("artifact-1");
    expect(packPostCalls).toBe(3);
    expect(props.onDocumentAttached).toHaveBeenCalledTimes(2);
    window.localStorage.removeItem("tasko.ai-consent");
  });

  it("reports template capabilities and AI context truncation before generation", async () => {
    const source = {
      id: "large-resume-source",
      title: "Large CV",
      category: "CV / Resume",
      language: "English",
      file_name: "large-resume.docx",
      file_size: "80 KB",
      file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      uploaded_at: "2026-07-18T10:00:00.000Z",
      data_url: "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,cv",
    };
    installApplicationWorkspaceApiMock({
      requestHandler: (url, method) => {
        if (url.pathname !== "/documents/templates/preflight" || method !== "POST") return undefined;
        return Response.json({
          supported: true,
          template: {
            id: "large-template",
            type: "tailored_resume",
            name: "Large CV",
            fileName: "large-resume.docx",
            createdAt: "2026-07-18T10:00:00.000Z",
            updatedAt: "2026-07-18T10:00:00.000Z",
          },
          editableCount: 12,
          immutableCount: 3,
          immutableElements: [
            { id: "block-0001", type: "heading", text: "Experience", reason: "AI changes targeting this protected element will be rejected" },
          ],
          rejectedElements: [],
          aiContext: {
            maxCharacters: 32000,
            contextBudgetCharacters: 28000,
            estimatedCharacters: 36000,
            includedCharacters: 28000,
            truncated: true,
            source: {
              totalElements: 40,
              includedElements: 28,
              omittedElements: 12,
              estimatedCharacters: 18000,
              includedCharacters: 10000,
              truncated: true,
            },
          },
          warnings: [],
        });
      },
    });

    renderApplicationWorkspace(createV3WorkspaceApplication(), {
      profile: createWorkspaceProfile({ documents: JSON.stringify([source]) }),
    });

    expect(await screen.findByText("Supported · 12 editable")).toBeInTheDocument();
    expect(screen.getByText(/3 elements \(heading\)/)).toBeInTheDocument();
    expect(screen.getByText(/28 of 40 template elements/)).toBeInTheDocument();
    expect(screen.getByText(/context will be truncated/)).toBeInTheDocument();
  });

  it("restores persisted workspace uploads and lets the user delete them", async () => {
    const persistedSource = {
      id: "workspace-source-restored",
      applicationId: "application-v3",
      title: "Reloaded CV",
      category: "CV / Resume",
      language: "English",
      fileName: "reloaded-cv.docx",
      fileSize: "24 KB",
      fileType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      uploadedAt: "2026-07-19T09:00:00.000Z",
      dataUrl: "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,cv",
    };
    const fetchMock = installApplicationWorkspaceApiMock({
      workspaceSources: [persistedSource],
      requestHandler: (url, method) => {
        if (url.pathname === `/documents/workspace-sources/${persistedSource.id}` && method === "DELETE") {
          return new Response(null, { status: 204 });
        }
        return undefined;
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderApplicationWorkspace(createV3WorkspaceApplication());

    const restoredOption = await screen.findByRole("option", { name: /Reloaded CV · reloaded-cv\.docx/ });
    expect(restoredOption).toBeInTheDocument();
    const deleteButton = await screen.findByRole("button", { name: "Delete uploaded source reloaded-cv.docx" });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(screen.queryByRole("option", { name: /Reloaded CV · reloaded-cv\.docx/ })).not.toBeInTheDocument();
    });
    expect(fetchMock.mock.calls.some(([input, init]) => {
      const url = new URL(String(input));
      return url.pathname === `/documents/workspace-sources/${persistedSource.id}`
        && url.searchParams.get("applicationId") === "application-v3"
        && init?.method === "DELETE";
    })).toBe(true);
  });

  it("persists a newly uploaded DOCX before selecting it", async () => {
    let uploadedRequest: Record<string, string> | undefined;
    installApplicationWorkspaceApiMock({
      requestHandler: (url, method, init) => {
        if (url.pathname !== "/documents/workspace-sources" || method !== "POST") return undefined;
        uploadedRequest = JSON.parse(String(init?.body)) as Record<string, string>;
        return Response.json({
          id: "workspace-source-new",
          applicationId: uploadedRequest.applicationId,
          title: uploadedRequest.title,
          category: uploadedRequest.category,
          language: uploadedRequest.language,
          fileName: uploadedRequest.fileName,
          fileSize: "1 KB",
          fileType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          uploadedAt: "2026-07-19T10:00:00.000Z",
          dataUrl: uploadedRequest.dataUrl,
        }, { status: 201 });
      },
    });

    const { container } = renderApplicationWorkspace(createV3WorkspaceApplication());
    await screen.findByText("API online");
    const file = new File(["docx-content"], "target_cv.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    const uploadInput = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[0];
    fireEvent.change(uploadInput, { target: { files: [file] } });

    expect(await screen.findByRole("option", { name: /target cv · target_cv\.docx/ })).toBeInTheDocument();
    expect(uploadedRequest).toMatchObject({
      applicationId: "application-v3",
      category: "CV / Resume",
      fileName: "target_cv.docx",
    });
    expect(uploadedRequest?.dataUrl).toMatch(/^data:.*;base64,/);
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
    expect(fetchMock).toHaveBeenCalledTimes(6);
  });
});
