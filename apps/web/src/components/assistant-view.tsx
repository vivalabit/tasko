"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  Copy,
  FileText,
  Mail,
  MessageSquarePlus,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Square,
  Target,
  Trash2,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type AssistantLaunch = {
  id: string;
  prompt: string;
  contextKind: "profile" | "job" | "application";
  contextId?: string;
};

type AssistantProfile = {
  name: string;
  current_role: string;
  desired_role: string;
  skills: string;
  experience: string;
  resume_file_name: string;
};

type AssistantJob = {
  id: string;
  title: string;
  company: string;
  location: string;
  type?: string;
  match: number;
  overview: string;
  responsibilities?: string[];
  requirements: string[];
  skills: string[];
  aiMatch?: {
    reasons: string[];
    gaps: string[];
  };
};

type AssistantApplication = {
  id: string;
  status: string;
  notes: string;
  nextStep: string;
  job: AssistantJob;
};

type AssistantContextKind = AssistantLaunch["contextKind"];
type AssistantConnectionStatus = "idle" | "connecting" | "connected" | "reconnecting" | "disconnected";

type AssistantSseEvent = {
  event: string;
  data: Record<string, unknown>;
};

type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  source?: "openclaw" | "local";
};

type AssistantThread = {
  id: string;
  title: string;
  contextKind: AssistantContextKind;
  contextId: string;
  updatedAt: string;
  messages: AssistantMessage[];
};

type AssistantViewProps = {
  profile: AssistantProfile;
  jobs: AssistantJob[];
  applications: AssistantApplication[];
  launch: AssistantLaunch | null;
  onLaunchHandled: () => void;
};

const assistantThreadsStorageKey = "tasko.assistantThreads.v1";
const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const quickActions = [
  {
    title: "Tailor my resume",
    description: "Highlight the right evidence for a vacancy",
    prompt: "Tailor my resume for this job and suggest the five highest-impact changes.",
    icon: FileText,
  },
  {
    title: "Write a cover letter",
    description: "Create a focused, evidence-based draft",
    prompt: "Write a concise cover letter for this job using only evidence from my profile.",
    icon: Mail,
  },
  {
    title: "Prepare for interview",
    description: "Practice likely questions and strong answers",
    prompt: "Prepare me for an interview for this role with likely questions and answer guidance.",
    icon: Target,
  },
  {
    title: "Plan my job search",
    description: "Turn my current pipeline into next steps",
    prompt: "Review my job search context and give me a focused action plan for this week.",
    icon: BriefcaseBusiness,
  },
];

function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function parseSseEvent(block: string): AssistantSseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (!dataLines.length) return null;

  try {
    const data = JSON.parse(dataLines.join("\n")) as unknown;
    return data && typeof data === "object" ? { event, data: data as Record<string, unknown> } : null;
  } catch {
    return null;
  }
}

async function consumeAssistantSse(
  response: Response,
  onEvent: (event: AssistantSseEvent) => void,
): Promise<"done" | "stopped" | "error" | null> {
  if (!response.body) throw new Error("Assistant stream has no response body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const parsed = parseSseEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      if (parsed) {
        onEvent(parsed);
        if (["done", "stopped", "error"].includes(parsed.event)) {
          return parsed.event as "done" | "stopped" | "error";
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
    if (done) return null;
  }
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function normalizeThreads(value: unknown): AssistantThread[] {
  if (!Array.isArray(value)) return [];

  return value
    .filter((item): item is AssistantThread => {
      if (!item || typeof item !== "object") return false;
      const candidate = item as Partial<AssistantThread>;
      return (
        typeof candidate.id === "string" &&
        typeof candidate.title === "string" &&
        typeof candidate.updatedAt === "string" &&
        Array.isArray(candidate.messages) &&
        ["profile", "job", "application"].includes(candidate.contextKind ?? "")
      );
    })
    .slice(0, 30);
}

function formatThreadDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";

  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function createThreadTitle(prompt: string) {
  const normalized = prompt.replace(/\s+/g, " ").trim();
  if (!normalized) return "New conversation";
  return normalized.length > 42 ? `${normalized.slice(0, 42).trim()}…` : normalized;
}

function getContextLabel(
  contextKind: AssistantContextKind,
  contextId: string,
  jobs: AssistantJob[],
  applications: AssistantApplication[],
) {
  if (contextKind === "profile") return "My profile";
  if (contextKind === "job") {
    const job = jobs.find((item) => item.id === contextId);
    return job ? `${job.title} · ${job.company}` : "Select a vacancy";
  }

  const application = applications.find((item) => item.id === contextId);
  return application ? `${application.job.title} · ${application.job.company}` : "Select an application";
}

function getContextJob(
  contextKind: AssistantContextKind,
  contextId: string,
  jobs: AssistantJob[],
  applications: AssistantApplication[],
) {
  if (contextKind === "job") return jobs.find((job) => job.id === contextId) ?? null;
  if (contextKind === "application") {
    return applications.find((application) => application.id === contextId)?.job ?? null;
  }
  return null;
}

function serializeAssistantJob(job: AssistantJob | null) {
  if (!job) return null;

  return {
    id: job.id,
    title: job.title,
    company: job.company,
    location: job.location,
    type: job.type ?? "",
    match: job.match,
    overview: job.overview,
    responsibilities: job.responsibilities ?? [],
    requirements: job.requirements,
    skills: job.skills,
    aiMatch: job.aiMatch ? {
      reasons: job.aiMatch.reasons,
      gaps: job.aiMatch.gaps,
    } : null,
  };
}

function getAssistantResponse({
  prompt,
  profile,
  job,
  application,
}: {
  prompt: string;
  profile: AssistantProfile;
  job: AssistantJob | null;
  application: AssistantApplication | null;
}) {
  const normalizedPrompt = prompt.toLowerCase();
  const candidateName = profile.name.trim() || "the candidate";
  const desiredRole = profile.desired_role.trim() || profile.current_role.trim() || "your target role";
  const roleLabel = job ? `${job.title} at ${job.company}` : desiredRole;
  const skills = job?.skills.filter(Boolean).slice(0, 5) ?? [];
  const reasons = job?.aiMatch?.reasons.filter(Boolean).slice(0, 3) ?? [];
  const gaps = job?.aiMatch?.gaps.filter(Boolean).slice(0, 3) ?? [];
  const evidence = profile.experience.trim() || profile.skills.trim();

  if (normalizedPrompt.includes("cover letter") || normalizedPrompt.includes("сопровод")) {
    return [
      `Dear ${job?.company ? `${job.company} hiring team` : "Hiring Manager"},`,
      "",
      `I am applying for the ${job?.title ?? desiredRole} position. My background as ${profile.current_role || desiredRole} aligns with the role's focus${skills.length ? ` on ${skills.join(", ")}` : " and its core responsibilities"}.`,
      "",
      evidence
        ? `The strongest evidence to develop in the final version is: ${evidence.slice(0, 280)}${evidence.length > 280 ? "…" : ""}`
        : "Before sending, add one verified achievement with a measurable outcome. I have left this as guidance rather than inventing an example.",
      "",
      `I would welcome the opportunity to discuss how my experience could contribute to ${job?.company ?? "your team"}.`,
      "",
      `Best regards,\n${candidateName}`,
      "",
      "Review note: verify every claim and add one role-specific metric before sending.",
    ].join("\n");
  }

  if (normalizedPrompt.includes("interview") || normalizedPrompt.includes("интервью")) {
    const questions = [
      `Why are you interested in ${roleLabel}?`,
      `Which achievement best proves your ability to succeed in this role?`,
      skills[0] ? `Tell me about a time you used ${skills[0]} to solve a difficult problem.` : "Tell me about a difficult problem you solved.",
      gaps[0] ? `How would you address this potential gap: ${gaps[0]}?` : "What would you aim to accomplish in your first 90 days?",
      `What questions do you have for ${job?.company ?? "the hiring team"}?`,
    ];

    return [
      `Interview plan for ${roleLabel}`,
      "",
      ...questions.map((question, index) => `${index + 1}. ${question}\n   Answer with Situation → Action → Result, using only a real example from your experience.`),
      "",
      `Your strongest themes: ${reasons.length ? reasons.join("; ") : "connect your verified experience directly to the role requirements"}.`,
      "Prepare two questions about team priorities and how success will be measured in the first six months.",
    ].join("\n");
  }

  if (normalizedPrompt.includes("resume") || normalizedPrompt.includes("cv") || normalizedPrompt.includes("резюме")) {
    return [
      `Resume tailoring plan for ${roleLabel}`,
      "",
      `1. Rewrite the headline around “${job?.title ?? desiredRole}” and keep it specific.`,
      `2. Move the most relevant verified achievements into the top third of the resume.`,
      `3. Add supported keywords${skills.length ? `: ${skills.join(", ")}` : " from the vacancy requirements"}.`,
      "4. Turn responsibility statements into outcome statements with scope, action, and result.",
      gaps.length
        ? `5. Address these gaps honestly: ${gaps.join("; ")}. Do not add experience you cannot defend.`
        : "5. Check every claim against your profile and remove generic filler.",
      "",
      profile.resume_file_name
        ? `Context used: ${profile.resume_file_name}, profile, and the selected vacancy.`
        : "Your profile is available, but no resume file is attached. Attach one for line-by-line tailoring.",
    ].join("\n");
  }

  if (normalizedPrompt.includes("follow-up") || normalizedPrompt.includes("follow up") || normalizedPrompt.includes("recruiter")) {
    return [
      `Subject: Following up on the ${job?.title ?? desiredRole} application`,
      "",
      `Hi ${job?.company ? `${job.company} team` : "there"},`,
      "",
      `I wanted to follow up on my application for the ${job?.title ?? desiredRole} role. I remain very interested in the opportunity and would be happy to provide any additional information that would be helpful.`,
      "",
      `Thank you for your time,\n${candidateName}`,
      "",
      application?.nextStep ? `Pipeline note: current next step is “${application.nextStep}”.` : "Keep the message brief and send it only after an appropriate waiting period.",
    ].join("\n");
  }

  if (job) {
    return [
      `Current assessment: ${roleLabel} has a ${job.match}% displayed match.`,
      "",
      reasons.length ? `Strong signals:\n${reasons.map((item) => `• ${item}`).join("\n")}` : "Strong signals: compare your verified achievements with the core requirements.",
      gaps.length ? `\nGaps to review:\n${gaps.map((item) => `• ${item}`).join("\n")}` : "\nNo major gaps are recorded in the current AI match.",
      "",
      "Recommended next step: tailor the top third of the resume, verify the source vacancy, then prepare a short role-specific note.",
    ].join("\n");
  }

  return [
    `A focused plan for ${candidateName}:`,
    "",
    "1. Complete the profile and attach the latest resume.",
    "2. Prioritize a small set of roles that match your target and constraints.",
    "3. Tailor each application using verified achievements, not generic claims.",
    "4. Track follow-ups and interview preparation in the application pipeline.",
    "",
    `Current target: ${desiredRole}. Select a vacancy or application above for a more specific answer.`,
  ].join("\n");
}

export function AssistantView({ profile, jobs, applications, launch, onLaunchHandled }: AssistantViewProps) {
  const [threads, setThreads] = useState<AssistantThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [historyQuery, setHistoryQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [contextKind, setContextKind] = useState<AssistantContextKind>("profile");
  const [contextId, setContextId] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<AssistantConnectionStatus>("idle");
  const [streamingMessageId, setStreamingMessageId] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState("");
  const [isLoaded, setIsLoaded] = useState(false);
  const launchedIdRef = useRef("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const streamAbortControllerRef = useRef<AbortController | null>(null);
  const activeRequestIdRef = useRef("");
  const stopRequestedRef = useRef(false);

  const activeThread = threads.find((thread) => thread.id === activeThreadId) ?? null;
  const selectedApplication = contextKind === "application"
    ? applications.find((application) => application.id === contextId) ?? null
    : null;
  const selectedJob = getContextJob(contextKind, contextId, jobs, applications);
  const contextLabel = getContextLabel(contextKind, contextId, jobs, applications);
  const connectionLabel = connectionStatus === "connecting"
    ? "Connecting…"
    : connectionStatus === "connected"
      ? "Connected"
      : connectionStatus === "reconnecting"
        ? "Reconnecting…"
        : connectionStatus === "disconnected"
          ? "Connection lost"
          : "Ready";

  const filteredThreads = useMemo(() => {
    const query = historyQuery.trim().toLowerCase();
    return threads
      .filter((thread) => !query || thread.title.toLowerCase().includes(query))
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }, [historyQuery, threads]);

  useEffect(() => {
    try {
      const rawThreads = window.localStorage.getItem(assistantThreadsStorageKey);
      const storedThreads = normalizeThreads(rawThreads ? JSON.parse(rawThreads) : []);
      setThreads(storedThreads);
      setActiveThreadId(storedThreads[0]?.id ?? "");
    } catch {
      window.localStorage.removeItem(assistantThreadsStorageKey);
    } finally {
      setIsLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    window.localStorage.setItem(assistantThreadsStorageKey, JSON.stringify(threads.slice(0, 30)));
  }, [isLoaded, threads]);

  useEffect(() => {
    if (!activeThread) return;
    setContextKind(activeThread.contextKind);
    setContextId(activeThread.contextId);
  }, [activeThread?.id]);

  useEffect(() => {
    if (!launch || launchedIdRef.current === launch.id) return;
    launchedIdRef.current = launch.id;
    setActiveThreadId("");
    setContextKind(launch.contextKind);
    setContextId(launch.contextId ?? "");
    setDraft(launch.prompt);
    onLaunchHandled();
  }, [launch, onLaunchHandled]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeThread?.messages.length, activeThread?.messages.at(-1)?.content, isGenerating]);

  function updateThreadContext(nextKind: AssistantContextKind, nextId: string) {
    setContextKind(nextKind);
    setContextId(nextId);
    if (!activeThread) return;

    setThreads((currentThreads) => currentThreads.map((thread) =>
      thread.id === activeThread.id
        ? { ...thread, contextKind: nextKind, contextId: nextId, updatedAt: new Date().toISOString() }
        : thread,
    ));
  }

  function startNewChat() {
    setActiveThreadId("");
    setDraft("");
    setContextKind("profile");
    setContextId("");
  }

  function deleteThread(threadId: string) {
    setThreads((currentThreads) => currentThreads.filter((thread) => thread.id !== threadId));
    if (activeThreadId === threadId) setActiveThreadId("");
  }

  async function submitMessage(explicitPrompt?: string) {
    const prompt = (explicitPrompt ?? draft).trim();
    if (!prompt || isGenerating) return;

    const now = new Date().toISOString();
    const threadId = activeThread?.id ?? createId("assistant-thread");
    const userMessage: AssistantMessage = {
      id: createId("assistant-user"),
      role: "user",
      content: prompt,
      createdAt: now,
    };
    const assistantMessageId = createId("assistant-response");
    const pendingAssistantMessage: AssistantMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      createdAt: now,
    };
    if (activeThread) {
      setThreads((currentThreads) => currentThreads.map((thread) =>
        thread.id === threadId
          ? { ...thread, messages: [...thread.messages, userMessage, pendingAssistantMessage], updatedAt: now }
          : thread,
      ));
    } else {
      setThreads((currentThreads) => [{
        id: threadId,
        title: createThreadTitle(prompt),
        contextKind,
        contextId,
        updatedAt: now,
        messages: [userMessage, pendingAssistantMessage],
      }, ...currentThreads]);
      setActiveThreadId(threadId);
    }

    setDraft("");
    setIsGenerating(true);
    setStreamingMessageId(assistantMessageId);
    setConnectionStatus("connecting");
    stopRequestedRef.current = false;
    const requestId = createId("assistant-stream");
    activeRequestIdRef.current = requestId;
    const abortController = new AbortController();
    streamAbortControllerRef.current = abortController;
    let streamedContent = "";
    let offset = 0;
    let completed = false;
    let terminalError = "";
    const requestPayload = {
      requestId,
      threadId,
      message: prompt,
      contextKind,
      contextId,
      job: serializeAssistantJob(selectedJob),
      application: selectedApplication ? {
        id: selectedApplication.id,
        status: selectedApplication.status,
        notes: selectedApplication.notes,
        nextStep: selectedApplication.nextStep,
        job: serializeAssistantJob(selectedApplication.job),
      } : null,
    };

    const updateAssistantMessage = (content: string, source?: AssistantMessage["source"]) => {
      const updatedAt = new Date().toISOString();
      setThreads((currentThreads) => currentThreads.map((thread) =>
        thread.id === threadId
          ? {
              ...thread,
              updatedAt,
              messages: thread.messages.map((message) =>
                message.id === assistantMessageId ? { ...message, content, source, createdAt: updatedAt } : message,
              ),
            }
          : thread,
      ));
    };

    try {
      for (let attempt = 0; attempt < 4 && !completed; attempt += 1) {
        if (attempt > 0) {
          setConnectionStatus("reconnecting");
          await wait(Math.min(400 * (2 ** (attempt - 1)), 1600));
        }

        try {
          const apiResponse = await fetch(`${apiBaseUrl}/assistant/chat/stream`, {
            method: "POST",
            headers: {
              Accept: "text/event-stream",
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ ...requestPayload, offset }),
            signal: abortController.signal,
          });
          if (!apiResponse.ok) {
            throw new Error(`Assistant stream failed with status ${apiResponse.status}`);
          }

          const terminalEvent = await consumeAssistantSse(apiResponse, ({ event, data }) => {
            if (event === "connected") {
              setConnectionStatus("connected");
              return;
            }
            if (event === "delta" && typeof data.text === "string" && typeof data.offset === "number") {
              streamedContent += data.text;
              offset = data.offset;
              updateAssistantMessage(streamedContent, "openclaw");
              return;
            }
            if (event === "error") {
              terminalError = typeof data.message === "string" ? data.message : "Assistant generation failed";
            }
          });

          if (terminalEvent === "done") {
            completed = true;
            updateAssistantMessage(streamedContent.trim(), "openclaw");
          } else if (terminalEvent === "stopped") {
            completed = true;
          } else if (terminalEvent === "error") {
            throw new Error(terminalError || "Assistant generation failed");
          } else {
            throw new Error("Assistant stream disconnected");
          }
        } catch (error) {
          if (stopRequestedRef.current || abortController.signal.aborted) throw error;
          if (attempt === 3 || terminalError) throw error;
        }
      }
    } catch {
      if (stopRequestedRef.current) {
        if (!streamedContent) {
          setThreads((currentThreads) => currentThreads.map((thread) =>
            thread.id === threadId
              ? { ...thread, messages: thread.messages.filter((message) => message.id !== assistantMessageId) }
              : thread,
          ));
        }
        setConnectionStatus("idle");
      } else if (!streamedContent) {
        const fallbackResponse = getAssistantResponse({
          prompt,
          profile,
          job: selectedJob,
          application: selectedApplication,
        });
        updateAssistantMessage(fallbackResponse, "local");
        setConnectionStatus("disconnected");
      } else {
        setConnectionStatus("disconnected");
      }
    } finally {
      setIsGenerating(false);
      setStreamingMessageId("");
      streamAbortControllerRef.current = null;
      activeRequestIdRef.current = "";
      if (completed) setConnectionStatus("idle");
    }
  }

  async function stopGenerating() {
    const requestId = activeRequestIdRef.current;
    if (!requestId || !isGenerating) return;
    stopRequestedRef.current = true;
    streamAbortControllerRef.current?.abort();
    setConnectionStatus("idle");
    try {
      await fetch(`${apiBaseUrl}/assistant/chat/stream/${encodeURIComponent(requestId)}`, {
        method: "DELETE",
      });
    } catch {
      // The local abort already stopped rendering; the server expires orphaned streams.
    }
  }

  function regenerateMessage(messageId: string) {
    if (!activeThread || isGenerating) return;
    const messageIndex = activeThread.messages.findIndex((message) => message.id === messageId);
    const previousUserMessage = [...activeThread.messages.slice(0, messageIndex)].reverse().find((message) => message.role === "user");
    if (!previousUserMessage) return;

    setThreads((currentThreads) => currentThreads.map((thread) =>
      thread.id === activeThread.id
        ? { ...thread, messages: thread.messages.filter((message) => message.id !== messageId) }
        : thread,
    ));
    setDraft(previousUserMessage.content);
  }

  async function copyMessage(message: AssistantMessage) {
    await navigator.clipboard?.writeText(message.content);
    setCopiedMessageId(message.id);
    window.setTimeout(() => setCopiedMessageId(""), 1400);
  }

  return (
    <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden px-3 py-3 sm:px-4 xl:px-4 2xl:px-5 2xl:py-4">
      <header className="mb-3 flex shrink-0 items-start justify-between gap-3 2xl:mb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-[#ff6b12] to-[#e43d00] text-white shadow-[0_10px_28px_rgba(255,90,0,0.28)]">
              <Sparkles className="h-[18px] w-[18px]" />
            </span>
            <div>
              <h1 className="text-[24px] font-bold leading-tight text-white sm:text-[27px] 2xl:text-[31px]">AI Assistant</h1>
              <p className="mt-0.5 text-[12px] text-muted 2xl:text-sm">Your context-aware job search workspace</p>
            </div>
          </div>
        </div>
        <Button onClick={startNewChat} disabled={isGenerating} className="h-9 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#dd3d00] px-3 text-xs 2xl:h-10 2xl:text-sm">
          <MessageSquarePlus className="h-4 w-4" /> New chat
        </Button>
      </header>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[210px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)_260px] 2xl:grid-cols-[250px_minmax(0,1fr)_290px] 2xl:gap-4">
        <aside className="panel hidden min-h-0 overflow-hidden lg:flex lg:flex-col">
          <div className="border-b border-border p-3">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Conversations</p>
            <label className="mt-2.5 flex h-9 items-center gap-2 rounded-md border border-border bg-white/[0.035] px-2.5 focus-within:border-accent/60">
              <Search className="h-3.5 w-3.5 text-muted" />
              <input value={historyQuery} onChange={(event) => setHistoryQuery(event.target.value)} placeholder="Search history" className="min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-muted" />
            </label>
          </div>
          <div className="job-scroll min-h-0 flex-1 overflow-y-auto p-2">
            {filteredThreads.length ? filteredThreads.map((thread) => (
              <div key={thread.id} className={cn("group relative mb-1 rounded-md border transition", thread.id === activeThreadId ? "border-accent/35 bg-accent/10" : "border-transparent hover:border-border hover:bg-white/[0.035]")}>
                <button type="button" onClick={() => setActiveThreadId(thread.id)} className="w-full p-2.5 pr-8 text-left">
                  <p className="line-clamp-2 text-xs font-bold leading-4 text-[#e7ebf2]">{thread.title}</p>
                  <div className="mt-1.5 flex items-center justify-between gap-2 text-[10px] text-muted">
                    <span className="truncate">{getContextLabel(thread.contextKind, thread.contextId, jobs, applications)}</span>
                    <span className="shrink-0">{formatThreadDate(thread.updatedAt)}</span>
                  </div>
                </button>
                <button type="button" onClick={() => deleteThread(thread.id)} aria-label="Delete conversation" className="absolute right-1.5 top-2 rounded p-1 text-muted opacity-0 transition hover:bg-white/10 hover:text-white group-hover:opacity-100">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )) : (
              <div className="px-2 py-8 text-center">
                <Bot className="mx-auto h-6 w-6 text-muted" />
                <p className="mt-2 text-xs font-semibold text-muted">No conversations yet</p>
              </div>
            )}
          </div>
        </aside>

        <main className="panel flex min-h-0 min-w-0 flex-col overflow-hidden">
          <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border px-3 py-2.5 2xl:px-4 2xl:py-3">
            <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted">Context</span>
            <div className="relative">
              <select
                value={contextKind}
                onChange={(event) => {
                  const nextKind = event.target.value as AssistantContextKind;
                  const nextId = nextKind === "job" ? jobs[0]?.id ?? "" : nextKind === "application" ? applications[0]?.id ?? "" : "";
                  updateThreadContext(nextKind, nextId);
                }}
                className="h-8 appearance-none rounded-md border border-border bg-[#151c24] pl-2.5 pr-7 text-xs font-bold text-white outline-none focus:border-accent/60"
              >
                <option value="profile">My profile</option>
                <option value="job" disabled={!jobs.length}>Vacancy</option>
                <option value="application" disabled={!applications.length}>Application</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-2 h-4 w-4 text-muted" />
            </div>
            {contextKind !== "profile" && (
              <div className="relative min-w-0 flex-1 sm:max-w-[390px]">
                <select
                  value={contextId}
                  onChange={(event) => updateThreadContext(contextKind, event.target.value)}
                  className="h-8 w-full appearance-none truncate rounded-md border border-border bg-[#151c24] pl-2.5 pr-7 text-xs font-semibold text-[#dfe4ec] outline-none focus:border-accent/60"
                >
                  {contextKind === "job" ? jobs.map((job) => <option key={job.id} value={job.id}>{job.title} · {job.company}</option>) : applications.map((application) => <option key={application.id} value={application.id}>{application.job.title} · {application.job.company}</option>)}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-2 h-4 w-4 text-muted" />
              </div>
            )}
            <span className={cn(
              "ml-auto hidden items-center gap-1.5 text-[10px] font-semibold sm:inline-flex",
              connectionStatus === "connected" && "text-success",
              ["connecting", "reconnecting"].includes(connectionStatus) && "text-amber-400",
              connectionStatus === "disconnected" && "text-red-400",
              connectionStatus === "idle" && "text-muted",
            )}>
              <span className={cn(
                "h-1.5 w-1.5 rounded-full",
                connectionStatus === "connected" && "bg-success",
                ["connecting", "reconnecting"].includes(connectionStatus) && "animate-pulse bg-amber-400",
                connectionStatus === "disconnected" && "bg-red-400",
                connectionStatus === "idle" && "bg-muted",
              )} /> {connectionLabel}
            </span>
          </div>

          <div className="job-scroll min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5 2xl:px-7 2xl:py-6">
            {!activeThread?.messages.length ? (
              <div className="mx-auto flex min-h-full max-w-[720px] flex-col justify-center py-4">
                <div className="text-center">
                  <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl border border-accent/30 bg-accent/10 text-accent">
                    <Bot className="h-6 w-6" />
                  </span>
                  <h2 className="mt-3 text-xl font-bold text-white 2xl:text-2xl">What are we working on?</h2>
                  <p className="mx-auto mt-1.5 max-w-[540px] text-xs leading-5 text-muted 2xl:text-sm">I use your selected profile, vacancy, or application to make every answer specific and evidence-based.</p>
                </div>
                <div className="mt-5 grid gap-2 sm:grid-cols-2 2xl:mt-6 2xl:gap-3">
                  {quickActions.map((action) => (
                    <button key={action.title} type="button" onClick={() => submitMessage(action.prompt)} className="group rounded-lg border border-border bg-white/[0.025] p-3 text-left transition hover:border-accent/40 hover:bg-accent/[0.07] 2xl:p-4">
                      <span className="grid h-8 w-8 place-items-center rounded-md bg-accent/12 text-accent transition group-hover:bg-accent/20"><action.icon className="h-4 w-4" /></span>
                      <p className="mt-2.5 text-sm font-bold text-white">{action.title}</p>
                      <p className="mt-1 text-[11px] leading-4 text-muted 2xl:text-xs">{action.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-[760px] space-y-5">
                {activeThread.messages.map((message) => (
                  <article key={message.id} className={cn("flex gap-2.5 sm:gap-3", message.role === "user" && "justify-end")}>
                    {message.role === "assistant" && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-accent/15 text-accent"><Bot className="h-4 w-4" /></span>}
                    <div className={cn("min-w-0 max-w-[88%]", message.role === "user" && "rounded-xl rounded-tr-sm bg-accent px-3.5 py-2.5 text-white shadow-[0_8px_24px_rgba(255,90,0,0.14)]")}>
                      {message.role === "assistant" && (
                        <p className="mb-1.5 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.1em] text-accent">
                          Tasko Assistant
                          {message.source && (
                            <span className={cn(
                              "rounded border px-1.5 py-0.5 text-[8px] tracking-[0.08em]",
                              message.source === "openclaw"
                                ? "border-success/35 bg-success/10 text-success"
                                : "border-border bg-white/[0.035] text-muted",
                            )}>
                              {message.source === "openclaw" ? "OpenClaw" : "Local fallback"}
                            </span>
                          )}
                        </p>
                      )}
                      <p className={cn("whitespace-pre-wrap text-[13px] leading-5 2xl:text-sm 2xl:leading-6", message.role === "assistant" ? "text-[#e4e9f1]" : "text-white")}>
                        {message.content}
                        {message.id === streamingMessageId && message.content && <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-accent align-middle" />}
                        {message.id === streamingMessageId && !message.content && (
                          <span className="flex gap-1 py-1">
                            <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted" />
                            <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted [animation-delay:120ms]" />
                            <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted [animation-delay:240ms]" />
                          </span>
                        )}
                      </p>
                      {message.role === "assistant" && message.id !== streamingMessageId && message.content && (
                        <div className="mt-2.5 flex items-center gap-1.5 border-t border-border pt-2">
                          <Button variant="ghost" size="sm" onClick={() => copyMessage(message)} className="h-7 px-2 text-[10px] text-muted hover:text-white">
                            {copiedMessageId === message.id ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />} {copiedMessageId === message.id ? "Copied" : "Copy"}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => regenerateMessage(message.id)} className="h-7 px-2 text-[10px] text-muted hover:text-white">
                            <RefreshCw className="h-3.5 w-3.5" /> Regenerate
                          </Button>
                        </div>
                      )}
                    </div>
                    {message.role === "user" && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white/[0.08] text-[#dfe4ec]"><UserRound className="h-4 w-4" /></span>}
                  </article>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="shrink-0 border-t border-border p-3 2xl:p-4">
            <div className="mx-auto max-w-[780px] rounded-lg border border-border bg-white/[0.035] p-2 shadow-[0_12px_34px_rgba(0,0,0,0.18)] focus-within:border-accent/60">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submitMessage();
                  }
                }}
                rows={2}
                placeholder="Ask anything about your job search…"
                className="max-h-32 min-h-[42px] w-full resize-none bg-transparent px-2 py-1 text-[13px] leading-5 text-white outline-none placeholder:text-muted 2xl:text-sm"
              />
              <div className="flex items-center justify-between gap-2 px-1">
                <p className="truncate text-[10px] text-muted">Using: {contextLabel}</p>
                {isGenerating ? (
                  <Button onClick={stopGenerating} aria-label="Stop generating" className="h-8 rounded-md border border-red-400/30 bg-red-500/10 px-2.5 text-[10px] font-bold text-red-300 hover:bg-red-500/20">
                    <Square className="h-3 w-3 fill-current" /> Stop generating
                  </Button>
                ) : (
                  <Button onClick={() => submitMessage()} disabled={!draft.trim()} aria-label="Send message" className="h-8 w-8 rounded-md bg-accent p-0 text-white hover:bg-[#ff6b12] disabled:opacity-40">
                    <Send className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            <p className="mt-1.5 text-center text-[9px] text-muted">Tasko may make mistakes. Verify generated claims before using them.</p>
          </div>
        </main>

        <aside className="panel hidden min-h-0 overflow-y-auto xl:block">
          <div className="border-b border-border p-3.5 2xl:p-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Active context</p>
            <div className="mt-3 rounded-lg border border-accent/25 bg-accent/[0.07] p-3">
              <span className="grid h-8 w-8 place-items-center rounded-md bg-accent/16 text-accent">
                {contextKind === "profile" ? <UserRound className="h-4 w-4" /> : contextKind === "job" ? <BriefcaseBusiness className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
              </span>
              <p className="mt-2.5 text-sm font-bold leading-5 text-white">{contextLabel}</p>
              {selectedJob && <p className="mt-1 text-[11px] text-muted">{selectedJob.location} · {selectedJob.match}% match</p>}
              {selectedApplication && <span className="mt-2 inline-flex rounded-md border border-border bg-white/[0.04] px-2 py-1 text-[10px] font-bold capitalize text-[#dfe4ec]">{selectedApplication.status}</span>}
            </div>
          </div>

          <div className="border-b border-border p-3.5 2xl:p-4">
            <p className="text-xs font-bold text-white">Sources available</p>
            <div className="mt-3 space-y-2.5">
              {[
                { label: "Candidate profile", ready: Boolean(profile.name || profile.current_role || profile.skills) },
                { label: "Resume", ready: Boolean(profile.resume_file_name) },
                { label: "Vacancy details", ready: Boolean(selectedJob) },
                { label: "Application notes", ready: Boolean(selectedApplication?.notes) },
              ].map((source) => (
                <div key={source.label} className="flex items-center gap-2 text-[11px]">
                  <span className={cn("grid h-4 w-4 place-items-center rounded-full border", source.ready ? "border-success/40 bg-success/12 text-success" : "border-border text-muted")}>
                    {source.ready ? <Check className="h-2.5 w-2.5" /> : <span className="h-1 w-1 rounded-full bg-current" />}
                  </span>
                  <span className={source.ready ? "text-[#dfe4ec]" : "text-muted"}>{source.label}</span>
                  <span className="ml-auto text-[9px] font-bold uppercase text-muted">{source.ready ? "Ready" : "Missing"}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3.5 2xl:p-4">
            <p className="text-xs font-bold text-white">How Tasko uses context</p>
            <p className="mt-2 text-[11px] leading-5 text-muted">Answers are grounded in the selected data. Missing evidence is called out instead of being invented.</p>
            {selectedJob?.skills.length ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {selectedJob.skills.slice(0, 6).map((skill) => <span key={skill} className="rounded-md border border-border bg-white/[0.035] px-2 py-1 text-[10px] text-[#cfd5df]">{skill}</span>)}
              </div>
            ) : null}
          </div>
        </aside>
      </div>
    </section>
  );
}
