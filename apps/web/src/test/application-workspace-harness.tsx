import type { ComponentProps } from "react";
import { render } from "@testing-library/react";
import { vi } from "vitest";

import { ApplicationWorkspace } from "@/components/application-workspace";

type ApplicationWorkspaceProps = ComponentProps<typeof ApplicationWorkspace>;
type WorkspaceApplication = NonNullable<
  ApplicationWorkspaceProps["application"]
>;
type WorkspaceJob = WorkspaceApplication["job"];

type ApplicationOverrides = Omit<Partial<WorkspaceApplication>, "job"> & {
  job?: Partial<WorkspaceJob>;
};

type WorkspaceApiOptions = {
  confirmations?: unknown[];
  documents?: unknown[];
  templates?: unknown[];
};

const baseJob: Omit<WorkspaceJob, "aiMatch"> = {
  id: "job-product-designer",
  title: "Senior Product Designer",
  company: "Acme Labs",
  location: "Zurich, Switzerland",
  type: "Full-time",
  match: 86,
  overview: "Lead product discovery and delivery for a growing B2B platform.",
  responsibilities: ["Lead discovery", "Partner with product and engineering"],
  requirements: [
    "5+ years of product design experience",
    "Strong research practice",
  ],
  skills: ["Product design", "User research", "Figma"],
  applyUrl: "https://example.com/jobs/product-designer",
};

export function createWorkspaceProfile(
  overrides: Partial<ApplicationWorkspaceProps["profile"]> = {},
): ApplicationWorkspaceProps["profile"] {
  return {
    name: "Alex Morgan",
    current_role: "Product Designer",
    desired_role: "Senior Product Designer",
    location: "Zurich, Switzerland",
    headline: "Product designer for complex B2B workflows",
    skills: "Product design, user research, prototyping",
    experience: "Six years designing B2B software products.",
    education: "BA Interaction Design",
    documents: "",
    resume_file_name: "",
    resume_file_size: "",
    resume_updated_at: "",
    resume_data_url: "",
    ...overrides,
  };
}

export function createLegacyWorkspaceApplication(
  overrides: ApplicationOverrides = {},
): WorkspaceApplication {
  return createWorkspaceApplication({
    ...overrides,
    id: overrides.id ?? "application-legacy",
    job: {
      ...overrides.job,
      aiMatch: overrides.job?.aiMatch ?? {
        version: "ai-match-v1",
        reasons: ["Relevant product design experience"],
        gaps: ["Leadership scope needs validation"],
        updatedAt: "2026-07-01T10:00:00.000Z",
      },
    },
  });
}

export function createV3WorkspaceApplication(
  overrides: ApplicationOverrides = {},
): WorkspaceApplication {
  return createWorkspaceApplication({
    ...overrides,
    id: overrides.id ?? "application-v3",
    job: {
      ...overrides.job,
      aiMatch: overrides.job?.aiMatch ?? {
        version: "ai-match-v3",
        reasons: ["Strong product discovery background"],
        gaps: ["Confirm formal people-management experience"],
        updatedAt: "2026-07-15T10:00:00.000Z",
        applicationGuide: {
          language: "English",
          positioning:
            "Position Alex as a research-led designer who aligns cross-functional teams.",
          readiness: "needs_confirmation",
          roleMission:
            "Turn complex B2B workflows into clear, validated product experiences.",
          hiringPriorities: [
            "Discovery leadership",
            "Cross-functional collaboration",
          ],
          mustHave: ["B2B product design"],
          niceToHave: ["People leadership"],
          hardConstraints: [],
          evidenceMatrix: [
            {
              requirement: "B2B product design",
              importance: "required",
              status: "verified",
              evidence: "Six years designing B2B software products.",
              action: "Lead with recent product outcomes.",
            },
          ],
          clarificationQuestions: [],
          resumePlan: {
            targetHeadline: "Senior B2B Product Designer",
            summaryFocus: "Research-led product delivery",
            evidenceToLead: ["B2B workflow design"],
            bulletStrategy: ["Quantify product outcomes"],
          },
          coverLetterPlan: {
            openingAngle: "Connect discovery experience to Acme's platform.",
            proofPoints: ["Cross-functional product delivery"],
            motivationAngle: "Complex B2B products",
          },
          cvImprovements: ["Make product outcomes measurable"],
          coverLetterStrategy: ["Use one concrete discovery example"],
          risks: ["Do not imply unverified people-management experience"],
          keywords: ["Product discovery", "B2B", "User research"],
          applicationQuestions: ["Describe a complex workflow you simplified."],
          finalChecklist: ["Verify every claim against the source CV."],
        },
      },
    },
  });
}

export function createWorkspaceApplicationWithoutGuide(
  overrides: ApplicationOverrides = {},
): WorkspaceApplication {
  return createWorkspaceApplication({
    ...overrides,
    id: overrides.id ?? "application-without-guide",
    job: {
      ...overrides.job,
      aiMatch: overrides.job?.aiMatch ?? {
        version: "ai-match-v3",
        reasons: ["Relevant product design experience"],
        gaps: ["Application guide has not been generated"],
        updatedAt: "2026-07-16T10:00:00.000Z",
      },
    },
  });
}

function createWorkspaceApplication(
  overrides: ApplicationOverrides,
): WorkspaceApplication {
  return {
    id: "application",
    status: "draft",
    nextStep: "Prepare application pack",
    notes: "",
    documents: [],
    ...overrides,
    job: {
      ...baseJob,
      ...overrides.job,
    },
  };
}

export function installApplicationWorkspaceApiMock({
  confirmations = [],
  documents = [],
  templates = [],
}: WorkspaceApiOptions = {}) {
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const requestUrl =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const url = new URL(requestUrl);
    const method = init?.method ?? "GET";

    if (url.pathname === "/documents" && method === "GET") {
      return Response.json(documents);
    }
    if (url.pathname === "/documents/templates/library" && method === "GET") {
      return Response.json(templates);
    }
    if (
      /^\/applications\/[^/]+\/confirmations$/.test(url.pathname) &&
      method === "GET"
    ) {
      return Response.json(confirmations);
    }

    throw new Error(
      `Unhandled ApplicationWorkspace request: ${method} ${url.pathname}`,
    );
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderApplicationWorkspace(
  application: ApplicationWorkspaceProps["application"],
  overrides: Partial<Omit<ApplicationWorkspaceProps, "application">> = {},
) {
  const props: ApplicationWorkspaceProps = {
    application,
    profile: createWorkspaceProfile(),
    onBack: vi.fn(),
    onOpenAssistant: vi.fn(),
    onDocumentAttached: vi.fn(),
    onMarkApplied: vi.fn(),
    onRefreshAnalysis: vi.fn(),
    isAnalysisRefreshing: false,
    ...overrides,
  };

  return {
    ...render(<ApplicationWorkspace {...props} />),
    props,
  };
}
