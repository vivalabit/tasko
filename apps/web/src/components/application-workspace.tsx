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
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const docxContentType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function currentContent(document: GeneratedDocument | undefined) {
  if (!document) return "";
  return document.versions.find((version) => version.version === document.currentVersion)?.content ?? "";
}

function documentFileName(document: GeneratedDocument) {
  const base = document.title.trim().replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^[._-]+|[._-]+$/g, "") || "tasko-document";
  return `${base}-v${document.currentVersion}.docx`;
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
}: ApplicationWorkspaceProps) {
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [selectedResumeSourceId, setSelectedResumeSourceId] = useState("");
  const [selectedCoverSourceId, setSelectedCoverSourceId] = useState("");
  const [languageMode, setLanguageMode] = useState<"auto" | "English" | "German">("auto");
  const [isResumeSourceManual, setIsResumeSourceManual] = useState(false);
  const [isCoverSourceManual, setIsCoverSourceManual] = useState(false);
  const [temporarySources, setTemporarySources] = useState<ProfileSourceDocument[]>([]);
  const [generationType, setGenerationType] = useState<GeneratedDocument["type"] | "">("");
  const [isGeneratingPack, setIsGeneratingPack] = useState(false);
  const [documentError, setDocumentError] = useState("");
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>({});
  const [advice, setAdvice] = useState("");
  const [advicePrompt, setAdvicePrompt] = useState("");
  const [isLoadingAdvice, setIsLoadingAdvice] = useState(false);

  useEffect(() => {
    if (!application) return;
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
  const applicationReview = useMemo(
    () => application ? buildSavedApplicationReview(application.job) : "",
    [application],
  );
  const applicationGuide = application?.job.aiMatch?.applicationGuide;
  const clarificationQuestions = applicationGuide?.clarificationQuestions ?? [];
  const unansweredBlockingQuestions = clarificationQuestions.filter(
    (question) => question.blocking && !clarificationAnswers[question.id]?.trim(),
  );
  const vacancyLanguage = application?.job.aiMatch?.applicationGuide?.language || (application ? detectLegacyJobLanguage(application.job) : "");
  const effectiveLanguage = languageMode === "auto" ? vacancyLanguage : languageMode;

  useEffect(() => {
    setLanguageMode("auto");
    setIsResumeSourceManual(false);
    setIsCoverSourceManual(false);
    setSelectedResumeSourceId("");
    setSelectedCoverSourceId("");
    if (!application) {
      setClarificationAnswers({});
      return;
    }
    try {
      const stored = window.localStorage.getItem(`tasko.application-confirmations.${application.id}`);
      const parsed = stored ? JSON.parse(stored) as unknown : null;
      setClarificationAnswers(parsed && typeof parsed === "object" ? parsed as Record<string, string> : {});
    } catch {
      setClarificationAnswers({});
    }
  }, [application?.id]);

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

  if (!application) {
    return (
      <section className="grid min-w-0 flex-1 place-items-center p-6">
        <div className="panel max-w-md p-6 text-center">
          <FileText className="mx-auto h-8 w-8 text-muted" />
          <h1 className="mt-3 text-lg font-bold text-white">No application selected</h1>
          <Button className="mt-4 bg-accent text-white" onClick={onBack}><ArrowLeft className="h-4 w-4" /> Back to jobs</Button>
        </div>
      </section>
    );
  }

  const activeApplication = application;
  const jobUrl = activeApplication.job.applyUrl || activeApplication.job.sourceUrl || "";
  const profileReady = Boolean(profile.name && (profile.experience || profile.resume_file_name));
  const checklist = [
    { label: "Candidate profile", ready: profileReady },
    { label: "Vacancy analysis", ready: Boolean(applicationGuide) },
    { label: "Required confirmations", ready: unansweredBlockingQuestions.length === 0 },
    { label: "Tailored CV", ready: Boolean(latestResume) },
    { label: "Cover letter", ready: Boolean(latestCoverLetter) },
    { label: "Application link", ready: Boolean(jobUrl) },
  ];
  const readyCount = checklist.filter((item) => item.ready).length;
  const progress = Math.round((readyCount / checklist.length) * 100);

  function updateClarificationAnswer(questionId: string, value: string) {
    const nextAnswers = { ...clarificationAnswers, [questionId]: value };
    setClarificationAnswers(nextAnswers);
    window.localStorage.setItem(
      `tasko.application-confirmations.${activeApplication.id}`,
      JSON.stringify(nextAnswers),
    );
  }

  async function askAssistant(message: string, sources: ProfileSourceDocument[] = []) {
    if (!message.trim()) return "";
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
      }),
    });
    if (!response.ok) throw new Error(await readApiError(response, "AI request failed"));
    const payload = await response.json() as { message?: string };
    return payload.message?.trim() ?? "";
  }

  async function generateDocument(type: GeneratedDocument["type"]) {
    setGenerationType(type);
    setDocumentError("");
    try {
      const isCoverLetter = type === "cover_letter";
      const selectedSourceId = isCoverLetter ? selectedCoverSourceId : selectedResumeSourceId;
      const selectedSource = profileSources.find((source) => source.id === selectedSourceId);
      if (!selectedSource || !selectedSource.file_name.toLowerCase().endsWith(".docx")) {
        throw new Error(`Select a DOCX ${isCoverLetter ? "cover letter" : "CV"} before generating`);
      }
      if (!applicationReview) {
        throw new Error("Wait for the pre-application improvement plan before generating documents");
      }
      if (unansweredBlockingQuestions.length > 0) {
        throw new Error("Answer the required confirmation questions before generating documents");
      }
      const improvementPlan = JSON.stringify(
        {
          analysis: applicationGuide,
          candidateConfirmations: clarificationQuestions.map((question) => ({
            requirement: question.requirement,
            question: question.question,
            answer: clarificationAnswers[question.id]?.trim() || "Not answered — do not use the proposed claim",
          })),
        },
        null,
        2,
      ).slice(0, 12_000);
      const targetLanguage = effectiveLanguage || selectedSource.language || "English";
      const prompt = isCoverLetter
        ? `Rewrite the selected DOCX cover letter in ${targetLanguage} for this vacancy using only verified evidence from my profile, the source document, and explicit candidate confirmations below. Follow the saved vacancy analysis as mandatory guidance, especially its positioning, evidence matrix, risks, and unsupported claims. An unanswered question is not evidence. A negative answer means the skill must be omitted. Preserve truthful facts. Return only the complete letter text without Markdown or commentary, keeping a greeting, focused body paragraphs, and professional closing. Do not invent achievements or metrics.\n\nSAVED ANALYSIS AND CANDIDATE CONFIRMATIONS:\n${improvementPlan}`
        : `Tailor the selected DOCX resume in ${targetLanguage} to this vacancy while keeping its layout unchanged. Use only verified profile/source evidence and explicit candidate confirmations below. Follow the saved vacancy analysis as mandatory guidance: apply its resume plan and evidence emphasis, and avoid every unsupported claim. An unanswered question is not evidence. A negative answer means the skill must be omitted. Return exactly one plain-text line for every non-empty body text block in the source DOCX, in the identical order and with the identical number of lines. Repeat contact details, section headings, dates, employers, education, and any line that should not change verbatim. Rewrite only existing summary, skill, and achievement lines where truthful evidence supports it. Do not add, remove, merge, split, or reorder lines. Do not use Markdown markers or commentary. Do not invent facts or metrics.\n\nSAVED ANALYSIS AND CANDIDATE CONFIRMATIONS:\n${improvementPlan}`;
      const content = await askAssistant(prompt, [selectedSource]);
      if (!content) throw new Error("AI returned an empty document");

      const templateId = await ensureSourceTemplate(selectedSource, type);

      const title = `${isCoverLetter ? "Cover letter" : "Tailored CV"} · ${activeApplication.job.title} · ${activeApplication.job.company}`;
      const response = await fetch(`${apiBaseUrl}/documents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          title,
          content,
          jobId: activeApplication.job.id,
          applicationId: activeApplication.id,
          templateId,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Document save failed"));
      const saved = await response.json() as GeneratedDocument;
      setDocuments((current) => [saved, ...current.filter((document) => document.id !== saved.id)]);
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
      setAdvice(await askAssistant(prompt));
    } catch (error) {
      setAdvice(error instanceof Error ? error.message : "Advice request failed");
    } finally {
      setIsLoadingAdvice(false);
    }
  }

  return (
    <section className="job-scroll min-w-0 flex-1 overflow-y-auto px-3 py-3 sm:px-4 2xl:px-5 2xl:py-4">
      <div className="mx-auto max-w-[1280px]">
        <button type="button" onClick={onBack} className="mb-3 inline-flex items-center gap-1.5 text-xs font-bold text-muted transition hover:text-white">
          <ArrowLeft className="h-4 w-4" /> Back to jobs
        </button>

        <header className="panel overflow-hidden">
          <div className="flex flex-col gap-4 p-4 sm:p-5 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-accent/35 bg-accent/10 px-2 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-accent">Application workspace</span>
                <span className="rounded-md border border-[#2f80ed]/35 bg-[#2f80ed]/10 px-2 py-1 text-[10px] font-bold text-[#8cc7ff]">{application.status === "draft" ? "Preparing" : application.status}</span>
              </div>
              <h1 className="mt-3 text-2xl font-bold leading-tight text-white 2xl:text-3xl">{application.job.title}</h1>
              <p className="mt-1.5 text-sm font-semibold text-muted">{application.job.company} <span className="text-white/30">•</span> {application.job.location} <span className="text-white/30">•</span> {application.job.type}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="mr-2 hidden text-right sm:block">
                <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted">AI match</p>
                <p className="mt-0.5 text-xl font-black text-success">{application.job.match}%</p>
              </div>
              <Button variant="ghost" disabled={!jobUrl} onClick={() => jobUrl && window.open(jobUrl, "_blank", "noopener,noreferrer")} className="h-10 rounded-md border border-border bg-white/[0.025] text-xs text-[#e6ebf3] hover:bg-white/[0.06] disabled:opacity-45">
                <ExternalLink className="h-4 w-4" /> View vacancy
              </Button>
              <Button onClick={() => jobUrl && window.open(jobUrl, "_blank", "noopener,noreferrer")} disabled={!jobUrl} className="h-10 rounded-md bg-accent px-4 text-xs font-bold text-white hover:bg-[#ff6a14] disabled:opacity-45">
                Open application website <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="border-t border-border bg-white/[0.018] px-4 py-3 sm:px-5">
            <div className="flex items-center justify-between gap-3 text-[11px] font-bold">
              <span className="text-muted">Application readiness</span>
              <span className="text-white">{readyCount}/{checklist.length} ready · {progress}%</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/[0.08]"><div className="h-full rounded-full bg-gradient-to-r from-accent to-[#ff9f1a] transition-all" style={{ width: `${progress}%` }} /></div>
          </div>
        </header>

        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_350px]">
          <main className="space-y-3">
            <section className="panel overflow-hidden border-accent/25">
              <div className="flex flex-col gap-3 border-b border-border bg-accent/[0.045] p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
                <div className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-accent/14 text-accent"><Bot className="h-5 w-5" /></span>
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-[0.12em] text-accent">Step 1 · Improve before generating</p>
                    <h2 className="mt-1 text-lg font-bold text-white">What to improve in your CV and application</h2>
                    <p className="mt-1 text-xs leading-5 text-muted">This plan comes from the saved AI Match. The document generator follows it without analyzing the vacancy again.</p>
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap items-end gap-2">
                  <label className="grid gap-1">
                    <span className="text-[9px] font-black uppercase tracking-[0.1em] text-muted">Application language</span>
                    <select
                      value={languageMode}
                      onChange={(event) => {
                        setLanguageMode(event.target.value as "auto" | "English" | "German");
                        setIsResumeSourceManual(false);
                        setIsCoverSourceManual(false);
                        setSelectedResumeSourceId("");
                        setSelectedCoverSourceId("");
                      }}
                      className="h-9 rounded-md border border-border bg-[#151c24] px-2.5 text-xs font-bold text-white outline-none focus:border-accent/60"
                    >
                      <option value="auto">Auto detect</option>
                      <option value="English">English</option>
                      <option value="German">German</option>
                    </select>
                  </label>
                  {languageMode === "auto" && vacancyLanguage ? <span className="mb-0.5 rounded-md border border-[#2f80ed]/35 bg-[#2f80ed]/10 px-2 py-1.5 text-[10px] font-bold text-[#8cc7ff]">Detected: {vacancyLanguage}</span> : null}
                </div>
              </div>
              <div className="p-4 sm:p-5">
                {applicationGuide ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(260px,0.75fr)]">
                      <article className="rounded-md border border-accent/25 bg-accent/[0.055] p-4">
                        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.1em] text-accent"><Target className="h-4 w-4" /> Core mission</div>
                        <p className="mt-2 text-sm font-bold leading-6 text-white">{applicationGuide.roleMission || activeApplication.job.overview || `Succeed as ${activeApplication.job.title}.`}</p>
                        <p className="mt-3 border-t border-accent/15 pt-3 text-xs leading-5 text-[#dfe4ec]"><span className="font-bold text-white">Positioning:</span> {applicationGuide.positioning}</p>
                      </article>
                      <article className="rounded-md border border-border bg-[#0c1219] p-4">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-[10px] font-black uppercase tracking-[0.1em] text-muted">Analysis readiness</p>
                          <span className={cn("rounded border px-2 py-1 text-[9px] font-black uppercase", applicationGuide.readiness === "ready" ? "border-success/35 bg-success/10 text-success" : applicationGuide.readiness === "weak_fit" ? "border-red-400/35 bg-red-500/10 text-red-200" : "border-amber-400/35 bg-amber-400/10 text-amber-200")}>{(applicationGuide.readiness ?? "needs_confirmation").replace("_", " ")}</span>
                        </div>
                        <p className="mt-3 text-[11px] leading-5 text-muted">{applicationGuide.hiringPriorities?.length ? applicationGuide.hiringPriorities[0] : "Review the evidence map and confirm any uncertain requirements."}</p>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {(applicationGuide.keywords ?? []).map((keyword) => <span key={keyword} className="rounded border border-border bg-white/[0.035] px-2 py-1 text-[10px] font-bold text-[#d8dee8]">{keyword}</span>)}
                        </div>
                      </article>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {[
                        { label: "Hiring priorities", values: applicationGuide.hiringPriorities, tone: "text-accent" },
                        { label: "Must have", values: applicationGuide.mustHave, tone: "text-white" },
                        { label: "Nice to have", values: applicationGuide.niceToHave, tone: "text-[#8cc7ff]" },
                        { label: "Hard constraints", values: applicationGuide.hardConstraints, tone: "text-amber-200" },
                      ].map((group) => (
                        <article key={group.label} className="rounded-md border border-border bg-white/[0.02] p-3">
                          <h3 className={cn("text-[10px] font-black uppercase tracking-[0.1em]", group.tone)}>{group.label}</h3>
                          {group.values?.length ? <ul className="mt-2 space-y-1.5 text-[11px] leading-4 text-muted">{group.values.map((value) => <li key={value} className="flex gap-2"><CircleDot className="mt-0.5 h-3 w-3 shrink-0" />{value}</li>)}</ul> : <p className="mt-2 text-[10px] text-muted">None identified</p>}
                        </article>
                      ))}
                    </div>

                    {applicationGuide.evidenceMatrix?.length ? (
                      <section className="overflow-hidden rounded-md border border-border bg-[#0c1219]">
                        <div className="border-b border-border px-4 py-3"><h3 className="text-sm font-bold text-white">Requirement → candidate evidence</h3><p className="mt-1 text-[10px] text-muted">Every important vacancy signal is linked to proof, a transferable skill, a question, or an explicit gap.</p></div>
                        <div className="divide-y divide-border">
                          {applicationGuide.evidenceMatrix.map((item) => {
                            const meta = evidenceStatusMeta(item.status);
                            return <article key={`${item.requirement}-${item.status}`} className="grid gap-2 px-4 py-3 md:grid-cols-[minmax(150px,0.8fr)_minmax(0,1.2fr)_auto] md:items-start">
                              <div><p className="text-xs font-bold text-white">{item.requirement}</p><p className="mt-1 text-[9px] font-black uppercase text-muted">{item.importance}</p></div>
                              <div><p className="text-[11px] leading-4 text-[#d8dee8]">{item.evidence || "No verified evidence found in the profile."}</p>{item.action ? <p className="mt-1.5 text-[10px] leading-4 text-muted"><span className="font-bold text-white">Action:</span> {item.action}</p> : null}</div>
                              <span className={cn("rounded border px-2 py-1 text-[9px] font-black uppercase", meta.className)}>{meta.label}</span>
                            </article>;
                          })}
                        </div>
                      </section>
                    ) : null}

                    {clarificationQuestions.length ? (
                      <section className="rounded-md border border-amber-400/25 bg-amber-400/[0.045] p-4">
                        <div className="flex items-start gap-3"><MessageSquareText className="mt-0.5 h-5 w-5 shrink-0 text-amber-200" /><div><h3 className="text-sm font-bold text-white">Confirm important missing evidence</h3><p className="mt-1 text-[10px] leading-4 text-muted">Answer with a concrete true example, or write “No”. Proposed claims are never used until you confirm them.</p></div></div>
                        <div className="mt-3 grid gap-3">
                          {clarificationQuestions.map((question) => (
                            <label key={question.id} className="block rounded-md border border-border bg-[#0c1219] p-3">
                              <span className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold text-white">{question.question}</span>{question.blocking ? <span className="rounded border border-amber-400/30 px-1.5 py-0.5 text-[8px] font-black uppercase text-amber-200">Required</span> : null}</span>
                              {question.why ? <span className="mt-1 block text-[10px] leading-4 text-muted">Why: {question.why}</span> : null}
                              {question.claimIfConfirmed ? <span className="mt-1 block text-[10px] leading-4 text-[#b9c2cf]">If confirmed, AI may write: “{question.claimIfConfirmed}”</span> : null}
                              <textarea value={clarificationAnswers[question.id] ?? ""} onChange={(event) => updateClarificationAnswer(question.id, event.target.value)} rows={2} placeholder="Describe what you actually did, tools/features used, and result — or write No" className="mt-2 w-full resize-y rounded-md border border-border bg-[#151c24] px-3 py-2 text-xs leading-5 text-white outline-none placeholder:text-muted/60 focus:border-amber-400/50" />
                            </label>
                          ))}
                        </div>
                      </section>
                    ) : <div className="flex items-center gap-2 rounded-md border border-success/25 bg-success/[0.045] px-3 py-2 text-[11px] text-[#dfe4ec]"><CheckCircle2 className="h-4 w-4 text-success" /> No high-impact candidate confirmations are required.</div>}

                    <div className="grid gap-3 lg:grid-cols-2">
                      <article className="rounded-md border border-border bg-white/[0.02] p-4"><h3 className="text-sm font-bold text-white">CV strategy</h3><p className="mt-2 text-xs leading-5 text-[#dfe4ec]">{applicationGuide.resumePlan?.summaryFocus || applicationGuide.cvImprovements?.[0]}</p>{applicationGuide.resumePlan?.targetHeadline ? <p className="mt-2 text-[10px] text-muted"><span className="font-bold text-white">Target headline:</span> {applicationGuide.resumePlan.targetHeadline}</p> : null}<ul className="mt-2 space-y-1.5 text-[11px] leading-4 text-muted">{[...(applicationGuide.resumePlan?.evidenceToLead ?? []), ...(applicationGuide.resumePlan?.bulletStrategy ?? []), ...(applicationGuide.cvImprovements ?? [])].slice(0, 6).map((item) => <li key={item} className="flex gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />{item}</li>)}</ul></article>
                      <article className="rounded-md border border-border bg-white/[0.02] p-4"><h3 className="text-sm font-bold text-white">Cover letter strategy</h3><p className="mt-2 text-xs leading-5 text-[#dfe4ec]">{applicationGuide.coverLetterPlan?.openingAngle || applicationGuide.coverLetterStrategy?.[0]}</p>{applicationGuide.coverLetterPlan?.motivationAngle ? <p className="mt-2 text-[10px] leading-4 text-muted"><span className="font-bold text-white">Motivation:</span> {applicationGuide.coverLetterPlan.motivationAngle}</p> : null}<ul className="mt-2 space-y-1.5 text-[11px] leading-4 text-muted">{[...(applicationGuide.coverLetterPlan?.proofPoints ?? []), ...(applicationGuide.coverLetterStrategy ?? [])].slice(0, 5).map((item) => <li key={item} className="flex gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />{item}</li>)}</ul></article>
                    </div>

                    {(applicationGuide.risks ?? []).length ? <div className="rounded-md border border-red-400/25 bg-red-500/[0.045] p-3"><h3 className="flex items-center gap-2 text-xs font-bold text-red-100"><AlertTriangle className="h-4 w-4" /> Do not claim without evidence</h3><ul className="mt-2 space-y-1 text-[10px] leading-4 text-red-100/80">{applicationGuide.risks.map((risk) => <li key={risk}>• {risk}</li>)}</ul></div> : null}
                  </div>
                ) : <div className="rounded-md border border-border bg-[#0c1219] py-10 text-center"><Sparkles className="mx-auto h-5 w-5 text-muted" /><p className="mt-2 text-[11px] text-muted">Run AI Match for this vacancy to create the evidence map and document plan.</p></div>}
                <p className="mt-2 text-[10px] leading-4 text-muted">To refresh this plan, return to Jobs and use Rerun AI Match. That remains the single vacancy analysis.</p>
              </div>
            </section>

            <section className="panel p-4 sm:p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.12em] text-accent">Application pack</p>
                  <h2 className="mt-1 text-lg font-bold text-white">Documents tailored to this vacancy</h2>
                  <p className="mt-1 text-xs leading-5 text-muted">Choose DOCX originals, then AI changes their text without replacing the design.</p>
                </div>
                <Button onClick={generatePack} disabled={isGeneratingPack || Boolean(generationType) || !selectedResumeSourceId || !selectedCoverSourceId || !applicationReview || unansweredBlockingQuestions.length > 0} className="h-10 shrink-0 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-4 text-xs font-bold text-white shadow-[0_10px_28px_rgba(255,90,0,0.2)] disabled:opacity-45">
                  {isGeneratingPack ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {isGeneratingPack ? "Generating pack…" : "Generate application pack"}
                </Button>
              </div>

              {documentError ? <div className="mt-3 rounded-md border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs leading-5 text-red-200">{documentError}</div> : null}
              {effectiveLanguage && !resumeSources.some((source) => source.language === effectiveLanguage) ? <div className="mt-3 rounded-md border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs leading-5 text-amber-200">No {effectiveLanguage} CV DOCX is saved in Profile. Add one or choose another language.</div> : null}

              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                <DocumentCard
                  icon={FileText}
                  label="Tailored CV"
                  description="Rewrites existing text blocks while keeping the DOCX structure and design."
                  document={latestResume}
                  isGenerating={generationType === "tailored_resume"}
                  onGenerate={() => generateDocument("tailored_resume")}
                  canGenerate={Boolean(selectedResumeSourceId && applicationReview && unansweredBlockingQuestions.length === 0)}
                  disabledLabel={!selectedResumeSourceId ? "Select DOCX" : !applicationReview ? "AI Match required" : "Answer required questions"}
                  sourceControl={(
                    <SourcePicker
                      label="Source CV"
                      sources={resumeSources}
                      selectedId={selectedResumeSourceId}
                      onChange={(sourceId) => {
                        setSelectedResumeSourceId(sourceId);
                        setIsResumeSourceManual(Boolean(sourceId));
                      }}
                      onAttach={(file) => void attachWorkspaceSource(file, "CV / Resume")}
                    />
                  )}
                />
                <DocumentCard
                  icon={Mail}
                  label="Cover letter"
                  description="Tailors the letter inside the selected DOCX without replacing its layout."
                  document={latestCoverLetter}
                  isGenerating={generationType === "cover_letter"}
                  onGenerate={() => generateDocument("cover_letter")}
                  canGenerate={Boolean(selectedCoverSourceId && applicationReview && unansweredBlockingQuestions.length === 0)}
                  disabledLabel={!selectedCoverSourceId ? "Select DOCX" : !applicationReview ? "AI Match required" : "Answer required questions"}
                  sourceControl={(
                    <SourcePicker
                      label="Source cover letter"
                      sources={coverSources}
                      selectedId={selectedCoverSourceId}
                      onChange={(sourceId) => {
                        setSelectedCoverSourceId(sourceId);
                        setIsCoverSourceManual(Boolean(sourceId));
                      }}
                      onAttach={(file) => void attachWorkspaceSource(file, "Cover Letter")}
                    />
                  )}
                />
              </div>
            </section>

            <section className="panel p-4 sm:p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.12em] text-accent">Final review</p>
                  <h2 className="mt-1 text-base font-bold text-white">Submission checklist</h2>
                </div>
                {application.status === "draft" ? (
                  <Button onClick={() => onMarkApplied(application.id)} className="h-9 rounded-md bg-success px-3 text-xs font-bold text-[#081006] hover:bg-[#6de046]"><Check className="h-4 w-4" /> Mark as applied</Button>
                ) : <span className="inline-flex items-center gap-1.5 rounded-md border border-success/35 bg-success/10 px-2.5 py-1.5 text-[11px] font-bold text-success"><Check className="h-3.5 w-3.5" /> Application tracked</span>}
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {checklist.map((item) => (
                  <div key={item.label} className="flex items-center gap-2.5 rounded-md border border-border bg-white/[0.025] px-3 py-2.5">
                    <span className={cn("grid h-5 w-5 place-items-center rounded-full border", item.ready ? "border-success/40 bg-success/12 text-success" : "border-white/20 text-muted")}>
                      {item.ready ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
                    </span>
                    <span className={cn("text-xs font-semibold", item.ready ? "text-[#e4e9f0]" : "text-muted")}>{item.label}</span>
                    <span className="ml-auto text-[9px] font-bold uppercase text-muted">{item.ready ? "Ready" : "Missing"}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="relative overflow-hidden rounded-lg border border-[#7c5cff]/30 bg-gradient-to-br from-[#17142a] via-[#111722] to-[#111821] p-4 sm:p-5">
              <div className="absolute -right-12 -top-14 h-44 w-44 rounded-full bg-[#7c5cff]/12 blur-3xl" />
              <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[#9f7aea]/35 bg-[#9f7aea]/15 text-[#c4a7ff]"><Rocket className="h-5 w-5" /></span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2"><h2 className="text-base font-bold text-white">Auto Apply</h2><span className="rounded border border-[#9f7aea]/35 bg-[#9f7aea]/12 px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.1em] text-[#c4a7ff]">Coming soon</span></div>
                    <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">AI will open the employer form, fill approved answers, upload these documents and pause before final submission.</p>
                    <p className="mt-2 inline-flex items-center gap-1.5 text-[10px] font-bold text-[#b8c0cc]"><ShieldCheck className="h-3.5 w-3.5 text-success" /> You will always review before anything is submitted.</p>
                  </div>
                </div>
                <Button disabled className="h-10 shrink-0 rounded-md border border-[#9f7aea]/30 bg-[#9f7aea]/10 px-4 text-xs font-bold text-[#c4a7ff] opacity-75"><LockKeyhole className="h-4 w-4" /> Auto Apply</Button>
              </div>
            </section>
          </main>

          <aside className="space-y-3">
            <section className="panel overflow-hidden">
              <div className="border-b border-border p-4">
                <div className="flex items-center gap-2.5"><span className="grid h-9 w-9 place-items-center rounded-md bg-accent/14 text-accent"><Bot className="h-4 w-4" /></span><div><h2 className="text-sm font-bold text-white">AI Application Coach</h2><p className="mt-0.5 text-[10px] text-muted">Ask follow-ups about the plan or vacancy</p></div></div>
              </div>
              <div className="p-4">
                <div className="grid gap-2">
                  {[
                    "What should I emphasize in this application?",
                    "Review the biggest risks before I apply.",
                    "Suggest concise answers for likely application questions.",
                  ].map((prompt) => (
                    <button key={prompt} type="button" disabled={isLoadingAdvice} onClick={() => requestAdvice(prompt)} className={cn("rounded-md border p-2.5 text-left text-[11px] font-semibold leading-4 transition", advicePrompt === prompt ? "border-accent/45 bg-accent/10 text-white" : "border-border bg-white/[0.025] text-[#d8dee8] hover:border-accent/35 hover:bg-accent/[0.06]")}>{prompt}</button>
                  ))}
                </div>
                <div className="job-scroll mt-3 max-h-[360px] min-h-[150px] overflow-y-auto rounded-md border border-border bg-[#0c1219] p-3">
                  {isLoadingAdvice ? <div className="flex items-center gap-2 text-xs text-muted"><LoaderCircle className="h-4 w-4 animate-spin text-accent" /> Reviewing your question…</div> : advice ? <p className="whitespace-pre-wrap text-xs leading-5 text-[#dfe4ec]">{advice}</p> : <div className="py-6 text-center"><Sparkles className="mx-auto h-5 w-5 text-muted" /><p className="mt-2 text-[11px] leading-5 text-muted">The full improvement plan is above the document generator. Choose a question for more detail.</p></div>}
                </div>
                <Button variant="ghost" onClick={() => onOpenAssistant("Review this application and help me finish it.", application.id)} className="mt-3 h-9 w-full rounded-md border border-border bg-transparent text-xs text-[#e6ebf3] hover:bg-white/[0.06]">Continue in full Assistant <ChevronRight className="h-4 w-4" /></Button>
              </div>
            </section>

            <section className="panel p-4">
              <h2 className="text-sm font-bold text-white">Why you match</h2>
              <div className="mt-3 space-y-2">
                {(application.job.aiMatch?.reasons.length ? application.job.aiMatch.reasons : application.job.skills.slice(0, 4).map((skill) => `${skill} aligns with this role.`)).slice(0, 4).map((reason) => (
                  <div key={reason} className="flex gap-2 text-[11px] leading-4 text-[#d8dee8]"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" /><span>{reason}</span></div>
                ))}
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
  isGenerating,
  onGenerate,
  canGenerate,
  disabledLabel,
  sourceControl,
}: {
  icon: typeof FileText;
  label: string;
  description: string;
  document: GeneratedDocument | undefined;
  isGenerating: boolean;
  onGenerate: () => void;
  canGenerate: boolean;
  disabledLabel: string;
  sourceControl?: React.ReactNode;
}) {
  const content = currentContent(document);
  return (
    <article className="flex min-h-[360px] flex-col rounded-lg border border-border bg-white/[0.025] p-3.5">
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-accent/12 text-accent"><Icon className="h-4 w-4" /></span>
        <div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-bold text-white">{label}</h3>{document ? <span className="inline-flex items-center gap-1 rounded border border-success/35 bg-success/10 px-1.5 py-0.5 text-[9px] font-bold text-success"><FileCheck2 className="h-3 w-3" /> Ready · v{document.currentVersion}</span> : <span className="rounded border border-border px-1.5 py-0.5 text-[9px] font-bold text-muted">Not generated</span>}</div><p className="mt-1 text-[10px] leading-4 text-muted">{description}</p></div>
      </div>
      {sourceControl}
      <div className="mt-3 min-h-[180px] flex-1 overflow-hidden rounded-md border border-border bg-[#f6f4ef] p-4 text-[#20242a] shadow-inner">
        {isGenerating ? <div className="grid h-full min-h-[150px] place-items-center text-center"><div><LoaderCircle className="mx-auto h-5 w-5 animate-spin text-[#ff5a00]" /><p className="mt-2 text-[11px] font-semibold text-[#646b74]">Writing an evidence-based version…</p></div></div> : content ? <p className="line-clamp-[10] whitespace-pre-wrap font-serif text-[10px] leading-[1.55]">{content}</p> : <div className="grid h-full min-h-[150px] place-items-center text-center"><div><Icon className="mx-auto h-6 w-6 text-[#a4a8ad]" /><p className="mt-2 text-[11px] font-semibold text-[#767c84]">Your document preview will appear here.</p></div></div>}
      </div>
      <div className="mt-3 flex gap-2">
        <Button type="button" disabled={isGenerating || !canGenerate} onClick={onGenerate} className="h-9 flex-1 rounded-md bg-accent px-3 text-[11px] font-bold text-white hover:bg-[#ff6a14] disabled:opacity-45">{isGenerating ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : document ? <RefreshCw className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}{isGenerating ? "Generating…" : !canGenerate ? disabledLabel : document ? "Regenerate" : "Generate"}</Button>
        {document ? <a href={`${apiBaseUrl}/documents/${encodeURIComponent(document.id)}/download`} download={documentFileName(document)} className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border px-3 text-[11px] font-bold text-[#e6ebf3] transition hover:bg-white/[0.06]"><Download className="h-3.5 w-3.5" /> DOCX</a> : null}
      </div>
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
    <div className="mt-3 rounded-md border border-border bg-black/10 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
        <label className="inline-flex cursor-pointer items-center gap-1 text-[10px] font-bold text-accent hover:text-white">
          <Upload className="h-3.5 w-3.5" /> Attach for this application
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
      <select value={selectedId} onChange={(event) => onChange(event.target.value)} className="mt-2 h-8 w-full rounded-md border border-border bg-[#151c24] px-2 text-[11px] font-semibold text-white outline-none focus:border-accent/60">
        <option value="">Select DOCX source</option>
        {sources.map((source) => <option key={source.id} value={source.id}>{source.language ? `${source.language} · ` : ""}{source.title} · {source.file_name}</option>)}
      </select>
      <p className="mt-2 text-[9px] leading-4 text-muted">{sources.length ? "The selected DOCX is copied and keeps its layout, styles, images, header and footer." : "No DOCX source in Profile yet. Add one there or attach it for this application."}</p>
    </div>
  );
}
