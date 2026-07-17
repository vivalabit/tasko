"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Download,
  ExternalLink,
  FileCheck2,
  FileText,
  LoaderCircle,
  LockKeyhole,
  Mail,
  MessageSquareText,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  getAiMatchAnalysisStatus,
  hasCurrentApplicationGuide,
  isLegacyAiMatch,
} from "@/lib/ai-match";
import {
  importLegacyCandidateConfirmations,
  isCandidateConfirmationComplete,
  isMeaningfulCandidateConfirmation,
  type CandidateConfirmation,
  type CandidateConfirmationResponse,
} from "@/lib/candidate-confirmations";
import {
  createGenerationProvenance,
  isGeneratedDocumentOutdated,
  type GenerationFingerprintInputs,
  type GenerationInputVersions,
} from "@/lib/generation-provenance";
import { cn } from "@/lib/utils";

type WorkspaceJob = {
  id: string;
  title: string;
  company: string;
  location: string;
  type: string;
  match: number;
  overview: string;
  responsibilities: string[];
  requirements: string[];
  skills: string[];
  applyUrl?: string;
  sourceUrl?: string;
  aiMatch?: {
    version?: string;
    reasons: string[];
    gaps: string[];
    updatedAt?: string;
    applicationGuide?: ApplicationGuide;
  };
};

type ApplicationGuide = {
  language: "English" | "German";
  positioning: string;
  readiness?: "ready" | "needs_confirmation" | "weak_fit";
  roleMission?: string;
  hiringPriorities?: string[];
  mustHave?: string[];
  niceToHave?: string[];
  hardConstraints?: string[];
  evidenceMatrix?: Array<{
    requirement: string;
    importance: "required" | "preferred";
    status: "verified" | "transferable" | "needs_confirmation" | "missing";
    evidence: string;
    action: string;
  }>;
  clarificationQuestions?: Array<{
    id: string;
    requirement: string;
    question: string;
    why: string;
    claimIfConfirmed: string;
    blocking: boolean;
  }>;
  resumePlan?: {
    targetHeadline: string;
    summaryFocus: string;
    evidenceToLead: string[];
    bulletStrategy: string[];
  };
  coverLetterPlan?: {
    openingAngle: string;
    proofPoints: string[];
    motivationAngle: string;
  };
  cvImprovements: string[];
  coverLetterStrategy: string[];
  risks: string[];
  keywords: string[];
  applicationQuestions: string[];
  finalChecklist: string[];
};

type WorkspaceApplicationDocument = {
  id: string;
  artifactId?: string;
  title: string;
  fileName: string;
  fileSize: string;
  fileType: string;
  uploadedAt: string;
  dataUrl: string;
};

type WorkspaceApplication = {
  id: string;
  status: string;
  nextStep: string;
  notes: string;
  job: WorkspaceJob;
  documents: WorkspaceApplicationDocument[];
};

type WorkspaceProfile = {
  name: string;
  current_role: string;
  desired_role: string;
  location: string;
  headline: string;
  skills: string;
  experience: string;
  education: string;
  documents: string;
  resume_file_name: string;
  resume_file_size: string;
  resume_updated_at: string;
  resume_data_url: string;
};

type ProfileSourceDocument = {
  id: string;
  title: string;
  category: string;
  language: string;
  file_name: string;
  file_size: string;
  file_type: string;
  uploaded_at: string;
  data_url: string;
};

type GeneratedDocumentVersion = {
  id: string;
  version: number;
  content: string;
  createdAt: string;
  factualValidation: {
    status?: string;
    checkedChanges?: number;
  };
  visualValidation: {
    status?: string;
    sourcePageCount?: number;
    renderedPageCount?: number;
    linksPreserved?: boolean;
    sourceLinkCount?: number;
    renderedLinkCount?: number;
    tableOverflow?: boolean;
  };
  diff: Array<{
    blockId: string;
    type: string;
    original: string;
    replacement: string;
    reason: string;
  }>;
};

type GeneratedDocument = {
  id: string;
  type: "cover_letter" | "tailored_resume";
  title: string;
  jobId: string | null;
  applicationIds: string[];
  currentVersion: number;
  createdAt: string;
  updatedAt: string;
  generationFingerprint: string | null;
  generationModel: string | null;
  inputVersions: GenerationInputVersions | Record<string, unknown>;
  versions: GeneratedDocumentVersion[];
};

type DocumentTemplate = {
  id: string;
  type: "cover_letter" | "tailored_resume";
  name: string;
  fileName: string;
  extractedText: string;
  createdAt: string;
  updatedAt: string;
};

type ApplicationWorkspaceProps = {
  application: WorkspaceApplication | null;
  profile: WorkspaceProfile;
  onBack: () => void;
  onOpenAssistant: (prompt: string, applicationId: string) => void;
  onDocumentAttached: (
    applicationId: string,
    document: {
      artifactId: string;
      title: string;
      fileName: string;
      fileType: string;
      uploadedAt: string;
      dataUrl: string;
    },
  ) => void;
  onMarkApplied: (applicationId: string) => void;
  onRefreshAnalysis: (applicationId: string) => void;
  isAnalysisRefreshing: boolean;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const docxContentType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const confirmationAnswerMaxChars = 1_500;
function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function currentContent(document: GeneratedDocument | undefined) {
  if (!document) return "";
  const content = document.versions.find((version) => version.version === document.currentVersion)?.content ?? "";
  if (document.type !== "tailored_resume") return content;
  try {
    const payload = JSON.parse(content) as {
      replacements?: Array<{ blockId?: string; replacement?: string; reason?: string }>;
    };
    if (!Array.isArray(payload.replacements)) return content;
    if (payload.replacements.length === 0) return "No safe block replacements were needed.";
    return payload.replacements.map((replacement) => (
      `${replacement.blockId ?? "Block"}: ${replacement.replacement ?? ""}${replacement.reason ? `\nWhy: ${replacement.reason}` : ""}`
    )).join("\n\n");
  } catch {
    return content;
  }
}

function documentFileName(document: GeneratedDocument, version = document.currentVersion) {
  const base = document.title.trim().replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^[._-]+|[._-]+$/g, "") || "tasko-document";
  return `${base}-v${version}.docx`;
}

function formatVersionTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

function generationFingerprintInputs(
  application: WorkspaceApplication,
  profile: WorkspaceProfile,
  applicationGuide: ApplicationGuide | undefined,
  sourceDocument: ProfileSourceDocument,
  language: string,
  clarificationQuestions: NonNullable<ApplicationGuide["clarificationQuestions"]>,
  candidateConfirmations: Record<string, CandidateConfirmation>,
): GenerationFingerprintInputs {
  const job = application.job;
  return {
    vacancy: serializeJob(job),
    profile,
    applicationGuide: applicationGuide ?? null,
    sourceDocument: {
      id: sourceDocument.id,
      title: sourceDocument.title,
      category: sourceDocument.category,
      fileName: sourceDocument.file_name,
      fileType: sourceDocument.file_type,
      uploadedAt: sourceDocument.uploaded_at,
      dataUrl: sourceDocument.data_url,
    },
    language,
    confirmations: clarificationQuestions.flatMap((question) => {
      const confirmation = candidateConfirmations[question.id];
      if (!confirmation) return [];
      return [{
        questionId: question.id,
        requirement: question.requirement,
        blocking: question.blocking,
        response: confirmation.response,
        exampleText: confirmation.exampleText.trim(),
      }];
    }),
  };
}

function documentValidationEvidence(
  profile: WorkspaceProfile,
  applicationGuide: ApplicationGuide | undefined,
  clarificationQuestions: NonNullable<ApplicationGuide["clarificationQuestions"]>,
  candidateConfirmations: Record<string, CandidateConfirmation>,
) {
  return {
    profile: {
      name: profile.name,
      currentRole: profile.current_role,
      desiredRole: profile.desired_role,
      location: profile.location,
      headline: profile.headline,
      skills: profile.skills,
      experience: profile.experience,
      education: profile.education,
    },
    confirmations: clarificationQuestions.flatMap((question) => {
      const confirmation = candidateConfirmations[question.id];
      if (!confirmation || confirmation.response === "no") return [];
      return [{
        requirement: question.requirement,
        response: confirmation.response,
        exampleText: confirmation.exampleText.trim(),
      }];
    }),
    verifiedGuideEvidence: applicationGuide?.evidenceMatrix
      ?.filter((item) => item.status === "verified" || item.status === "transferable")
      .map((item) => ({ requirement: item.requirement, evidence: item.evidence })) ?? [],
  };
}

function inferSourceLanguage(fileName: string, title = "") {
  const value = `${fileName} ${title}`.toLowerCase();
  if (/(?:^|[\s_.-])(de|deu|ger)(?:[\s_.-]|$)|deutsch|german/.test(value)) return "German";
  if (/(?:^|[\s_.-])(en|eng)(?:[\s_.-]|$)|english/.test(value)) return "English";
  return "";
}

function detectLegacyJobLanguage(job: WorkspaceJob) {
  const text = [job.title, job.overview, ...job.requirements, ...job.responsibilities].join(" ").toLowerCase();
  const germanMarkers = [" der ", " die ", " das ", " und ", " mit ", " für ", " wir ", " sie ", "aufgaben", "anforderungen", "kenntnisse", "bewerbung"];
  const englishMarkers = [" the ", " and ", " with ", " for ", " we ", " you ", "responsibilities", "requirements", "skills", "application"];
  const padded = ` ${text} `;
  const germanScore = germanMarkers.reduce((score, marker) => score + padded.split(marker).length - 1, 0);
  const englishScore = englishMarkers.reduce((score, marker) => score + padded.split(marker).length - 1, 0);
  return germanScore > englishScore ? "German" : "English";
}

function reviewSection(title: string, values: string[]) {
  return values.length ? `${title}\n${values.map((value) => `• ${value}`).join("\n")}` : "";
}

function buildSavedApplicationReview(job: WorkspaceJob) {
  if (!hasCurrentApplicationGuide(job.aiMatch)) return "";
  const guide = job.aiMatch?.applicationGuide;
  if (!guide) return "";
  const language = guide?.language || detectLegacyJobLanguage(job);
  const reasons = job.aiMatch?.reasons ?? [];
  const gaps = job.aiMatch?.gaps ?? [];
  const sections = [
    `VACANCY LANGUAGE: ${language}`,
    reviewSection("ROLE MISSION", guide.roleMission ? [guide.roleMission] : []),
    reviewSection("BEST POSITIONING", [guide?.positioning || reasons[0] || `Emphasize verified experience that is directly relevant to ${job.title}.`]),
    reviewSection("HIRING PRIORITIES", guide.hiringPriorities ?? []),
    reviewSection("MUST HAVE", guide.mustHave ?? []),
    reviewSection("NICE TO HAVE", guide.niceToHave ?? []),
    reviewSection("HARD CONSTRAINTS", guide.hardConstraints ?? []),
    reviewSection("CV IMPROVEMENTS", guide?.cvImprovements?.length ? guide.cvImprovements : gaps.length ? gaps : reasons),
    reviewSection("COVER LETTER STRATEGY", guide?.coverLetterStrategy?.length ? guide.coverLetterStrategy : reasons),
    reviewSection("GAPS AND RISKS", guide?.risks?.length ? guide.risks : gaps),
    reviewSection("KEYWORDS AND EVIDENCE TO EMPHASIZE", guide?.keywords?.length ? guide.keywords : job.skills.slice(0, 8)),
    reviewSection("LIKELY APPLICATION QUESTIONS", guide?.applicationQuestions ?? []),
    reviewSection("FINAL BEFORE-SUBMITTING CHECKLIST", guide?.finalChecklist?.length ? guide.finalChecklist : ["Verify every claim against the source CV.", "Confirm the selected documents and language before submitting."]),
  ];
  return sections.filter(Boolean).join("\n\n");
}

async function readApiError(response: Response, fallback: string) {
  const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
  return typeof payload?.detail === "string" && payload.detail.trim() ? payload.detail : fallback;
}

function serializeJob(job: WorkspaceJob) {
  return {
    id: job.id,
    title: job.title,
    company: job.company,
    location: job.location,
    type: job.type,
    match: job.match,
    overview: job.overview,
    responsibilities: job.responsibilities,
    requirements: job.requirements,
    skills: job.skills,
    aiMatch: job.aiMatch ?? null,
  };
}

function parseProfileSourceDocuments(profile: WorkspaceProfile): ProfileSourceDocument[] {
  const sources: ProfileSourceDocument[] = [];
  if (profile.resume_file_name && profile.resume_data_url) {
    sources.push({
      id: "profile-main-resume",
      title: "Main profile CV",
      category: "CV / Resume",
      language: inferSourceLanguage(profile.resume_file_name, "Main profile CV"),
      file_name: profile.resume_file_name,
      file_size: profile.resume_file_size,
      file_type: "application/octet-stream",
      uploaded_at: profile.resume_updated_at,
      data_url: profile.resume_data_url,
    });
  }
  if (!profile.documents.trim()) return sources;
  try {
    const parsed = JSON.parse(profile.documents) as unknown;
    if (!Array.isArray(parsed)) return sources;
    for (const value of parsed) {
      if (!value || typeof value !== "object") continue;
      const candidate = value as Partial<ProfileSourceDocument>;
      if (typeof candidate.id !== "string" || typeof candidate.data_url !== "string" || !candidate.data_url || typeof candidate.file_name !== "string" || !candidate.file_name) continue;
      sources.push({
        id: candidate.id,
        title: candidate.title?.trim() || candidate.file_name,
        category: candidate.category?.trim() || "Other",
        language: candidate.language?.trim() || inferSourceLanguage(candidate.file_name, candidate.title ?? ""),
        file_name: candidate.file_name,
        file_size: candidate.file_size?.trim() || "",
        file_type: candidate.file_type?.trim() || "application/octet-stream",
        uploaded_at: candidate.uploaded_at?.trim() || "",
        data_url: candidate.data_url,
      });
    }
  } catch {
    return sources;
  }
  return sources;
}

function assistantSourcePayload(source: ProfileSourceDocument) {
  return {
    id: source.id,
    title: source.title,
    category: source.category,
    fileName: source.file_name,
    dataUrl: source.data_url,
  };
}

function evidenceStatusMeta(status: NonNullable<ApplicationGuide["evidenceMatrix"]>[number]["status"]) {
  if (status === "verified") return { label: "Verified", className: "border-success/35 bg-success/10 text-success" };
  if (status === "transferable") return { label: "Transferable", className: "border-[#2f80ed]/35 bg-[#2f80ed]/10 text-[#8cc7ff]" };
  if (status === "missing") return { label: "Missing", className: "border-red-400/35 bg-red-500/10 text-red-200" };
  return { label: "Confirm", className: "border-amber-400/35 bg-amber-400/10 text-amber-200" };
}

export function ApplicationWorkspace({
  application,
  profile,
  onBack,
  onOpenAssistant,
  onDocumentAttached,
  onMarkApplied,
  onRefreshAnalysis,
  isAnalysisRefreshing,
}: ApplicationWorkspaceProps) {
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [documentsLoaded, setDocumentsLoaded] = useState(false);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [selectedResumeSourceId, setSelectedResumeSourceId] = useState("");
  const [selectedCoverSourceId, setSelectedCoverSourceId] = useState("");
  const [languageMode, setLanguageMode] = useState<"auto" | "English" | "German">("auto");
  const [isResumeSourceManual, setIsResumeSourceManual] = useState(false);
  const [isCoverSourceManual, setIsCoverSourceManual] = useState(false);
  const [temporarySources, setTemporarySources] = useState<ProfileSourceDocument[]>([]);
  const [generationType, setGenerationType] = useState<GeneratedDocument["type"] | "">("");
  const [isGeneratingPack, setIsGeneratingPack] = useState(false);
  const [restoringVersionKey, setRestoringVersionKey] = useState("");
  const [currentGenerationFingerprints, setCurrentGenerationFingerprints] = useState<Partial<Record<GeneratedDocument["type"], string>>>({});
  const [documentError, setDocumentError] = useState("");
  const [candidateConfirmations, setCandidateConfirmations] = useState<Record<string, CandidateConfirmation>>({});
  const [confirmationsDirty, setConfirmationsDirty] = useState(false);
  const [confirmationSyncStatus, setConfirmationSyncStatus] = useState<"loading" | "saving" | "saved" | "unsaved" | "error">("loading");
  const [confirmationSyncMessage, setConfirmationSyncMessage] = useState("");
  const [advice, setAdvice] = useState("");
  const [advicePrompt, setAdvicePrompt] = useState("");
  const [isLoadingAdvice, setIsLoadingAdvice] = useState(false);
  const [analysisTab, setAnalysisTab] = useState<"overview" | "evidence" | "strategy">("overview");

  useEffect(() => {
    if (!application) return;
    setDocumentsLoaded(false);
    setDocuments([]);
    const controller = new AbortController();
    Promise.all([
      fetch(`${apiBaseUrl}/documents?applicationId=${encodeURIComponent(application.id)}`, { signal: controller.signal }),
      fetch(`${apiBaseUrl}/documents/templates/library`, { signal: controller.signal }),
    ])
      .then(async ([documentsResponse, templatesResponse]) => {
        if (!documentsResponse.ok || !templatesResponse.ok) throw new Error("Application documents are temporarily unavailable");
        const loadedDocuments = await documentsResponse.json() as GeneratedDocument[];
        const loadedTemplates = await templatesResponse.json() as DocumentTemplate[];
        setDocuments(loadedDocuments);
        setTemplates(loadedTemplates);
        setDocumentsLoaded(true);
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setDocumentError(error instanceof Error ? error.message : "Application documents are temporarily unavailable");
      });
    return () => controller.abort();
  }, [application]);

  const latestResume = useMemo(
    () => documents.find((document) => document.type === "tailored_resume"),
    [documents],
  );
  const latestCoverLetter = useMemo(
    () => documents.find((document) => document.type === "cover_letter"),
    [documents],
  );
  const profileSources = useMemo(
    () => [...temporarySources, ...parseProfileSourceDocuments(profile)],
    [profile, temporarySources],
  );
  const resumeSources = useMemo(
    () => profileSources.filter((source) => source.category === "CV / Resume" && source.file_name.toLowerCase().endsWith(".docx")),
    [profileSources],
  );
  const coverSources = useMemo(
    () => profileSources.filter((source) => source.category === "Cover Letter" && source.file_name.toLowerCase().endsWith(".docx")),
    [profileSources],
  );
  const analysisStatus = getAiMatchAnalysisStatus(application?.job.aiMatch);
  const hasCurrentAnalysis = analysisStatus === "current";
  const isAnalysisOutdated = analysisStatus === "outdated";
  const isLegacyAnalysis = isLegacyAiMatch(application?.job.aiMatch);
  const applicationReview = useMemo(
    () => application ? buildSavedApplicationReview(application.job) : "",
    [application],
  );
  const applicationGuide = hasCurrentAnalysis ? application?.job.aiMatch?.applicationGuide : undefined;
  const clarificationQuestions = applicationGuide?.clarificationQuestions ?? [];
  const unansweredBlockingQuestions = clarificationQuestions.filter(
    (question) => question.blocking && !isCandidateConfirmationComplete(question, candidateConfirmations[question.id]),
  );
  const hasIncompleteBlockingConfirmations = unansweredBlockingQuestions.length > 0;
  const hasOversizedConfirmation = clarificationQuestions.some(
    (question) => (candidateConfirmations[question.id]?.exampleText.trim().length ?? 0) > confirmationAnswerMaxChars,
  );
  const vacancyLanguage = applicationGuide?.language || (application ? detectLegacyJobLanguage(application.job) : "");
  const effectiveLanguage = languageMode === "auto" ? vacancyLanguage : languageMode;

  useEffect(() => {
    setLanguageMode("auto");
    setIsResumeSourceManual(false);
    setIsCoverSourceManual(false);
    setSelectedResumeSourceId("");
    setSelectedCoverSourceId("");
    setAnalysisTab("overview");
    if (!application) {
      setCandidateConfirmations({});
      setConfirmationsDirty(false);
      return;
    }
    const controller = new AbortController();
    const applicationId = application.id;
    const legacyStorageKey = `tasko.application-confirmations.${applicationId}`;
    setCandidateConfirmations({});
    setConfirmationsDirty(false);
    setConfirmationSyncStatus("loading");
    setConfirmationSyncMessage("");

    async function loadCandidateConfirmations() {
      try {
        const response = await fetch(
          `${apiBaseUrl}/applications/${encodeURIComponent(applicationId)}/confirmations`,
          { cache: "no-store", signal: controller.signal },
        );
        if (!response.ok && response.status !== 404) {
          throw new Error(await readApiError(response, "Candidate confirmations could not be loaded"));
        }
        const storedConfirmations = response.ok ? await response.json() as CandidateConfirmation[] : [];
        const questionsById = new Map(clarificationQuestions.map((question) => [question.id, question]));
        const backendNeedsSync = storedConfirmations.some((confirmation) => {
          const question = questionsById.get(confirmation.questionId);
          return !question || confirmation.requirement !== question.requirement || confirmation.blocking !== question.blocking;
        });
        const backendById = Object.fromEntries(storedConfirmations.flatMap((confirmation) => {
          const question = questionsById.get(confirmation.questionId);
          if (!question) return [];
          return [[confirmation.questionId, {
            ...confirmation,
            requirement: question.requirement,
            blocking: question.blocking,
          }]];
        }));
        let legacyById: Record<string, CandidateConfirmation> = {};
        try {
          const storedLegacyAnswers = window.localStorage.getItem(legacyStorageKey);
          legacyById = importLegacyCandidateConfirmations(
            storedLegacyAnswers ? JSON.parse(storedLegacyAnswers) : null,
            clarificationQuestions,
          );
        } catch {
          legacyById = {};
        }

        const missingLegacyConfirmations = Object.fromEntries(
          Object.entries(legacyById).filter(([questionId]) => !backendById[questionId]),
        );
        const shouldSync = Object.keys(missingLegacyConfirmations).length > 0 || backendNeedsSync;
        setCandidateConfirmations({ ...missingLegacyConfirmations, ...backendById });
        setConfirmationsDirty(shouldSync);
        setConfirmationSyncStatus(shouldSync ? "unsaved" : "saved");
        setConfirmationSyncMessage(Object.keys(missingLegacyConfirmations).length > 0 ? "Legacy answers imported — checking before backend save" : backendNeedsSync ? "Requirements changed — updating saved answers" : "");
        if (Object.keys(legacyById).length > 0 && Object.keys(missingLegacyConfirmations).length === 0) {
          window.localStorage.removeItem(legacyStorageKey);
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setConfirmationSyncStatus("error");
        setConfirmationSyncMessage(error instanceof Error ? error.message : "Candidate confirmations could not be loaded");
      }
    }

    void loadCandidateConfirmations();
    return () => controller.abort();
  }, [application?.id, application?.job.aiMatch?.updatedAt]);

  useEffect(() => {
    if (!application || !confirmationsDirty) return;
    if (hasIncompleteBlockingConfirmations || hasOversizedConfirmation) {
      setConfirmationSyncStatus("unsaved");
      setConfirmationSyncMessage(
        hasOversizedConfirmation
          ? `Shorten examples to ${confirmationAnswerMaxChars.toLocaleString()} characters`
          : "Choose an answer and add a concrete example for each required yes or partial response",
      );
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(async () => {
      setConfirmationSyncStatus("saving");
      setConfirmationSyncMessage("");
      try {
        const confirmations = clarificationQuestions.flatMap((question) => {
          const confirmation = candidateConfirmations[question.id];
          if (!confirmation) return [];
          return [{
            ...confirmation,
            requirement: question.requirement,
            blocking: question.blocking,
          }];
        });
        const response = await fetch(
          `${apiBaseUrl}/applications/${encodeURIComponent(application.id)}/confirmations`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              confirmations,
              requiredQuestionIds: clarificationQuestions.filter((question) => question.blocking).map((question) => question.id),
            }),
            signal: controller.signal,
          },
        );
        if (!response.ok) throw new Error(await readApiError(response, "Candidate confirmations could not be saved"));
        const savedConfirmations = await response.json() as CandidateConfirmation[];
        setCandidateConfirmations(Object.fromEntries(savedConfirmations.map((confirmation) => [confirmation.questionId, confirmation])));
        setConfirmationsDirty(false);
        setConfirmationSyncStatus("saved");
        setConfirmationSyncMessage("");
        window.localStorage.removeItem(`tasko.application-confirmations.${application.id}`);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setConfirmationSyncStatus("error");
        setConfirmationSyncMessage(error instanceof Error ? error.message : "Candidate confirmations could not be saved");
      }
    }, 600);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [application, candidateConfirmations, clarificationQuestions, confirmationsDirty, hasIncompleteBlockingConfirmations, hasOversizedConfirmation]);

  useEffect(() => {
    if (!effectiveLanguage) return;
    if (!isResumeSourceManual) {
      const matchingResume = resumeSources.find((source) => source.language === effectiveLanguage);
      setSelectedResumeSourceId(matchingResume?.id ?? "");
    }
    if (!isCoverSourceManual) {
      const matchingCover = coverSources.find((source) => source.language === effectiveLanguage);
      setSelectedCoverSourceId(matchingCover?.id ?? "");
    }
  }, [coverSources, effectiveLanguage, isCoverSourceManual, isResumeSourceManual, resumeSources]);

  useEffect(() => {
    setCurrentGenerationFingerprints({});
    if (!application || !applicationGuide || !effectiveLanguage) return;

    let cancelled = false;
    const timeoutId = window.setTimeout(async () => {
      const selectedSources: Array<[GeneratedDocument["type"], ProfileSourceDocument | undefined]> = [
        ["tailored_resume", profileSources.find((source) => source.id === selectedResumeSourceId)],
        ["cover_letter", profileSources.find((source) => source.id === selectedCoverSourceId)],
      ];
      const fingerprints = await Promise.all(selectedSources.map(async ([type, source]) => {
        if (!source) return [type, undefined] as const;
        const provenance = await createGenerationProvenance(generationFingerprintInputs(
          application,
          profile,
          applicationGuide,
          source,
          effectiveLanguage || source.language || "English",
          clarificationQuestions,
          candidateConfirmations,
        ));
        return [type, provenance.generationFingerprint] as const;
      }));
      if (!cancelled) {
        setCurrentGenerationFingerprints(Object.fromEntries(
          fingerprints.filter((entry): entry is [GeneratedDocument["type"], string] => Boolean(entry[1])),
        ));
      }
    }, 120);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [application, applicationGuide, candidateConfirmations, clarificationQuestions, effectiveLanguage, profile, profileSources, selectedCoverSourceId, selectedResumeSourceId]);

  if (!application) {
    return (
      <section className="grid min-w-0 flex-1 place-items-center p-6">
        <div className="panel max-w-md p-6 text-center">
          <FileText className="mx-auto h-8 w-8 text-muted" />
          <h1 className="mt-3 text-lg font-bold text-white">No application selected</h1>
          <Button className="mt-4 bg-accent text-white" onClick={onBack}><ArrowLeft className="h-4 w-4" /> Back to applications</Button>
        </div>
      </section>
    );
  }

  const activeApplication = application;
  const jobUrl = activeApplication.job.applyUrl || activeApplication.job.sourceUrl || "";
  const profileReady = Boolean(profile.name && (profile.experience || profile.resume_file_name));
  const confirmationsReady = hasCurrentAnalysis && unansweredBlockingQuestions.length === 0 && !hasOversizedConfirmation;
  const analysisRequiredLabel = isAnalysisOutdated ? "Refresh analysis first" : "AI Match required";
  const isResumeOutdated = Boolean(latestResume && isGeneratedDocumentOutdated(
    latestResume.generationFingerprint,
    currentGenerationFingerprints.tailored_resume,
  ));
  const isCoverLetterOutdated = Boolean(latestCoverLetter && isGeneratedDocumentOutdated(
    latestCoverLetter.generationFingerprint,
    currentGenerationFingerprints.cover_letter,
  ));
  const resumeReady = Boolean(latestResume && !isResumeOutdated);
  const coverLetterReady = Boolean(latestCoverLetter && !isCoverLetterOutdated);
  const checklist = [
    { label: "Candidate profile", ready: profileReady },
    { label: "Vacancy analysis", ready: hasCurrentAnalysis },
    { label: "Required confirmations", ready: confirmationsReady },
    { label: "Tailored CV", ready: resumeReady },
    { label: "Cover letter", ready: coverLetterReady },
    { label: "Application link", ready: Boolean(jobUrl) },
  ];
  const readyCount = checklist.filter((item) => item.ready).length;
  const progress = Math.round((readyCount / checklist.length) * 100);
  const preparationSteps = [
    { label: "Review match", detail: isAnalysisOutdated ? "Analysis outdated" : "Positioning and requirements", ready: hasCurrentAnalysis, icon: Target },
    { label: "Confirm facts", detail: !hasCurrentAnalysis ? "Refresh analysis first" : hasOversizedConfirmation ? "Shorten a long answer" : unansweredBlockingQuestions.length ? `${unansweredBlockingQuestions.length} answer${unansweredBlockingQuestions.length === 1 ? "" : "s"} required` : "Evidence confirmed", ready: confirmationsReady, icon: MessageSquareText },
    { label: "Create documents", detail: resumeReady && coverLetterReady ? "Application pack ready" : "CV and cover letter", ready: resumeReady && coverLetterReady, icon: FileText },
    { label: "Final review", detail: progress === 100 ? "Ready to submit" : `${readyCount} of ${checklist.length} checks ready`, ready: progress === 100, icon: ShieldCheck },
  ];

  function updateCandidateConfirmation(
    question: NonNullable<ApplicationGuide["clarificationQuestions"]>[number],
    updates: Partial<Pick<CandidateConfirmation, "response" | "exampleText">>,
  ) {
    setCandidateConfirmations((currentConfirmations) => {
      const current = currentConfirmations[question.id];
      const next: CandidateConfirmation = {
        questionId: question.id,
        requirement: question.requirement,
        response: updates.response ?? current?.response ?? "yes",
        exampleText: updates.exampleText ?? current?.exampleText ?? "",
        blocking: question.blocking,
        updatedAt: current?.updatedAt ?? "",
      };
      return { ...currentConfirmations, [question.id]: next };
    });
    setConfirmationsDirty(true);
    setConfirmationSyncStatus("unsaved");
    setConfirmationSyncMessage("");
  }

  async function askAssistant(
    message: string,
    sources: ProfileSourceDocument[] = [],
    candidateConfirmations: Array<{ requirement: string; question: string; answer: string }> = [],
  ) {
    if (!message.trim()) return { message: "", model: "unknown" };
    const response = await fetch(`${apiBaseUrl}/assistant/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        threadId: createId(`application-workspace-${activeApplication.id}`),
        message,
        contextKind: "application",
        contextId: activeApplication.id,
        application: {
          id: activeApplication.id,
          status: activeApplication.status,
          nextStep: activeApplication.nextStep,
          notes: activeApplication.notes,
          job: serializeJob(activeApplication.job),
        },
        sourceDocuments: sources.map(assistantSourcePayload),
        candidateConfirmations,
      }),
    });
    if (response.status === 413) {
      throw new Error("The application context is larger than the assistant can process. Your answers are saved — shorten unusually long confirmations and try again.");
    }
    if (!response.ok) throw new Error(await readApiError(response, "AI request failed"));
    const payload = await response.json() as {
      message?: string;
      metadata?: { metrics?: { model?: string } };
    };
    return {
      message: payload.message?.trim() ?? "",
      model: payload.metadata?.metrics?.model?.trim() || "unknown",
    };
  }

  async function generateDocument(type: GeneratedDocument["type"]) {
    setGenerationType(type);
    setDocumentError("");
    try {
      if (!documentsLoaded) throw new Error("Document history is still loading");
      const isCoverLetter = type === "cover_letter";
      const selectedSourceId = isCoverLetter ? selectedCoverSourceId : selectedResumeSourceId;
      const selectedSource = profileSources.find((source) => source.id === selectedSourceId);
      if (!selectedSource || !selectedSource.file_name.toLowerCase().endsWith(".docx")) {
        throw new Error(`Select a DOCX ${isCoverLetter ? "cover letter" : "CV"} before generating`);
      }
      if (!applicationReview) {
        throw new Error(isAnalysisOutdated ? "Refresh the outdated analysis before generating documents" : "Run AI Match before generating documents");
      }
      if (unansweredBlockingQuestions.length > 0) {
        throw new Error("Answer the required confirmation questions before generating documents");
      }
      const oversizedConfirmation = clarificationQuestions.find(
        (question) => (candidateConfirmations[question.id]?.exampleText.trim().length ?? 0) > confirmationAnswerMaxChars,
      );
      if (oversizedConfirmation) {
        throw new Error(`Shorten the highlighted confirmation to ${confirmationAnswerMaxChars.toLocaleString()} characters before generating`);
      }
      const assistantConfirmations = clarificationQuestions
        .flatMap((question) => {
          const confirmation = candidateConfirmations[question.id];
          if (!confirmation) return [];
          const example = confirmation.exampleText.trim();
          return [{
            requirement: question.requirement,
            question: question.question,
            answer: `${confirmation.response.toUpperCase()}${example ? `: ${example}` : ""}`,
          }];
        });
      const targetLanguage = effectiveLanguage || selectedSource.language || "English";
      const provenance = await createGenerationProvenance(generationFingerprintInputs(
        activeApplication,
        profile,
        applicationGuide,
        selectedSource,
        targetLanguage,
        clarificationQuestions,
        candidateConfirmations,
      ));
      const prompt = isCoverLetter
        ? `Rewrite the selected DOCX cover letter in ${targetLanguage} for this vacancy. Treat the saved application guide, candidate profile, selected source document, and candidate confirmations in CONTEXT_JSON as factual data. Follow the guide's positioning, evidence map, risks, and cover-letter plan. Candidate confirmations take precedence over inferred evidence; a negative answer means the claim must be omitted. Use only verified facts and never invent achievements or metrics. Return only the complete letter text without Markdown or commentary, with a greeting, focused body paragraphs, and a professional closing.`
        : `Tailor the selected DOCX resume in ${targetLanguage} while preserving its layout. The selected source document in CONTEXT_JSON uses format resume-blocks-v1 and contains blocks with stable blockId, type, and original fields. Treat the application guide, candidate profile, source blocks, and candidate confirmations as factual data; confirmations take precedence over inferred evidence. Return only valid JSON with this exact shape: {"replacements":[{"blockId":"block-0001","original":"exact original block text","replacement":"new text","reason":"short evidence-based reason"}]}. Include only blocks that should change. Copy blockId and original exactly from CONTEXT_JSON. Never change a block whose type is immutable. Preserve every tab (\\t) and line break (\\n) at the same position in the replacement's inline structure so DOCX hyperlinks, runs, and formatting remain valid. Do not add IDs, remove blocks, merge blocks, split blocks, use Markdown, or invent facts or metrics. Prefer targeted replacements for summary, skill, and achievement blocks; preserve headings, contacts, and table structure.`;
      const assistantResult = await askAssistant(prompt, [selectedSource], assistantConfirmations);
      const content = assistantResult.message;
      if (!content) throw new Error("AI returned an empty document");

      const templateId = await ensureSourceTemplate(selectedSource, type);

      const title = `${isCoverLetter ? "Cover letter" : "Tailored CV"} · ${activeApplication.job.title} · ${activeApplication.job.company}`;
      const existingDocument = isCoverLetter ? latestCoverLetter : latestResume;
      const response = await fetch(
        existingDocument
          ? `${apiBaseUrl}/documents/${encodeURIComponent(existingDocument.id)}`
          : `${apiBaseUrl}/documents`,
        {
          method: existingDocument ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content,
            templateId,
            generationFingerprint: provenance.generationFingerprint,
            generationModel: assistantResult.model,
            inputVersions: provenance.inputVersions,
            validationEvidence: documentValidationEvidence(
              profile,
              applicationGuide,
              clarificationQuestions,
              candidateConfirmations,
            ),
            ...(existingDocument ? {} : {
              type,
              title,
              jobId: activeApplication.job.id,
              applicationId: activeApplication.id,
            }),
          }),
        },
      );
      if (!response.ok) throw new Error(await readApiError(response, "Document save failed"));
      const saved = await response.json() as GeneratedDocument;
      setDocuments((current) => [saved, ...current.filter((document) => document.id !== saved.id)]);
      setCurrentGenerationFingerprints((current) => ({
        ...current,
        [type]: provenance.generationFingerprint,
      }));
      onDocumentAttached(activeApplication.id, {
        artifactId: saved.id,
        title: saved.title,
        fileName: documentFileName(saved),
        fileType: docxContentType,
        uploadedAt: saved.updatedAt,
        dataUrl: `${apiBaseUrl}/documents/${encodeURIComponent(saved.id)}/download`,
      });
      return true;
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : "Document generation failed");
      return false;
    } finally {
      setGenerationType("");
    }
  }

  async function generatePack() {
    setIsGeneratingPack(true);
    const resumeReady = await generateDocument("tailored_resume");
    if (resumeReady) await generateDocument("cover_letter");
    setIsGeneratingPack(false);
  }

  async function restoreDocumentVersion(document: GeneratedDocument, version: number) {
    const restoreKey = `${document.id}:${version}`;
    setRestoringVersionKey(restoreKey);
    setDocumentError("");
    try {
      const response = await fetch(
        `${apiBaseUrl}/documents/${encodeURIComponent(document.id)}/restore`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version }),
        },
      );
      if (!response.ok) throw new Error(await readApiError(response, "Document version could not be restored"));
      const restored = await response.json() as GeneratedDocument;
      setDocuments((current) => [
        restored,
        ...current.filter((currentDocument) => currentDocument.id !== restored.id),
      ]);
      onDocumentAttached(activeApplication.id, {
        artifactId: restored.id,
        title: restored.title,
        fileName: documentFileName(restored),
        fileType: docxContentType,
        uploadedAt: restored.updatedAt,
        dataUrl: `${apiBaseUrl}/documents/${encodeURIComponent(restored.id)}/download`,
      });
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : "Document version could not be restored");
    } finally {
      setRestoringVersionKey("");
    }
  }

  async function ensureSourceTemplate(source: ProfileSourceDocument, type: GeneratedDocument["type"]) {
    const templateName = `${source.title} · ${source.uploaded_at || source.id}`.slice(0, 240);
    const existing = templates.find((template) => template.type === type && template.fileName === source.file_name && template.name === templateName);
    if (existing) return existing.id;
    const response = await fetch(`${apiBaseUrl}/documents/templates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type,
        name: templateName,
        fileName: source.file_name,
        dataUrl: source.data_url,
      }),
    });
    if (!response.ok) throw new Error(await readApiError(response, "Selected DOCX could not be used as a Word template"));
    const uploaded = await response.json() as DocumentTemplate;
    setTemplates((current) => [uploaded, ...current]);
    return uploaded.id;
  }

  async function attachWorkspaceSource(file: File | undefined, category: "CV / Resume" | "Cover Letter") {
    if (!file) return;
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".docx")) {
      setDocumentError("CV and cover letter sources must be DOCX files so their design can be preserved");
      return;
    }
    if (file.size > 10_000_000) {
      setDocumentError("Source document must be under 10 MB");
      return;
    }
    setDocumentError("");
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Source document reading failed"));
        reader.onerror = () => reject(new Error("Source document reading failed"));
        reader.readAsDataURL(file);
      });
      const source: ProfileSourceDocument = {
        id: createId("workspace-source"),
        title: file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "),
        category,
        language: effectiveLanguage || inferSourceLanguage(file.name) || "English",
        file_name: file.name,
        file_size: `${Math.max(1, Math.round(file.size / 1024))} KB`,
        file_type: file.type || "application/octet-stream",
        uploaded_at: new Date().toISOString(),
        data_url: dataUrl,
      };
      setTemporarySources((current) => [source, ...current]);
      if (category === "CV / Resume") {
        setSelectedResumeSourceId(source.id);
        setIsResumeSourceManual(true);
      } else {
        setSelectedCoverSourceId(source.id);
        setIsCoverSourceManual(true);
      }
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : "Source document reading failed");
    }
  }

  async function requestAdvice(prompt: string) {
    setAdvicePrompt(prompt);
    setIsLoadingAdvice(true);
    try {
      setAdvice((await askAssistant(prompt)).message);
    } catch (error) {
      setAdvice(error instanceof Error ? error.message : "Advice request failed");
    } finally {
      setIsLoadingAdvice(false);
    }
  }

  return (
    <section className="job-scroll application-workspace min-w-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5 xl:px-7">
      <div className="mx-auto max-w-[1420px]">
        <button type="button" onClick={onBack} className="mb-4 inline-flex items-center gap-2 text-xs font-semibold text-muted transition hover:text-white">
          <ArrowLeft className="h-4 w-4" /> Applications
        </button>

        <header className="application-hero overflow-hidden rounded-2xl border border-white/[0.09]">
          <div className="relative grid gap-5 px-5 py-6 sm:px-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#ff8b4a]">Application prep</span>
                <span className="rounded-full border border-white/10 bg-white/[0.045] px-2.5 py-1 text-[10px] font-bold capitalize text-[#cbd3df]">{application.status === "draft" ? "In progress" : application.status}</span>
              </div>
              <h1 className="mt-4 max-w-4xl text-2xl font-bold leading-[1.15] tracking-[-0.025em] text-white sm:text-3xl">{application.job.title}</h1>
              <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-[#aeb7c5]">
                <span className="text-[#eef1f6]">{application.job.company}</span><span className="text-white/25">/</span><span>{application.job.location}</span><span className="text-white/25">/</span><span>{application.job.type}</span>
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 lg:justify-end">
              <div className="mr-2 flex h-14 items-center gap-3 rounded-xl border border-success/20 bg-success/[0.07] px-4">
                <div><p className="text-[9px] font-black uppercase tracking-[0.12em] text-[#9aa5b4]">AI match</p><p className="text-xl font-black text-success">{application.job.match}%</p></div>
                <CheckCircle2 className="h-5 w-5 text-success/80" />
              </div>
              <Button variant="ghost" disabled={!jobUrl} onClick={() => jobUrl && window.open(jobUrl, "_blank", "noopener,noreferrer")} className="h-11 rounded-xl border border-white/10 bg-white/[0.035] px-4 text-xs text-[#e6ebf3] hover:bg-white/[0.07] disabled:opacity-45">
                <ExternalLink className="h-4 w-4" /> View vacancy
              </Button>
              <Button onClick={() => jobUrl && window.open(jobUrl, "_blank", "noopener,noreferrer")} disabled={!jobUrl} className="h-11 rounded-xl bg-accent px-4 text-xs font-bold text-white shadow-[0_12px_30px_rgba(255,90,0,0.22)] hover:bg-[#ff6a14] disabled:opacity-45">
                Apply on website <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="grid border-t border-white/[0.07] bg-black/15 sm:grid-cols-2 xl:grid-cols-4">
            {preparationSteps.map((step, index) => {
              const StepIcon = step.icon;
              return (
                <div key={step.label} className={cn("flex min-w-0 items-center gap-3 border-white/[0.07] px-5 py-4 xl:border-r xl:last:border-r-0", index > 0 && "border-t sm:border-t-0", index === 2 && "sm:border-t xl:border-t-0")}>
                  <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-full border text-[11px] font-black", step.ready ? "border-success/25 bg-success/10 text-success" : "border-white/10 bg-white/[0.035] text-[#7f8998]")}>{step.ready ? <Check className="h-4 w-4" /> : <StepIcon className="h-3.5 w-3.5" />}</span>
                  <div className="min-w-0"><p className={cn("truncate text-xs font-bold", step.ready ? "text-white" : "text-[#bbc3cf]")}>{index + 1}. {step.label}</p><p className="mt-0.5 truncate text-[10px] text-[#7f8998]">{step.detail}</p></div>
                </div>
              );
            })}
          </div>
        </header>

        <div className="mt-5 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
          <main className="min-w-0 space-y-5">
            <section className="workspace-card overflow-hidden">
              <div className="flex flex-col gap-4 border-b border-white/[0.07] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent/12 text-accent"><Target className="h-[18px] w-[18px]" /></span>
                  <div><p className="text-[10px] font-black uppercase tracking-[0.14em] text-accent">01 · Understand the role</p><h2 className="mt-1 text-lg font-bold tracking-[-0.01em] text-white">Your application angle</h2><p className="mt-1 text-xs leading-5 text-muted">Review the recommendation before generating any documents.</p></div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button type="button" variant="ghost" disabled={isAnalysisRefreshing} onClick={() => onRefreshAnalysis(activeApplication.id)} className={cn("h-11 rounded-xl border px-3 text-[11px] font-bold", isAnalysisOutdated ? "border-amber-400/30 bg-amber-400/[0.07] text-amber-100 hover:bg-amber-400/10" : "border-white/[0.08] bg-white/[0.025] text-[#dfe5ec] hover:bg-white/[0.06]")}>{isAnalysisRefreshing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}{isAnalysisRefreshing ? "Updating…" : isAnalysisOutdated ? "Update analysis" : "Refresh analysis"}</Button>
                  <label className="flex shrink-0 items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.025] p-1.5 pl-3">
                    <span className="text-[10px] font-bold text-muted">Language</span>
                    <select value={languageMode} onChange={(event) => { setLanguageMode(event.target.value as "auto" | "English" | "German"); setIsResumeSourceManual(false); setIsCoverSourceManual(false); setSelectedResumeSourceId(""); setSelectedCoverSourceId(""); }} className="h-8 rounded-lg border border-white/[0.08] bg-[#151c24] px-2.5 text-[11px] font-bold text-white outline-none focus:border-accent/60">
                      <option value="auto">Auto · {vacancyLanguage || "Detect"}</option><option value="English">English</option><option value="German">German</option>
                    </select>
                  </label>
                </div>
              </div>

              {applicationGuide ? (
                <div className="p-5 sm:p-6">
                  <article className="relative overflow-hidden rounded-2xl border border-accent/20 bg-gradient-to-br from-accent/[0.09] via-white/[0.025] to-transparent p-5 sm:p-6">
                    <div className="absolute -right-16 -top-20 h-52 w-52 rounded-full bg-accent/10 blur-3xl" />
                    <div className="relative grid gap-5 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-start">
                      <div><p className="text-[10px] font-black uppercase tracking-[0.14em] text-[#ff9a63]">Recommended narrative</p><p className="mt-3 text-base font-bold leading-7 text-white sm:text-lg">{applicationGuide.roleMission || activeApplication.job.overview || `Succeed as ${activeApplication.job.title}.`}</p><p className="mt-3 max-w-3xl text-sm leading-6 text-[#c6ced9]">{applicationGuide.positioning}</p></div>
                      <div className="rounded-xl border border-white/[0.08] bg-black/20 p-4">
                        <div className="flex items-center justify-between gap-2"><span className="text-[9px] font-black uppercase tracking-[0.1em] text-muted">Analysis status</span><span className={cn("rounded-full border px-2 py-1 text-[8px] font-black uppercase tracking-wide", applicationGuide.readiness === "ready" ? "border-success/30 bg-success/10 text-success" : applicationGuide.readiness === "weak_fit" ? "border-red-400/30 bg-red-500/10 text-red-200" : "border-amber-400/30 bg-amber-400/10 text-amber-200")}>{(applicationGuide.readiness ?? "needs_confirmation").replace("_", " ")}</span></div>
                        <div className="mt-4 flex flex-wrap gap-1.5">{(applicationGuide.keywords ?? []).slice(0, 8).map((keyword) => <span key={keyword} className="rounded-md border border-white/[0.07] bg-white/[0.04] px-2 py-1 text-[9px] font-semibold text-[#cbd3df]">{keyword}</span>)}</div>
                      </div>
                    </div>
                  </article>

                  <div className="mt-5 flex gap-1 overflow-x-auto rounded-xl border border-white/[0.07] bg-black/20 p-1" role="tablist" aria-label="Application analysis">
                    {[
                      { id: "overview" as const, label: "Role overview" },
                      { id: "evidence" as const, label: `Evidence map${applicationGuide.evidenceMatrix?.length ? ` · ${applicationGuide.evidenceMatrix.length}` : ""}` },
                      { id: "strategy" as const, label: "Document strategy" },
                    ].map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={analysisTab === tab.id} onClick={() => setAnalysisTab(tab.id)} className={cn("min-w-fit flex-1 rounded-lg px-4 py-2.5 text-[11px] font-bold transition", analysisTab === tab.id ? "bg-white/[0.09] text-white shadow-sm" : "text-muted hover:bg-white/[0.04] hover:text-white")}>{tab.label}</button>)}
                  </div>

                  {analysisTab === "overview" ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {[
                        { label: "What they care about", values: applicationGuide.hiringPriorities, tone: "text-[#ff9a63]" },
                        { label: "Must have", values: applicationGuide.mustHave, tone: "text-white" },
                        { label: "Advantage", values: applicationGuide.niceToHave, tone: "text-[#8cc7ff]" },
                        { label: "Constraints to verify", values: applicationGuide.hardConstraints, tone: "text-amber-200" },
                      ].map((group) => <article key={group.label} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-4"><h3 className={cn("text-[10px] font-black uppercase tracking-[0.11em]", group.tone)}>{group.label}</h3>{group.values?.length ? <ul className="mt-3 space-y-2 text-xs leading-5 text-[#b8c1cd]">{group.values.map((value) => <li key={value} className="flex gap-2.5"><CircleDot className="mt-1 h-3 w-3 shrink-0 text-[#647080]" /><span>{value}</span></li>)}</ul> : <p className="mt-3 text-xs text-muted">Nothing critical identified.</p>}</article>)}
                      <article className="rounded-xl border border-success/15 bg-success/[0.035] p-4 md:col-span-2"><h3 className="text-[10px] font-black uppercase tracking-[0.11em] text-success">Why your profile fits</h3><div className="mt-3 grid gap-2 sm:grid-cols-2">{(application.job.aiMatch?.reasons.length ? application.job.aiMatch.reasons : application.job.skills.slice(0, 4).map((skill) => `${skill} aligns with this role.`)).slice(0, 4).map((reason) => <div key={reason} className="flex gap-2 text-xs leading-5 text-[#c8d0da]"><Check className="mt-1 h-3.5 w-3.5 shrink-0 text-success" /><span>{reason}</span></div>)}</div></article>
                    </div>
                  ) : null}

                  {analysisTab === "evidence" ? (
                    <div className="mt-4 overflow-hidden rounded-xl border border-white/[0.07] bg-black/15">
                      {applicationGuide.evidenceMatrix?.length ? <div className="divide-y divide-white/[0.07]">{applicationGuide.evidenceMatrix.map((item) => { const meta = evidenceStatusMeta(item.status); return <article key={`${item.requirement}-${item.status}`} className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(150px,0.7fr)_minmax(0,1.3fr)_auto] md:items-start"><div><p className="text-xs font-bold text-white">{item.requirement}</p><p className="mt-1 text-[8px] font-black uppercase tracking-wider text-muted">{item.importance}</p></div><div><p className="text-[11px] leading-5 text-[#c7cfda]">{item.evidence || "No verified evidence found in the profile."}</p>{item.action ? <p className="mt-1 text-[10px] leading-4 text-muted"><span className="font-bold text-[#dfe4ec]">Next:</span> {item.action}</p> : null}</div><span className={cn("w-fit rounded-full border px-2 py-1 text-[8px] font-black uppercase tracking-wide", meta.className)}>{meta.label}</span></article>; })}</div> : <p className="p-6 text-center text-xs text-muted">No evidence map is available for this vacancy.</p>}
                    </div>
                  ) : null}

                  {analysisTab === "strategy" ? (
                    <div className="mt-4 space-y-3">
                      <div className="grid gap-3 lg:grid-cols-2">
                        <article className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><div className="flex items-center gap-2"><FileText className="h-4 w-4 text-accent" /><h3 className="text-sm font-bold text-white">CV direction</h3></div><p className="mt-3 text-xs leading-5 text-[#d0d6df]">{applicationGuide.resumePlan?.summaryFocus || applicationGuide.cvImprovements?.[0]}</p>{applicationGuide.resumePlan?.targetHeadline ? <p className="mt-3 rounded-lg bg-white/[0.035] px-3 py-2 text-[10px] leading-4 text-muted"><span className="font-bold text-white">Headline:</span> {applicationGuide.resumePlan.targetHeadline}</p> : null}<ul className="mt-3 space-y-2 text-[11px] leading-4 text-muted">{[...(applicationGuide.resumePlan?.evidenceToLead ?? []), ...(applicationGuide.resumePlan?.bulletStrategy ?? []), ...(applicationGuide.cvImprovements ?? [])].slice(0, 6).map((item) => <li key={item} className="flex gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />{item}</li>)}</ul></article>
                        <article className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><div className="flex items-center gap-2"><Mail className="h-4 w-4 text-accent" /><h3 className="text-sm font-bold text-white">Cover letter direction</h3></div><p className="mt-3 text-xs leading-5 text-[#d0d6df]">{applicationGuide.coverLetterPlan?.openingAngle || applicationGuide.coverLetterStrategy?.[0]}</p>{applicationGuide.coverLetterPlan?.motivationAngle ? <p className="mt-3 rounded-lg bg-white/[0.035] px-3 py-2 text-[10px] leading-4 text-muted"><span className="font-bold text-white">Motivation:</span> {applicationGuide.coverLetterPlan.motivationAngle}</p> : null}<ul className="mt-3 space-y-2 text-[11px] leading-4 text-muted">{[...(applicationGuide.coverLetterPlan?.proofPoints ?? []), ...(applicationGuide.coverLetterStrategy ?? [])].slice(0, 5).map((item) => <li key={item} className="flex gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />{item}</li>)}</ul></article>
                      </div>
                      {(applicationGuide.risks ?? []).length ? <div className="rounded-xl border border-red-400/20 bg-red-500/[0.045] p-4"><h3 className="flex items-center gap-2 text-xs font-bold text-red-100"><AlertTriangle className="h-4 w-4" /> Claims to avoid</h3><ul className="mt-2 grid gap-1 text-[10px] leading-4 text-red-100/75 sm:grid-cols-2">{applicationGuide.risks.map((risk) => <li key={risk}>• {risk}</li>)}</ul></div> : null}
                    </div>
                  ) : null}
                </div>
              ) : isAnalysisOutdated ? (
                <div className="m-5 rounded-xl border border-amber-400/25 bg-amber-400/[0.055] px-5 py-8 text-center sm:px-8">
                  <AlertTriangle className="mx-auto h-6 w-6 text-amber-200" />
                  <p className="mt-3 text-sm font-bold text-amber-100">Analysis outdated</p>
                  <p className="mx-auto mt-2 max-w-2xl text-xs leading-5 text-amber-100/70">{isLegacyAnalysis ? "This application uses a legacy ai-match-v1 percentage without an application guide." : "This application does not have a complete application guide v3."} Refresh this application before generating a CV or cover letter.</p>
                  <Button type="button" disabled={isAnalysisRefreshing} onClick={() => onRefreshAnalysis(activeApplication.id)} className="mt-5 h-10 rounded-xl bg-amber-300 px-4 text-xs font-bold text-[#241804] hover:bg-amber-200 disabled:opacity-55">{isAnalysisRefreshing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}{isAnalysisRefreshing ? "Updating analysis…" : "Update this application"}</Button>
                </div>
              ) : <div className="m-5 rounded-xl border border-white/[0.07] bg-black/15 py-12 text-center"><Sparkles className="mx-auto h-5 w-5 text-muted" /><p className="mt-2 text-xs text-muted">Run AI Match for this vacancy to create the application plan.</p></div>}
            </section>

            <section className={cn("workspace-card overflow-hidden", !confirmationsReady && "border-amber-300/20")}>
              <div className="flex items-start gap-3 border-b border-white/[0.07] px-5 py-5 sm:px-6">
                <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-xl", !confirmationsReady ? "bg-amber-400/10 text-amber-200" : "bg-success/10 text-success")}><MessageSquareText className="h-[18px] w-[18px]" /></span>
                <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="text-[10px] font-black uppercase tracking-[0.14em] text-accent">02 · Confirm your evidence</p>{!hasCurrentAnalysis ? <span className="rounded-full border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 text-[9px] font-black text-amber-200">Analysis required</span> : hasOversizedConfirmation ? <span className="rounded-full border border-red-400/25 bg-red-500/10 px-2 py-0.5 text-[9px] font-black text-red-200">Shorten long answer</span> : unansweredBlockingQuestions.length ? <span className="rounded-full border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 text-[9px] font-black text-amber-200">{unansweredBlockingQuestions.length} required</span> : <span className="rounded-full border border-success/25 bg-success/10 px-2 py-0.5 text-[9px] font-black text-success">Complete</span>}<span className={cn("rounded-full border px-2 py-0.5 text-[9px] font-black", confirmationSyncStatus === "saved" ? "border-success/20 bg-success/[0.06] text-success" : confirmationSyncStatus === "error" ? "border-red-400/25 bg-red-500/10 text-red-200" : "border-white/10 bg-white/[0.035] text-muted")}>{confirmationSyncStatus === "loading" ? "Loading answers" : confirmationSyncStatus === "saving" ? "Saving…" : confirmationSyncStatus === "saved" ? "Saved" : confirmationSyncStatus === "error" ? "Save failed" : "Not saved"}</span></div><h2 className="mt-1 text-lg font-bold text-white">Keep every claim accurate</h2><p className="mt-1 text-xs leading-5 text-muted">Choose yes, no, or partial and support positive answers with a concrete example.</p></div>
              </div>
              <div className="p-5 sm:p-6">
                {confirmationSyncMessage ? <div className={cn("mb-4 rounded-xl border px-3 py-2.5 text-[10px] leading-4", confirmationSyncStatus === "error" ? "border-red-400/25 bg-red-500/[0.07] text-red-200" : "border-amber-400/20 bg-amber-400/[0.05] text-amber-100/80")}>{confirmationSyncMessage}</div> : null}
                {!hasCurrentAnalysis ? <div className="flex items-center gap-3 rounded-xl border border-amber-400/20 bg-amber-400/[0.045] px-4 py-3 text-xs text-amber-100/80"><AlertTriangle className="h-5 w-5 shrink-0 text-amber-200" /><span>Update the analysis before confirming evidence. The legacy percentage does not contain the questions required for safe document generation.</span></div> : clarificationQuestions.length ? <div className="grid gap-3">{clarificationQuestions.map((question, index) => {
                  const confirmation = candidateConfirmations[question.id];
                  const answerLength = confirmation?.exampleText.trim().length ?? 0;
                  const isAnswered = Boolean(confirmation && (!question.blocking || isMeaningfulCandidateConfirmation(confirmation)));
                  const isOversized = answerLength > confirmationAnswerMaxChars;
                  const requiresExample = confirmation?.response === "yes" || confirmation?.response === "partial";
                  return <article key={question.id} className={cn("block rounded-xl border p-4 transition", isOversized ? "border-red-400/30 bg-red-500/[0.035]" : isAnswered ? "border-success/15 bg-success/[0.025]" : "border-white/[0.08] bg-black/15 focus-within:border-amber-400/35")}><span className="flex items-start gap-3"><span className={cn("grid h-6 w-6 shrink-0 place-items-center rounded-full border text-[10px] font-black", isAnswered && !isOversized ? "border-success/25 bg-success/10 text-success" : "border-white/10 text-muted")}>{isAnswered && !isOversized ? <Check className="h-3.5 w-3.5" /> : index + 1}</span><span className="min-w-0"><span className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold leading-5 text-white">{question.question}</span>{question.blocking ? <span className="rounded-full bg-amber-400/10 px-2 py-0.5 text-[8px] font-black uppercase text-amber-200">Required</span> : null}</span><span className="mt-1 block text-[10px] leading-4 text-[#9da8b7]"><span className="font-bold text-[#d5dbe4]">Requirement:</span> {question.requirement}</span>{question.why ? <span className="mt-1 block text-[10px] leading-4 text-muted">Why it matters: {question.why}</span> : null}</span></span><div className="mt-3 grid grid-cols-3 gap-2">{(["yes", "no", "partial"] as CandidateConfirmationResponse[]).map((response) => <button key={response} type="button" onClick={() => updateCandidateConfirmation(question, { response })} className={cn("h-9 rounded-lg border text-[10px] font-black uppercase tracking-wide transition", confirmation?.response === response ? response === "no" ? "border-red-400/35 bg-red-500/10 text-red-100" : response === "partial" ? "border-amber-400/35 bg-amber-400/10 text-amber-100" : "border-success/35 bg-success/10 text-success" : "border-white/[0.08] bg-white/[0.025] text-muted hover:bg-white/[0.06] hover:text-white")}>{response}</button>)}</div><textarea value={confirmation?.exampleText ?? ""} disabled={!confirmation} maxLength={confirmationAnswerMaxChars} onChange={(event) => updateCandidateConfirmation(question, { exampleText: event.target.value })} rows={2} placeholder={!confirmation ? "Choose yes, no, or partial first" : requiresExample ? "Add a true, concrete example" : "Optional context for this answer"} className="mt-3 w-full resize-y rounded-xl border border-white/[0.08] bg-[#0b1118] px-3 py-2.5 text-xs leading-5 text-white outline-none placeholder:text-muted/55 focus:border-amber-400/40 disabled:cursor-not-allowed disabled:opacity-45" /><span className="mt-1.5 flex items-center justify-between gap-3"><span className={cn("text-[9px]", question.blocking && requiresExample && !isMeaningfulCandidateConfirmation(confirmation) ? "font-bold text-amber-200" : "text-muted")}>{question.blocking && requiresExample && !isMeaningfulCandidateConfirmation(confirmation) ? "Add a specific example (at least two meaningful words)." : confirmationsDirty ? "Pending backend save" : confirmation?.updatedAt ? `Updated ${new Date(confirmation.updatedAt).toLocaleString()}` : "Changes save automatically"}</span><span className={cn("text-[9px]", isOversized ? "font-bold text-red-200" : "text-muted")}>{answerLength.toLocaleString()} / {confirmationAnswerMaxChars.toLocaleString()}</span></span></article>;
                })}</div> : <div className="flex items-center gap-3 rounded-xl border border-success/15 bg-success/[0.035] px-4 py-3 text-xs text-[#dfe5ec]"><CheckCircle2 className="h-5 w-5 shrink-0 text-success" /><span>No additional confirmations are required. Your verified profile is enough to continue.</span></div>}
              </div>
            </section>

            <section className="workspace-card overflow-hidden">
              <div className="flex flex-col gap-4 border-b border-white/[0.07] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div className="flex items-start gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent/12 text-accent"><Sparkles className="h-[18px] w-[18px]" /></span><div><p className="text-[10px] font-black uppercase tracking-[0.14em] text-accent">03 · Build your application pack</p><h2 className="mt-1 text-lg font-bold text-white">Tailored documents</h2><p className="mt-1 text-xs leading-5 text-muted">Select your originals. Tasko rewrites the content and preserves the DOCX design.</p></div></div>
                <Button onClick={generatePack} disabled={isGeneratingPack || Boolean(generationType) || !documentsLoaded || !selectedResumeSourceId || !selectedCoverSourceId || !applicationReview || unansweredBlockingQuestions.length > 0 || hasOversizedConfirmation} className="h-11 shrink-0 rounded-xl bg-accent px-4 text-xs font-bold text-white shadow-[0_12px_28px_rgba(255,90,0,0.2)] hover:bg-[#ff6a14] disabled:opacity-40">{isGeneratingPack ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{isGeneratingPack ? "Generating pack…" : "Generate both documents"}</Button>
              </div>
              <div className="p-5 sm:p-6">
                {documentError ? <div className="mb-4 rounded-xl border border-red-400/25 bg-red-500/[0.07] px-3 py-2.5 text-xs leading-5 text-red-200">{documentError}</div> : null}
                {effectiveLanguage && !resumeSources.some((source) => source.language === effectiveLanguage) ? <div className="mb-4 rounded-xl border border-amber-400/25 bg-amber-400/[0.07] px-3 py-2.5 text-xs leading-5 text-amber-200">No {effectiveLanguage} CV DOCX is saved in Profile. Add one or choose another language.</div> : null}
                <div className="grid gap-4 lg:grid-cols-2">
                  <DocumentCard icon={FileText} label="Tailored CV" description="Focused for this role, with your structure and visual style intact." document={latestResume} isOutdated={isResumeOutdated} isGenerating={generationType === "tailored_resume"} restoringVersionKey={restoringVersionKey} onGenerate={() => generateDocument("tailored_resume")} onRestore={(version) => latestResume && restoreDocumentVersion(latestResume, version)} canGenerate={Boolean(documentsLoaded && selectedResumeSourceId && applicationReview && confirmationsReady)} disabledLabel={!documentsLoaded ? "Loading history…" : !selectedResumeSourceId ? "Select source first" : !applicationReview ? analysisRequiredLabel : hasOversizedConfirmation ? "Shorten confirmation" : "Complete required answers"} sourceControl={<SourcePicker label="Source CV" sources={resumeSources} selectedId={selectedResumeSourceId} onChange={(sourceId) => { setSelectedResumeSourceId(sourceId); setIsResumeSourceManual(Boolean(sourceId)); }} onAttach={(file) => void attachWorkspaceSource(file, "CV / Resume")} />} />
                  <DocumentCard icon={Mail} label="Cover letter" description="A concise role-specific letter based only on verified evidence." document={latestCoverLetter} isOutdated={isCoverLetterOutdated} isGenerating={generationType === "cover_letter"} restoringVersionKey={restoringVersionKey} onGenerate={() => generateDocument("cover_letter")} onRestore={(version) => latestCoverLetter && restoreDocumentVersion(latestCoverLetter, version)} canGenerate={Boolean(documentsLoaded && selectedCoverSourceId && applicationReview && confirmationsReady)} disabledLabel={!documentsLoaded ? "Loading history…" : !selectedCoverSourceId ? "Select source first" : !applicationReview ? analysisRequiredLabel : hasOversizedConfirmation ? "Shorten confirmation" : "Complete required answers"} sourceControl={<SourcePicker label="Source cover letter" sources={coverSources} selectedId={selectedCoverSourceId} onChange={(sourceId) => { setSelectedCoverSourceId(sourceId); setIsCoverSourceManual(Boolean(sourceId)); }} onAttach={(file) => void attachWorkspaceSource(file, "Cover Letter")} />} />
                </div>
              </div>
            </section>

            <section className="relative overflow-hidden rounded-2xl border border-[#7c5cff]/20 bg-gradient-to-br from-[#17142a] via-[#111722] to-[#111821] p-5 sm:p-6">
              <div className="absolute -right-12 -top-14 h-44 w-44 rounded-full bg-[#7c5cff]/12 blur-3xl" /><div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[#9f7aea]/25 bg-[#9f7aea]/12 text-[#c4a7ff]"><Rocket className="h-5 w-5" /></span><div><div className="flex flex-wrap items-center gap-2"><h2 className="text-sm font-bold text-white">Auto Apply</h2><span className="rounded-full border border-[#9f7aea]/25 bg-[#9f7aea]/10 px-2 py-0.5 text-[8px] font-black uppercase tracking-wider text-[#c4a7ff]">Coming soon</span></div><p className="mt-1 max-w-2xl text-xs leading-5 text-muted">Tasko will fill the employer form with your approved answers and pause before submission.</p><p className="mt-2 inline-flex items-center gap-1.5 text-[10px] font-bold text-[#b8c0cc]"><ShieldCheck className="h-3.5 w-3.5 text-success" /> You remain in control of the final submission.</p></div></div><Button disabled className="h-10 shrink-0 rounded-xl border border-[#9f7aea]/25 bg-[#9f7aea]/10 px-4 text-xs font-bold text-[#c4a7ff] opacity-70"><LockKeyhole className="h-4 w-4" /> Auto Apply</Button></div>
            </section>
          </main>

          <aside className="space-y-4 xl:sticky xl:top-4">
            <section className="workspace-card overflow-hidden">
              <div className="border-b border-white/[0.07] p-5"><div className="flex items-end justify-between"><div><p className="text-[10px] font-black uppercase tracking-[0.13em] text-accent">Readiness</p><h2 className="mt-1 text-base font-bold text-white">Before you apply</h2></div><span className="text-2xl font-black text-white">{progress}<span className="text-sm text-muted">%</span></span></div><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/[0.07]"><div className="h-full rounded-full bg-gradient-to-r from-accent to-[#ff9b55] transition-all" style={{ width: `${progress}%` }} /></div></div>
              <div className="p-4"><div className="space-y-1">{checklist.map((item) => <div key={item.label} className="flex items-center gap-2.5 rounded-lg px-2 py-2"><span className={cn("grid h-5 w-5 place-items-center rounded-full border", item.ready ? "border-success/25 bg-success/10 text-success" : "border-white/10 text-[#687383]")}>{item.ready ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}</span><span className={cn("text-[11px] font-semibold", item.ready ? "text-[#e0e5ec]" : "text-muted")}>{item.label}</span><span className="ml-auto text-[8px] font-black uppercase tracking-wide text-[#687383]">{item.ready ? "Ready" : "Missing"}</span></div>)}</div>
                {application.status === "draft" ? <Button onClick={() => onMarkApplied(application.id)} className="mt-4 h-11 w-full rounded-xl bg-success text-xs font-black text-[#071006] hover:bg-[#6de046]"><Check className="h-4 w-4" /> Mark as applied</Button> : <div className="mt-4 flex h-11 items-center justify-center gap-2 rounded-xl border border-success/25 bg-success/10 text-xs font-bold text-success"><Check className="h-4 w-4" /> Application tracked</div>}
              </div>
            </section>

            <section className="workspace-card overflow-hidden">
              <div className="flex items-center gap-3 border-b border-white/[0.07] p-4"><span className="grid h-9 w-9 place-items-center rounded-xl bg-accent/12 text-accent"><Bot className="h-4 w-4" /></span><div><h2 className="text-sm font-bold text-white">Application coach</h2><p className="mt-0.5 text-[10px] text-muted">Ask about this vacancy</p></div></div>
              <div className="p-4"><div className="grid gap-2">{["What should I emphasize?", "What are the biggest risks?", "Help with application questions"].map((prompt) => <button key={prompt} type="button" disabled={isLoadingAdvice} onClick={() => requestAdvice(prompt)} className={cn("rounded-xl border px-3 py-2.5 text-left text-[11px] font-semibold leading-4 transition", advicePrompt === prompt ? "border-accent/35 bg-accent/10 text-white" : "border-white/[0.07] bg-white/[0.02] text-[#cbd3df] hover:border-accent/25 hover:bg-accent/[0.05]")}>{prompt}</button>)}</div>
                {(isLoadingAdvice || advice) ? <div className="job-scroll mt-3 max-h-[300px] overflow-y-auto rounded-xl border border-white/[0.07] bg-black/20 p-3">{isLoadingAdvice ? <div className="flex items-center gap-2 text-xs text-muted"><LoaderCircle className="h-4 w-4 animate-spin text-accent" /> Reviewing…</div> : <p className="whitespace-pre-wrap text-[11px] leading-5 text-[#dfe4ec]">{advice}</p>}</div> : null}
                <Button variant="ghost" onClick={() => onOpenAssistant("Review this application and help me finish it.", application.id)} className="mt-3 h-9 w-full rounded-xl border border-white/[0.07] bg-transparent text-[11px] text-[#e6ebf3] hover:bg-white/[0.05]">Open full Assistant <ChevronRight className="h-4 w-4" /></Button>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </section>
  );
}

function DocumentCard({
  icon: Icon,
  label,
  description,
  document,
  isOutdated,
  isGenerating,
  restoringVersionKey,
  onGenerate,
  onRestore,
  canGenerate,
  disabledLabel,
  sourceControl,
}: {
  icon: typeof FileText;
  label: string;
  description: string;
  document: GeneratedDocument | undefined;
  isOutdated: boolean;
  isGenerating: boolean;
  restoringVersionKey: string;
  onGenerate: () => void;
  onRestore: (version: number) => void;
  canGenerate: boolean;
  disabledLabel: string;
  sourceControl?: React.ReactNode;
}) {
  const content = currentContent(document);
  const currentVersion = document?.versions.find((version) => version.version === document.currentVersion);
  const isValidated = currentVersion?.factualValidation.status === "passed"
    && currentVersion.visualValidation.status === "passed";
  const isRestoringDocument = Boolean(document && restoringVersionKey.startsWith(`${document.id}:`));
  return (
    <article className="flex flex-col rounded-2xl border border-white/[0.08] bg-black/15 p-4 transition hover:border-white/[0.12]">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.035] text-accent"><Icon className="h-[18px] w-[18px]" /></span>
        <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold text-white">{label}</h3>{document ? isOutdated ? <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-[8px] font-black uppercase tracking-wide text-amber-200"><AlertTriangle className="h-3 w-3" /> Outdated · v{document.currentVersion}</span> : <span className="inline-flex items-center gap-1 rounded-full border border-success/25 bg-success/10 px-2 py-1 text-[8px] font-black uppercase tracking-wide text-success"><FileCheck2 className="h-3 w-3" /> Ready · v{document.currentVersion}</span> : <span className="rounded-full border border-white/[0.08] bg-white/[0.025] px-2 py-1 text-[8px] font-black uppercase tracking-wide text-muted">Not generated</span>}</div><p className="mt-1 text-[10px] leading-4 text-muted">{description}</p></div>
      </div>
      {sourceControl}
      <div className={cn("mt-3 min-h-[132px] overflow-hidden rounded-xl border p-4", content ? "border-white/[0.09] bg-[#f6f4ef] text-[#20242a] shadow-inner" : "border-dashed border-white/[0.1] bg-white/[0.015]")}>
        {isGenerating ? <div className="grid min-h-[100px] place-items-center text-center"><div><LoaderCircle className="mx-auto h-5 w-5 animate-spin text-accent" /><p className="mt-2 text-[11px] font-semibold text-muted">Writing an evidence-based version…</p></div></div> : content ? <p className="line-clamp-[7] whitespace-pre-wrap font-serif text-[9px] leading-[1.55]">{content}</p> : <div className="grid min-h-[100px] place-items-center text-center"><div><Icon className="mx-auto h-5 w-5 text-[#606b79]" /><p className="mt-2 text-[10px] font-semibold text-[#7f8998]">Preview will appear after generation</p></div></div>}
      </div>
      {isValidated ? (
        <details open className="mt-3 rounded-xl border border-white/[0.08] bg-white/[0.02]">
          <summary className="cursor-pointer px-3 py-2.5 text-[10px] font-bold text-white marker:text-muted">Review before download · {currentVersion.diff.length} change{currentVersion.diff.length === 1 ? "" : "s"}</summary>
          <div className="job-scroll max-h-72 space-y-2 overflow-y-auto border-t border-white/[0.07] p-3">
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full border border-success/25 bg-success/10 px-2 py-1 text-[8px] font-black uppercase tracking-wide text-success">Facts validated</span>
              <span className="rounded-full border border-success/25 bg-success/10 px-2 py-1 text-[8px] font-black uppercase tracking-wide text-success">Rendered · {currentVersion.visualValidation.sourcePageCount ?? "?"} → {currentVersion.visualValidation.renderedPageCount ?? "?"} page{currentVersion.visualValidation.renderedPageCount === 1 ? "" : "s"}</span>
              {!currentVersion.visualValidation.tableOverflow ? <span className="rounded-full border border-success/25 bg-success/10 px-2 py-1 text-[8px] font-black uppercase tracking-wide text-success">Tables fit</span> : null}
              {currentVersion.visualValidation.linksPreserved ? <span className="rounded-full border border-success/25 bg-success/10 px-2 py-1 text-[8px] font-black uppercase tracking-wide text-success">Links preserved</span> : null}
            </div>
            {currentVersion.diff.length ? currentVersion.diff.map((change) => <article key={`${change.blockId}-${change.original}`} className="rounded-lg border border-white/[0.07] bg-black/20 p-2.5"><div className="flex items-center justify-between gap-2"><p className="text-[9px] font-black uppercase tracking-wide text-[#9aa5b4]">{change.blockId} · {change.type}</p><p className="text-[8px] text-muted">{change.reason}</p></div><p className="mt-2 whitespace-pre-wrap text-[10px] leading-4 text-red-200/75 line-through">{change.original || "Added paragraph"}</p><p className="mt-1 whitespace-pre-wrap text-[10px] leading-4 text-emerald-200">{change.replacement || "Removed paragraph"}</p></article>) : <p className="rounded-lg border border-success/15 bg-success/[0.04] px-3 py-2 text-[9px] font-bold text-success">No factual content changes</p>}
          </div>
        </details>
      ) : null}
      <div className="mt-3 flex gap-2">
        <Button type="button" disabled={isGenerating || isRestoringDocument || !canGenerate} onClick={onGenerate} className="h-10 flex-1 rounded-xl bg-accent px-3 text-[11px] font-bold text-white hover:bg-[#ff6a14] disabled:opacity-40">{isGenerating ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : document ? <RefreshCw className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}{isGenerating ? "Generating…" : !canGenerate ? disabledLabel : document ? "Regenerate" : `Generate ${label}`}</Button>
        {document ? <a href={`${apiBaseUrl}/documents/${encodeURIComponent(document.id)}/download`} download={documentFileName(document)} className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-white/[0.09] px-3 text-[11px] font-bold text-[#e6ebf3] transition hover:bg-white/[0.05]"><Download className="h-3.5 w-3.5" /> DOCX</a> : null}
      </div>
      {document ? (
        <details className="mt-3 rounded-xl border border-white/[0.07] bg-white/[0.018]">
          <summary className="cursor-pointer px-3 py-2.5 text-[10px] font-bold text-[#cbd3df] marker:text-muted">
            Version history · {document.versions.length}
          </summary>
          <div className="border-t border-white/[0.07] px-3 py-2">
            {[...document.versions].sort((left, right) => right.version - left.version).map((version) => {
              const isCurrent = version.version === document.currentVersion;
              const restoreKey = `${document.id}:${version.version}`;
              const isRestoring = restoringVersionKey === restoreKey;
              return (
                <div key={version.id} className="flex items-center gap-2 border-b border-white/[0.05] py-2 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] font-bold text-white">v{version.version}{isCurrent ? <span className="ml-1.5 text-[8px] uppercase tracking-wide text-success">Current</span> : null}</p>
                    <p className="mt-0.5 text-[9px] text-muted">{formatVersionTimestamp(version.createdAt)}</p>
                  </div>
                  <a href={`${apiBaseUrl}/documents/${encodeURIComponent(document.id)}/download?version=${version.version}`} download={documentFileName(document, version.version)} className="inline-flex h-7 items-center gap-1 rounded-md border border-white/[0.08] px-2 text-[9px] font-bold text-[#dbe2eb] hover:bg-white/[0.05]"><Download className="h-3 w-3" /> DOCX</a>
                  {!isCurrent ? <button type="button" disabled={Boolean(restoringVersionKey) || isGenerating} onClick={() => onRestore(version.version)} className="inline-flex h-7 items-center gap-1 rounded-md border border-white/[0.08] px-2 text-[9px] font-bold text-[#dbe2eb] transition hover:border-accent/30 hover:text-white disabled:opacity-40">{isRestoring ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />} Restore</button> : null}
                </div>
              );
            })}
          </div>
        </details>
      ) : null}
    </article>
  );
}

function SourcePicker({
  label,
  sources,
  selectedId,
  onChange,
  onAttach,
}: {
  label: string;
  sources: ProfileSourceDocument[];
  selectedId: string;
  onChange: (sourceId: string) => void;
  onAttach: (file: File | undefined) => void;
}) {
  return (
    <div className="mt-4 rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[9px] font-black uppercase tracking-[0.1em] text-muted">{label}</p>
        <label className="inline-flex cursor-pointer items-center gap-1 text-[9px] font-bold text-accent hover:text-white">
          <Upload className="h-3.5 w-3.5" /> Upload DOCX
          <input
            type="file"
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(event) => {
              onAttach(event.target.files?.[0]);
              event.currentTarget.value = "";
            }}
          />
        </label>
      </div>
      <select value={selectedId} onChange={(event) => onChange(event.target.value)} className="mt-2 h-9 w-full rounded-lg border border-white/[0.08] bg-[#111821] px-2.5 text-[10px] font-semibold text-white outline-none focus:border-accent/60">
        <option value="">Select DOCX source</option>
        {sources.map((source) => <option key={source.id} value={source.id}>{source.language ? `${source.language} · ` : ""}{source.title} · {source.file_name}</option>)}
      </select>
      <p className="mt-2 text-[9px] leading-4 text-muted">{sources.length ? "Layout, styles, images, header and footer stay intact." : "No DOCX found. Upload one here or add it to Profile."}</p>
    </div>
  );
}
