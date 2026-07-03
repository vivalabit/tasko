"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Bookmark,
  BriefcaseBusiness,
  Bot,
  Calendar,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Command,
  ExternalLink,
  FileText,
  Heart,
  Home,
  Mail,
  MoreHorizontal,
  Plus,
  Info,
  RotateCcw,
  Save,
  Search,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Star,
  Settings,
  Target,
  Trash2,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Job = {
  id: string;
  company: string;
  title: string;
  location: string;
  type: string;
  salary: string;
  posted: string;
  experience: string;
  department: string;
  match: number;
  logo: "stripe" | "figma" | "linkedin";
  overview: string;
  responsibilities: string[];
  requirements: string[];
  skills: string[];
  salaryAverage: string;
  salaryMin: string;
  salaryMax: string;
  recommendations: { text: string; gain: string }[];
  companyInfo: string;
  reviews: string[];
  similarJobs: string[];
};

type ParsedJob = {
  title?: string | null;
  company?: string | null;
  location?: string | null;
  url?: string | null;
  apply_url?: string | null;
  posted_at?: string | null;
  employment_type?: string | null;
  seniority?: string | null;
  description?: string | null;
};

type ParserApiResponse = {
  status: "completed" | "queued" | "running";
  jobs?: ParsedJob[];
  snapshot_id?: string | null;
  message?: string | null;
};

type ParserSearchForm = {
  keywords: string;
  location: string;
  remote: string;
  experienceLevel: string;
  jobType: string;
  datePosted: string;
  resultsLimit: string;
  country: string;
  deduplicate: boolean;
  searchName: string;
  folder: string;
};

type ParserSearchConfig = {
  id: string;
  name: string;
  form: ParserSearchForm;
  updatedAt: string;
};

const jobs: Job[] = [
  {
    id: "stripe-senior-product-designer",
    company: "Stripe",
    title: "Senior Product Designer",
    location: "Remote",
    type: "Full-time",
    salary: "$120k - $160k",
    posted: "2h ago",
    experience: "5+ years",
    department: "Product Design",
    match: 92,
    logo: "stripe",
    overview:
      "We're looking for a Senior Product Designer to join our team and help design the future of online payments. You'll work on complex problems that impact millions of businesses worldwide.",
    responsibilities: [
      "Lead design projects from concept to execution",
      "Collaborate with cross-functional teams",
      "Design user-centered solutions for complex problems",
      "Mentor junior designers",
    ],
    requirements: [
      "5+ years of product design experience",
      "Strong portfolio demonstrating design thinking",
      "Experience with design systems",
      "Excellent communication skills",
    ],
    skills: ["Figma", "Sketch", "Design Systems", "User Research", "Prototyping"],
    salaryAverage: "$140k",
    salaryMin: "$120k",
    salaryMax: "$160k",
    recommendations: [
      { text: "Add more case studies", gain: "+5% match" },
      { text: "Highlight design system experience", gain: "+3% match" },
      { text: "Add metrics to your portfolio", gain: "+2% match" },
    ],
    companyInfo:
      "Stripe builds financial infrastructure for internet businesses, with design teams focused on developer tools, dashboards, and payment experiences.",
    reviews: [
      "Design quality bar is high and feedback cycles are direct.",
      "Strong product culture with close engineering collaboration.",
    ],
    similarJobs: ["Staff Product Designer at Square", "Design Systems Lead at Ramp", "Senior UX Designer at Shopify"],
  },
  {
    id: "figma-product-design-lead",
    company: "Figma",
    title: "Product Design Lead",
    location: "Remote",
    type: "Full-time",
    salary: "$130k - $170k",
    posted: "5h ago",
    experience: "6+ years",
    department: "Editor Experience",
    match: 89,
    logo: "figma",
    overview:
      "Figma is hiring a Product Design Lead to shape collaborative creation workflows for designers, engineers, and product teams. This role owns strategy, craft, and team rituals for high-impact editor surfaces.",
    responsibilities: [
      "Define the product design direction for core collaboration flows",
      "Partner with research, product, and engineering leads",
      "Prototype new interaction models",
      "Coach designers through critiques and launches",
    ],
    requirements: [
      "6+ years designing creative or productivity tools",
      "Experience leading ambiguous product initiatives",
      "Strong systems thinking and interaction design craft",
      "Comfort presenting design rationale to leadership",
    ],
    skills: ["Figma", "Prototyping", "Design Strategy", "Research", "Collaboration"],
    salaryAverage: "$150k",
    salaryMin: "$130k",
    salaryMax: "$170k",
    recommendations: [
      { text: "Show examples of design leadership", gain: "+4% match" },
      { text: "Add collaboration tooling case studies", gain: "+3% match" },
      { text: "Mention facilitation experience", gain: "+2% match" },
    ],
    companyInfo:
      "Figma creates collaborative design and product development software used by teams to ideate, design, prototype, and ship together.",
    reviews: [
      "Fast-moving product teams with thoughtful design critique.",
      "Strong remote culture and high ownership expectations.",
    ],
    similarJobs: ["Principal Product Designer at Miro", "Design Lead at Linear", "Senior Product Designer at Webflow"],
  },
];

const filters = ["Location", "Remote", "Salary", "Experience", "Job Type", "AI Match"];
const tabs = ["Overview", "Company", "AI Match", "Reviews", "Similar Jobs"];
type View = "Dashboard" | "Jobs";
type ParserSearchStatus = "idle" | "loading" | "ready" | "error";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const snapshotPollDelayMs = 4000;
const snapshotPollMaxAttempts = 30;
const parserSearchConfigsStorageKey = "tasko.parserSearchConfigs.v1";
const parserSearchConfigsLocalUrl = "/parser-search-configs.local.json";

const defaultParserSearchForm: ParserSearchForm = {
  keywords: "",
  location: "",
  remote: "Any",
  experienceLevel: "Any",
  jobType: "Any",
  datePosted: "Any time",
  resultsLimit: "100",
  country: "Any",
  deduplicate: true,
  searchName: "",
  folder: "",
};

const navItems: Array<{ label: string; icon: typeof Home; href: string; view?: View }> = [
  { label: "Dashboard", icon: Home, href: "#dashboard", view: "Dashboard" },
  { label: "Jobs", icon: BriefcaseBusiness, href: "#jobs", view: "Jobs" },
  { label: "Applications", icon: Mail, href: "#" },
  { label: "AI Assistant", icon: Sparkles, href: "#" },
];

const stats = [
  {
    label: "Applications",
    value: "24",
    note: "Total applied",
    delta: "20%",
    icon: FileText,
    color: "orange",
    chart: "M0,42 C22,42 26,36 42,38 C58,40 62,28 78,32 C95,36 101,18 120,24 C137,30 144,16 160,20 C178,25 187,11 205,17 C221,22 231,5 250,10",
  },
  {
    label: "Interviews",
    value: "5",
    note: "Upcoming",
    delta: "25%",
    icon: CalendarDays,
    color: "orange",
    chart: "M0,42 C24,43 33,36 49,39 C66,42 75,33 92,35 C112,38 121,17 138,18 C157,19 158,36 178,34 C196,31 203,12 221,13 C236,14 238,24 250,21",
  },
  {
    label: "Offers",
    value: "2",
    note: "Received",
    delta: "100%",
    icon: BriefcaseBusiness,
    color: "green",
    chart: "M0,42 C19,42 24,31 40,34 C59,37 66,32 82,38 C101,45 110,23 130,28 C150,32 160,25 178,30 C196,35 200,4 216,13 C232,22 238,31 250,24",
  },
  {
    label: "Match Score",
    value: "78%",
    note: "Average",
    delta: "12%",
    icon: Target,
    color: "orange",
    progress: true,
  },
];

const overview = [
  { label: "Applied", value: "12 (50%)", color: "bg-[#ff5a00]" },
  { label: "Interview", value: "5 (21%)", color: "bg-[#ff9f1a]" },
  { label: "Assessment", value: "3 (13%)", color: "bg-[#2f80ed]" },
  { label: "Offer", value: "2 (8%)", color: "bg-[#4a9d35]" },
  { label: "Rejected", value: "2 (8%)", color: "bg-[#d94d4d]" },
];

function getViewFromHash(): View {
  if (typeof window === "undefined") {
    return "Dashboard";
  }

  return window.location.hash === "#jobs" ? "Jobs" : "Dashboard";
}

function createParsedJobId(job: ParsedJob, index: number) {
  const source = job.url || `${job.title ?? "linkedin-job"}-${job.company ?? "company"}-${job.location ?? "location"}-${index}`;
  return `linkedin-${source.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 96)}`;
}

function mapParsedJobToJob(job: ParsedJob, index: number): Job {
  const title = job.title?.trim() || "LinkedIn vacancy";
  const company = job.company?.trim() || "LinkedIn";
  const location = job.location?.trim() || "Not specified";
  const type = job.employment_type?.trim() || "Not specified";
  const experience = job.seniority?.trim() || "Not specified";
  const overview = job.description?.trim() || "Imported from LinkedIn via Bright Data. Open the source vacancy to review the full description and apply details.";

  return {
    id: createParsedJobId(job, index),
    company,
    title,
    location,
    type,
    salary: "Not specified",
    posted: job.posted_at?.trim() || "LinkedIn",
    experience,
    department: "LinkedIn import",
    match: 72,
    logo: "linkedin",
    overview,
    responsibilities: ["Review the LinkedIn vacancy details", "Compare requirements with your profile", "Decide whether to save or apply"],
    requirements: [experience, type, location].filter((item) => item !== "Not specified"),
    skills: ["LinkedIn", "Imported"],
    salaryAverage: "N/A",
    salaryMin: "N/A",
    salaryMax: "N/A",
    recommendations: [
      { text: "Open the original LinkedIn posting", gain: "source" },
      { text: "Check the company and role requirements", gain: "review" },
      { text: "Save strong matches before applying", gain: "workflow" },
    ],
    companyInfo: `${company} vacancy imported from LinkedIn${job.url ? `: ${job.url}` : "."}`,
    reviews: ["This vacancy was imported automatically and has not been reviewed yet."],
    similarJobs: [],
  };
}

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function createClientId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeParserSearchConfigs(configs: ParserSearchConfig[]) {
  const normalizedConfigs = configs
    .filter((config) => config.id && config.name && config.form)
    .map((config) => ({
      ...config,
      form: { ...defaultParserSearchForm, ...config.form },
    }));
  const uniqueConfigs = new Map<string, ParserSearchConfig>();

  for (const config of normalizedConfigs) {
    uniqueConfigs.set(config.id, config);
  }

  return Array.from(uniqueConfigs.values());
}

export default function HomePage() {
  const [activeView, setActiveView] = useState<View>("Dashboard");
  const [jobList, setJobList] = useState<Job[]>(jobs);
  const [selectedJobId, setSelectedJobId] = useState(jobs[0].id);
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [savedJobs, setSavedJobs] = useState<string[]>([]);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("Best Match");
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [isParserDialogOpen, setIsParserDialogOpen] = useState(false);
  const [parserSearchStatus, setParserSearchStatus] = useState<ParserSearchStatus>("idle");
  const [parserSearchMessage, setParserSearchMessage] = useState("");
  const [parserSearchForm, setParserSearchForm] = useState<ParserSearchForm>(defaultParserSearchForm);
  const [parserSearchConfigs, setParserSearchConfigs] = useState<ParserSearchConfig[]>([]);
  const [selectedParserSearchConfigId, setSelectedParserSearchConfigId] = useState("");
  const [isParserSearchConfigsLoaded, setIsParserSearchConfigsLoaded] = useState(false);

  const filteredJobs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const results = normalizedQuery
      ? jobList.filter((job) =>
          [job.title, job.company, job.location, job.type, job.salary].some((value) =>
            value.toLowerCase().includes(normalizedQuery),
          ),
        )
      : jobList;

    return [...results].sort((a, b) => {
      if (sortBy === "Newest") return a.posted.localeCompare(b.posted);
      if (sortBy === "Salary") {
        const aSalary = Number.parseInt(a.salaryAverage.replace(/\D/g, ""), 10) || 0;
        const bSalary = Number.parseInt(b.salaryAverage.replace(/\D/g, ""), 10) || 0;
        return bSalary - aSalary;
      }
      return b.match - a.match;
    });
  }, [jobList, query, sortBy]);

  const selectedJob = filteredJobs.find((job) => job.id === selectedJobId) ?? filteredJobs[0] ?? jobList[0];
  const isSelectedSaved = savedJobs.includes(selectedJob.id);

  useEffect(() => {
    const syncViewFromHash = () => {
      setActiveView(getViewFromHash());
    };

    syncViewFromHash();
    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadParserSearchConfigs() {
      const configs: ParserSearchConfig[] = [];

      try {
        const rawConfigs = window.localStorage.getItem(parserSearchConfigsStorageKey);
        if (rawConfigs) {
          const parsedConfigs = JSON.parse(rawConfigs) as ParserSearchConfig[];
          if (Array.isArray(parsedConfigs)) {
            configs.push(...parsedConfigs);
          }
        }
      } catch {
        configs.length = 0;
      }

      try {
        const response = await fetch(parserSearchConfigsLocalUrl, { cache: "no-store" });
        if (response.ok) {
          const localConfigs = (await response.json()) as ParserSearchConfig[];
          if (Array.isArray(localConfigs)) {
            configs.push(...localConfigs);
          }
        }
      } catch {
        // Local config file is optional.
      }

      if (!isMounted) return;

      setParserSearchConfigs(normalizeParserSearchConfigs(configs));
      setIsParserSearchConfigsLoaded(true);
    }

    loadParserSearchConfigs();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!isParserSearchConfigsLoaded) return;

    window.localStorage.setItem(parserSearchConfigsStorageKey, JSON.stringify(parserSearchConfigs));
  }, [isParserSearchConfigsLoaded, parserSearchConfigs]);

  function changeView(view: View) {
    setActiveView(view);
    window.history.replaceState(null, "", view === "Jobs" ? "#jobs" : "#dashboard");
  }

  function toggleSaved(jobId: string) {
    setSavedJobs((current) => (current.includes(jobId) ? current.filter((id) => id !== jobId) : [...current, jobId]));
  }

  function toggleFilter(filter: string) {
    setActiveFilters((current) => (current.includes(filter) ? current.filter((item) => item !== filter) : [...current, filter]));
  }

  function updateParserSearchForm<Field extends keyof typeof parserSearchForm>(
    field: Field,
    value: (typeof parserSearchForm)[Field],
  ) {
    setParserSearchForm((current) => ({ ...current, [field]: value }));
    setParserSearchStatus("idle");
    setParserSearchMessage("");
  }

  function saveParserSearchConfig() {
    const configName = parserSearchForm.searchName.trim();
    if (!configName) {
      setParserSearchStatus("error");
      setParserSearchMessage("Enter a config name before saving");
      return;
    }

    const updatedAt = new Date().toISOString();
    const formToSave = { ...parserSearchForm, searchName: configName };
    const configId = selectedParserSearchConfigId || createClientId("parser-config");

    setParserSearchConfigs((currentConfigs) => {
      const configExists = currentConfigs.some((config) => config.id === configId);
      const nextConfig: ParserSearchConfig = {
        id: configId,
        name: configName,
        form: formToSave,
        updatedAt,
      };

      if (configExists) {
        return currentConfigs.map((config) => (config.id === configId ? nextConfig : config));
      }

      return [nextConfig, ...currentConfigs];
    });
    setSelectedParserSearchConfigId(configId);
    setParserSearchForm(formToSave);
    setParserSearchStatus("ready");
    setParserSearchMessage(`Saved config: ${configName}`);
  }

  function loadParserSearchConfig(configId: string) {
    const config = parserSearchConfigs.find((item) => item.id === configId);
    setSelectedParserSearchConfigId(configId);

    if (!config) return;

    setParserSearchForm({ ...defaultParserSearchForm, ...config.form, searchName: config.name });
    setParserSearchStatus("ready");
    setParserSearchMessage(`Loaded config: ${config.name}`);
  }

  function deleteParserSearchConfig() {
    if (!selectedParserSearchConfigId) return;

    const deletedConfig = parserSearchConfigs.find((config) => config.id === selectedParserSearchConfigId);
    setParserSearchConfigs((currentConfigs) => currentConfigs.filter((config) => config.id !== selectedParserSearchConfigId));
    setSelectedParserSearchConfigId("");
    setParserSearchStatus("ready");
    setParserSearchMessage(deletedConfig ? `Deleted config: ${deletedConfig.name}` : "Deleted config");
  }

  function addParsedJobsToList(parsedJobs: ParsedJob[]) {
    const importedJobs = parsedJobs.map((job, index) => mapParsedJobToJob(job, index));

    if (importedJobs.length > 0) {
      setJobList((currentJobs) => {
        const importedIds = new Set(importedJobs.map((job) => job.id));
        return [...importedJobs, ...currentJobs.filter((job) => !importedIds.has(job.id))];
      });
      setSelectedJobId(importedJobs[0].id);
      setActiveTab("Overview");
    }

    return importedJobs.length;
  }

  async function pollLinkedInSnapshot(snapshotId: string): Promise<ParserApiResponse> {
    for (let attempt = 1; attempt <= snapshotPollMaxAttempts; attempt += 1) {
      setParserSearchMessage(`Bright Data snapshot queued. Checking ${attempt}/${snapshotPollMaxAttempts}...`);
      await wait(snapshotPollDelayMs);

      const snapshotResponse = await fetch(
        `${apiBaseUrl}/parsers/linkedin/snapshots/${encodeURIComponent(snapshotId)}?results_limit=${Number.parseInt(parserSearchForm.resultsLimit, 10) || 100}&deduplicate=${parserSearchForm.deduplicate}`,
      );
      const snapshotData = (await snapshotResponse.json()) as ParserApiResponse & { detail?: string };

      if (!snapshotResponse.ok) {
        throw new Error(snapshotData.detail ?? "LinkedIn snapshot request failed");
      }

      if (snapshotData.status === "completed") {
        return snapshotData;
      }
    }

    throw new Error("Bright Data snapshot is still not ready. Try again later.");
  }

  async function runParsers() {
    setParserSearchStatus("loading");
    setParserSearchMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/parsers/linkedin/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keywords: parserSearchForm.keywords,
          location: parserSearchForm.location,
          remote: parserSearchForm.remote,
          experience_level: parserSearchForm.experienceLevel,
          job_type: parserSearchForm.jobType,
          date_posted: parserSearchForm.datePosted,
          results_limit: Number.parseInt(parserSearchForm.resultsLimit, 10) || 100,
          country: parserSearchForm.country,
          deduplicate: parserSearchForm.deduplicate,
          search_name: parserSearchForm.searchName,
          folder: parserSearchForm.folder,
        }),
      });
      const data = (await response.json()) as ParserApiResponse & { detail?: string };

      if (!response.ok) {
        throw new Error(data.detail ?? "LinkedIn parser request failed");
      }

      const finalData =
        data.status === "completed"
          ? data
          : data.snapshot_id
            ? await pollLinkedInSnapshot(data.snapshot_id)
            : data;
      const addedCount = finalData.status === "completed" ? addParsedJobsToList(finalData.jobs ?? []) : 0;

      setParserSearchStatus("ready");
      setParserSearchMessage(
        finalData.status === "completed"
          ? `Added ${addedCount} LinkedIn vacancies to Jobs`
          : `Bright Data snapshot queued: ${finalData.snapshot_id ?? data.snapshot_id ?? "waiting"}`,
      );
    } catch (error) {
      setParserSearchStatus("error");
      setParserSearchMessage(error instanceof Error ? error.message : "LinkedIn parser request failed");
    }
  }

  return (
    <main className="h-screen overflow-hidden bg-background text-foreground">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_16%_8%,rgba(255,90,0,0.12),transparent_26%),radial-gradient(circle_at_80%_0%,rgba(52,120,246,0.10),transparent_28%)]" />
      <div className="relative mx-auto flex h-full max-w-[1536px] overflow-hidden rounded-none border-border bg-[#0a0f15]/96 shadow-panel lg:rounded-[14px] lg:border">
        <AppSidebar activeView={activeView} onChangeView={changeView} />

        {activeView === "Dashboard" ? (
          <DashboardView onOpenJobs={() => changeView("Jobs")} />
        ) : (
        <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden px-3 py-3 sm:px-4 xl:px-4 2xl:px-5 2xl:py-4">
        <header className="grid shrink-0 gap-3 xl:grid-cols-[112px_minmax(260px,520px)_1fr] 2xl:grid-cols-[140px_minmax(280px,560px)_1fr] xl:items-center">
          <h1 className="text-[24px] font-bold leading-tight tracking-normal text-white sm:text-[27px] 2xl:text-[31px]">Jobs</h1>

          <label className="flex h-10 min-w-0 items-center gap-2.5 rounded-md border border-border bg-white/[0.075] px-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] focus-within:border-accent/70 2xl:h-12 2xl:px-4">
            <Search className="h-[18px] w-[18px] shrink-0 text-muted 2xl:h-5 2xl:w-5" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search jobs..."
              className="h-full min-w-0 flex-1 bg-transparent text-[13px] font-medium text-white outline-none placeholder:text-muted 2xl:text-sm"
            />
          </label>

          <div className="flex flex-wrap gap-2 xl:justify-end">
            <Button
              className="h-10 rounded-md border border-[#9f7aea]/60 bg-[#7c3aed] px-4 text-[13px] text-white shadow-[0_12px_28px_rgba(124,58,237,0.28)] hover:bg-[#8b5cf6] 2xl:h-12 2xl:px-5 2xl:text-sm"
              onClick={() => {
                setParserSearchStatus("idle");
                setParserSearchMessage("");
                setIsParserDialogOpen(true);
              }}
            >
              <Search className="h-[18px] w-[18px] 2xl:h-5 2xl:w-5" />
              Search vacancies
            </Button>
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-white/[0.03] px-4 text-[13px] text-[#e6ebf3] hover:bg-white/[0.075] 2xl:h-12 2xl:px-5 2xl:text-sm"
              onClick={() => setActiveTab("Overview")}
            >
              <Heart className={cn("h-[18px] w-[18px] 2xl:h-5 2xl:w-5", savedJobs.length > 0 && "fill-accent text-accent")} />
              Saved Jobs
            </Button>
            <Button
              variant="ghost"
              className={cn(
                "h-10 rounded-md border border-border bg-white/[0.03] px-4 text-[13px] text-[#e6ebf3] hover:bg-white/[0.075] 2xl:h-12 2xl:px-5 2xl:text-sm",
                alertsEnabled && "border-accent/70 text-white",
              )}
              onClick={() => setAlertsEnabled((enabled) => !enabled)}
            >
              <Bell className="h-[18px] w-[18px] 2xl:h-5 2xl:w-5" />
              Job Alerts
            </Button>
          </div>
        </header>

        <div className="mt-4 flex shrink-0 flex-col gap-2.5 lg:flex-row lg:items-center lg:justify-between 2xl:mt-5 2xl:gap-3">
          <div className="flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => toggleFilter(filter)}
                className={cn(
                  "inline-flex h-9 items-center gap-2 rounded-md border border-transparent bg-white/[0.055] px-3 text-[13px] font-semibold text-[#d8dee8] transition hover:bg-white/[0.09] 2xl:h-10 2xl:px-4 2xl:text-sm",
                  activeFilters.includes(filter) && "border-accent/70 bg-accent/15 text-white",
                )}
              >
                {filter}
                <ChevronDown className="h-3.5 w-3.5 text-muted 2xl:h-4 2xl:w-4" />
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setActiveFilters([]);
                setSortBy("Best Match");
              }}
              className="inline-flex h-9 items-center rounded-md border border-border bg-white/[0.09] px-4 text-[13px] font-semibold text-[#d8dee8] transition hover:bg-white/[0.13] 2xl:h-10 2xl:px-5 2xl:text-sm"
            >
              Reset
            </button>
          </div>

          <button
            type="button"
            onClick={() => setSortBy((current) => (current === "Best Match" ? "Newest" : current === "Newest" ? "Salary" : "Best Match"))}
            className="inline-flex h-9 w-fit items-center gap-2 whitespace-nowrap rounded-md bg-white/[0.045] px-3 text-[13px] font-semibold text-[#d8dee8] transition hover:bg-white/[0.08] 2xl:h-10 2xl:px-4 2xl:text-sm"
          >
            <SlidersHorizontal className="h-3.5 w-3.5 text-muted 2xl:h-4 2xl:w-4" />
            Sort by: {sortBy}
            <ChevronDown className="h-3.5 w-3.5 text-muted 2xl:h-4 2xl:w-4" />
          </button>
        </div>

        <div className="mt-3 grid min-h-0 flex-1 gap-3 xl:grid-cols-[350px_minmax(0,1fr)] 2xl:mt-4 2xl:grid-cols-[420px_minmax(0,1fr)] 2xl:gap-4">
          <aside className="flex min-h-0 flex-col overflow-hidden rounded-md bg-white/[0.02]">
            <p className="shrink-0 px-1 pb-3 pt-3 text-sm font-semibold text-muted 2xl:pb-4 2xl:pt-5 2xl:text-base">{filteredJobs.length} jobs found</p>
            <div className="job-scroll min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 2xl:space-y-3">
              {filteredJobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => {
                    setSelectedJobId(job.id);
                    setActiveTab("Overview");
                  }}
                  className={cn(
                    "grid w-full grid-cols-[46px_minmax(0,1fr)_78px_22px] items-center gap-3 rounded-md border p-3 text-left transition 2xl:grid-cols-[58px_minmax(0,1fr)_96px_26px] 2xl:p-4",
                    selectedJob.id === job.id
                      ? "border-accent bg-white/[0.055] shadow-[0_0_0_1px_rgba(255,90,0,0.12)]"
                      : "border-transparent bg-white/[0.035] hover:border-white/[0.13] hover:bg-white/[0.055]",
                  )}
                >
                  <CompanyLogo logo={job.logo} />
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-bold text-white 2xl:text-base">{job.title}</h2>
                    <p className="mt-0.5 text-xs font-semibold text-[#cdd4df] 2xl:mt-1 2xl:text-sm">{job.company}</p>
                    <p className="mt-0.5 text-xs text-muted 2xl:mt-1 2xl:text-sm">
                      {job.location} <span className="text-white/30">•</span> {job.type}
                    </p>
                    <p className="mt-1.5 text-xs text-muted 2xl:mt-2 2xl:text-sm">
                      {job.salary} <span className="mx-2 text-white/15">|</span> {job.posted}
                    </p>
                  </div>
                  <p className="justify-self-end whitespace-nowrap text-xs font-bold text-success 2xl:text-sm">{job.match}% match</p>
                  <Bookmark
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleSaved(job.id);
                    }}
                    className={cn("h-[18px] w-[18px] justify-self-end text-muted 2xl:h-5 2xl:w-5", savedJobs.includes(job.id) && "fill-accent text-accent")}
                  />
                </button>
              ))}
            </div>
          </aside>

          <section className="panel job-scroll min-h-0 overflow-y-auto p-3 md:p-4 2xl:p-5">
            <div className="grid gap-4 lg:grid-cols-[1fr_170px] 2xl:gap-5 2xl:grid-cols-[1fr_188px]">
              <div className="flex min-w-0 items-start gap-3 2xl:gap-4">
                <CompanyLogo logo={selectedJob.logo} large />
                <div className="min-w-0 pt-0.5">
                  <h2 className="text-[22px] font-bold leading-tight text-white md:text-[24px] 2xl:text-[29px]">{selectedJob.title}</h2>
                  <p className="mt-1.5 text-sm font-semibold text-muted 2xl:mt-2 2xl:text-base">
                    {selectedJob.company} <span className="text-white/35">•</span> {selectedJob.location} <span className="text-white/35">•</span> {selectedJob.type}
                  </p>
                  <p className="mt-2 text-sm font-semibold text-muted 2xl:mt-3 2xl:text-base">{selectedJob.salary}</p>
                </div>
              </div>

              <div className="grid gap-2">
                <Button className="h-9 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] text-[13px] 2xl:h-10 2xl:text-sm">
                  <ExternalLink className="h-4 w-4" />
                  Apply Now
                </Button>
                <Button
                  variant="ghost"
                  className="h-9 rounded-md border border-border bg-transparent text-[13px] text-[#e6ebf3] hover:bg-white/[0.06] 2xl:h-10 2xl:text-sm"
                  onClick={() => toggleSaved(selectedJob.id)}
                >
                  <Heart className={cn("h-[18px] w-[18px] 2xl:h-5 2xl:w-5", isSelectedSaved && "fill-accent text-accent")} />
                  {isSelectedSaved ? "Saved" : "Save Job"}
                </Button>
                <Button
                  variant="ghost"
                  className="h-9 rounded-md border border-border bg-transparent text-[13px] text-[#e6ebf3] hover:bg-white/[0.06] 2xl:h-10 2xl:text-sm"
                  onClick={() => navigator.clipboard?.writeText(`${selectedJob.title} at ${selectedJob.company}`)}
                >
                  <Share2 className="h-[18px] w-[18px] 2xl:h-5 2xl:w-5" />
                  Share Job
                </Button>
              </div>
            </div>

            <div className="mt-5 flex gap-2 overflow-x-auto border-b border-border 2xl:mt-7 2xl:gap-4">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "relative h-10 min-w-fit px-4 text-[13px] font-bold text-muted transition hover:text-white 2xl:h-11 2xl:px-5 2xl:text-sm",
                    activeTab === tab && "text-white after:absolute after:bottom-[-1px] after:left-0 after:h-0.5 after:w-full after:bg-accent",
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="mt-4 grid gap-3 min-[1800px]:grid-cols-[minmax(0,1.12fr)_minmax(320px,0.9fr)] 2xl:mt-5 2xl:gap-4">
              <div className="grid gap-3 2xl:gap-4">
                <JobMainPanel job={selectedJob} tab={activeTab} />
                <SalaryInsights job={selectedJob} />
              </div>

              <div className="grid content-start gap-3 2xl:gap-4">
                <MatchPanel job={selectedJob} />
                <RecommendationsPanel job={selectedJob} />
                <JobDetails job={selectedJob} />
              </div>
            </div>
          </section>
        </div>

        {isParserDialogOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
            <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[940px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
              <div className="flex shrink-0 items-start justify-between gap-4">
                <div>
                  <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">Search vacancies</h2>
                  <p className="mt-1 text-sm font-medium text-muted">Choose parser and configure search settings</p>
                </div>
                <button
                  type="button"
                  aria-label="Close parser settings"
                  onClick={() => setIsParserDialogOpen(false)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border">
                <div className="grid min-h-0 lg:grid-cols-[334px_minmax(0,1fr)] lg:items-start">
                  <section className="border-b border-border p-4 lg:self-start lg:border-b-0 2xl:p-5">
                    <h3 className="text-sm font-bold text-white">1. Choose parser</h3>
                    <div className="mt-4 rounded-md border border-accent bg-white/[0.035] p-3 shadow-[0_0_0_1px_rgba(255,90,0,0.18)]">
                      <div className="flex items-center gap-3">
                        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[#0a66c2] text-lg font-black text-white">in</div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-white">LinkedIn</h4>
                            <span className="rounded bg-success/18 px-2 py-0.5 text-[11px] font-bold text-success">Recommended</span>
                          </div>
                          <p className="mt-1 text-xs font-medium text-muted">Extract jobs from LinkedIn</p>
                        </div>
                        <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full border-2 border-accent">
                          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        </span>
                      </div>
                    </div>
                  </section>

                  <section className="p-4 lg:border-l lg:border-border 2xl:p-5">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-bold text-white">2. Configure parser settings</h3>
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 text-xs font-bold text-muted transition hover:text-white"
                        onClick={() => {
                          setParserSearchForm(defaultParserSearchForm);
                          setSelectedParserSearchConfigId("");
                          setParserSearchStatus("idle");
                          setParserSearchMessage("");
                        }}
                      >
                        <RotateCcw className="h-4 w-4" />
                        Reset to defaults
                      </button>
                    </div>

                    <div className="mt-4 grid gap-4">
                      <label className="grid gap-2">
                        <span className="text-xs font-bold text-[#d8dee8]">Job title or keywords</span>
                        <input
                          value={parserSearchForm.keywords}
                          onChange={(event) => updateParserSearchForm("keywords", event.target.value)}
                          placeholder="e.g. Product Designer, UX Designer, Design System"
                          className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
                        />
                        <span className="text-xs font-medium text-muted">Use keywords to find relevant vacancies</span>
                      </label>

                      <div className="grid gap-4 md:grid-cols-2">
                        <label className="grid gap-2">
                          <span className="text-xs font-bold text-[#d8dee8]">Location</span>
                          <input
                            value={parserSearchForm.location}
                            onChange={(event) => updateParserSearchForm("location", event.target.value)}
                            placeholder="e.g. Remote, United States, Europe"
                            className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
                          />
                          <span className="text-xs font-medium text-muted">Leave empty to search worldwide</span>
                        </label>

                        <label className="grid gap-2">
                          <span className="text-xs font-bold text-[#d8dee8]">Remote</span>
                          <select
                            value={parserSearchForm.remote}
                            onChange={(event) => updateParserSearchForm("remote", event.target.value)}
                            className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                          >
                            <option>Any</option>
                            <option>Remote only</option>
                            <option>Hybrid</option>
                            <option>On-site</option>
                          </select>
                          <span className="text-xs font-medium text-muted">Filter by remote work options</span>
                        </label>

                        <label className="grid gap-2">
                          <span className="text-xs font-bold text-[#d8dee8]">Experience level</span>
                          <select
                            value={parserSearchForm.experienceLevel}
                            onChange={(event) => updateParserSearchForm("experienceLevel", event.target.value)}
                            className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                          >
                            <option>Any</option>
                            <option>Entry level</option>
                            <option>Associate</option>
                            <option>Mid-Senior level</option>
                            <option>Director</option>
                          </select>
                          <span className="text-xs font-medium text-muted">Filter by experience level</span>
                        </label>

                        <label className="grid gap-2">
                          <span className="text-xs font-bold text-[#d8dee8]">Job type</span>
                          <select
                            value={parserSearchForm.jobType}
                            onChange={(event) => updateParserSearchForm("jobType", event.target.value)}
                            className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                          >
                            <option>Any</option>
                            <option>Full-time</option>
                            <option>Part-time</option>
                            <option>Contract</option>
                            <option>Internship</option>
                          </select>
                          <span className="text-xs font-medium text-muted">Full-time, Part-time, Contract, etc.</span>
                        </label>

                        <label className="grid gap-2">
                          <span className="text-xs font-bold text-[#d8dee8]">Date posted</span>
                          <select
                            value={parserSearchForm.datePosted}
                            onChange={(event) => updateParserSearchForm("datePosted", event.target.value)}
                            className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                          >
                            <option>Any time</option>
                            <option>Past 24 hours</option>
                            <option>Past week</option>
                            <option>Past month</option>
                          </select>
                          <span className="text-xs font-medium text-muted">Filter by job posting date</span>
                        </label>
                      </div>

                      <div className="rounded-md border border-border bg-white/[0.018] p-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-bold text-white">Additional settings</h4>
                          <ChevronDown className="h-4 w-4 rotate-180 text-muted" />
                        </div>
                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                          <label className="grid gap-2">
                            <span className="text-xs font-bold text-[#d8dee8]">Results limit</span>
                            <input
                              type="number"
                              min="1"
                              max="1000"
                              value={parserSearchForm.resultsLimit}
                              onChange={(event) => updateParserSearchForm("resultsLimit", event.target.value)}
                              className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                            />
                            <span className="text-xs font-medium text-muted">Maximum number of vacancies to fetch (max 1000)</span>
                          </label>

                          <label className="grid gap-2">
                            <span className="text-xs font-bold text-[#d8dee8]">Country</span>
                            <select
                              value={parserSearchForm.country}
                              onChange={(event) => updateParserSearchForm("country", event.target.value)}
                              className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                            >
                              <option>Any</option>
                              <option>United States</option>
                              <option>United Kingdom</option>
                              <option>Germany</option>
                              <option>Switzerland</option>
                            </select>
                            <span className="text-xs font-medium text-muted">Filter by country</span>
                          </label>
                        </div>

                        <div className="mt-4 flex items-start gap-3">
                          <button
                            type="button"
                            aria-label="Deduplicate results"
                            onClick={() => updateParserSearchForm("deduplicate", !parserSearchForm.deduplicate)}
                            className={cn(
                              "relative mt-0.5 h-5 w-9 rounded-full transition",
                              parserSearchForm.deduplicate ? "bg-accent shadow-[0_0_14px_rgba(255,90,0,0.22)]" : "bg-white/15",
                            )}
                          >
                            <span className={cn("absolute top-0.5 h-4 w-4 rounded-full bg-white transition", parserSearchForm.deduplicate ? "right-0.5" : "left-0.5")} />
                          </button>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-bold text-white">Deduplicate results</p>
                              <Info className="h-3.5 w-3.5 text-muted" />
                            </div>
                            <p className="mt-1 text-xs font-medium text-muted">Remove duplicate vacancies</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </section>
                </div>

                <section className="border-t border-border p-4 2xl:p-5">
                  <h3 className="text-sm font-bold text-white">3. Search configs</h3>
                  <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_320px]">
                    <label className="grid gap-2 md:col-span-2">
                      <span className="text-xs font-bold text-[#d8dee8]">Existing configs</span>
                      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                        <select
                          value={selectedParserSearchConfigId}
                          onChange={(event) => loadParserSearchConfig(event.target.value)}
                          className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-muted outline-none focus:border-accent/70"
                        >
                          <option value="">Select saved config</option>
                          {parserSearchConfigs.map((config) => (
                            <option key={config.id} value={config.id}>
                              {config.name}
                            </option>
                          ))}
                        </select>
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-9 rounded-md border border-border bg-transparent px-3 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
                          disabled={!selectedParserSearchConfigId}
                          onClick={deleteParserSearchConfig}
                        >
                          <Trash2 className="h-4 w-4" />
                          Delete
                        </Button>
                      </div>
                      <span className="text-xs font-medium text-muted">Saved locally in this browser, outside git</span>
                    </label>

                    <label className="grid gap-2">
                      <span className="text-xs font-bold text-[#d8dee8]">Config name</span>
                      <input
                        value={parserSearchForm.searchName}
                        onChange={(event) => updateParserSearchForm("searchName", event.target.value)}
                        placeholder="e.g. Product Designer Remote Jobs"
                        className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
                      />
                      <span className="text-xs font-medium text-muted">Name current settings to run them again later</span>
                    </label>

                    <label className="grid gap-2">
                      <span className="text-xs font-bold text-[#d8dee8]">Save to folder</span>
                      <select
                        value={parserSearchForm.folder}
                        onChange={(event) => updateParserSearchForm("folder", event.target.value)}
                        className="h-9 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-muted outline-none focus:border-accent/70"
                      >
                        <option value="">Select folder (optional)</option>
                        <option>Design roles</option>
                        <option>Remote jobs</option>
                        <option>High match</option>
                      </select>
                    </label>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-9 rounded-md border border-accent/55 bg-accent/12 px-4 text-[13px] text-white hover:bg-accent/18"
                      onClick={saveParserSearchConfig}
                    >
                      <Save className="h-4 w-4" />
                      Save config
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-9 rounded-md border border-border bg-transparent px-4 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
                      onClick={() => {
                        setParserSearchForm(defaultParserSearchForm);
                        setSelectedParserSearchConfigId("");
                        setParserSearchStatus("idle");
                        setParserSearchMessage("");
                      }}
                    >
                      New config
                    </Button>
                  </div>
                </section>
              </div>

              <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm font-semibold text-muted">
                  Parser: <span className="text-white">LinkedIn</span>
                  {parserSearchMessage && (
                    <span className={cn("ml-2", parserSearchStatus === "error" ? "text-[#ff7a7a]" : "text-accent")}>
                      {parserSearchMessage}
                    </span>
                  )}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
                    onClick={() => setIsParserDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
                    disabled={parserSearchStatus === "loading"}
                    onClick={runParsers}
                  >
                    <Search className="h-4 w-4" />
                    {parserSearchStatus === "loading" ? "Searching..." : "Start search"}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
      )}
      </div>
    </main>
  );
}

function DashboardView({ onOpenJobs }: { onOpenJobs: () => void }) {
  return (
    <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden px-3 py-3 sm:px-4 xl:px-4 2xl:px-5 2xl:py-4">
      <header className="mb-3 flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between 2xl:mb-4 2xl:gap-4">
        <div>
          <h1 className="text-[24px] font-bold leading-tight tracking-normal text-white sm:text-[27px] 2xl:text-[31px]">
            Good morning, Alex!
          </h1>
          <p className="mt-1 text-[13px] text-muted 2xl:mt-1.5 2xl:text-base">Let's find the right opportunity for you today.</p>
        </div>
        <Button
          size="lg"
          className="h-10 w-full justify-center rounded-md bg-gradient-to-r from-[#ff5a00] to-[#dd3d00] text-[13px] md:w-auto 2xl:h-11 2xl:text-sm"
          onClick={onOpenJobs}
        >
          <Plus className="h-4 w-4 2xl:h-5 2xl:w-5" />
          New Search
          <span className="ml-1.5 inline-flex items-center gap-1 rounded-md bg-white/10 px-2 py-1 text-[11px] 2xl:ml-2 2xl:text-xs">
            <Command className="h-3 w-3" /> K
          </span>
        </Button>
      </header>

      <div className="grid shrink-0 gap-2.5 sm:grid-cols-2 xl:grid-cols-4 2xl:gap-3">
        {stats.map((stat) => (
          <article key={stat.label} className="panel min-h-[118px] p-3 2xl:min-h-[142px] 2xl:p-4">
            <div className="mb-2 flex items-start gap-2.5 2xl:gap-3">
              <div
                className={cn(
                  "grid h-9 w-9 shrink-0 place-items-center rounded-md 2xl:h-11 2xl:w-11",
                  stat.color === "green" ? "bg-success/20 text-success" : "bg-accent/20 text-accent",
                )}
              >
                <stat.icon className="h-5 w-5 2xl:h-6 2xl:w-6" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-[#d6dbe4] 2xl:text-sm">{stat.label}</p>
                <p className="mt-0.5 text-[24px] font-bold leading-none 2xl:mt-1 2xl:text-[28px]">{stat.value}</p>
                <p className="mt-0.5 text-xs text-muted 2xl:mt-1 2xl:text-sm">{stat.note}</p>
              </div>
              <MoreHorizontal className="h-4 w-4 text-muted" />
            </div>
            {stat.progress ? (
              <div className="mt-4 h-2 rounded-full bg-white/[0.06] 2xl:mt-5">
                <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-[#ff5a00] to-[#ff7a1a]" />
              </div>
            ) : (
              <svg viewBox="0 0 250 54" className="h-8 w-full 2xl:h-10" aria-hidden="true">
                <path d={stat.chart} fill="none" stroke={stat.color === "green" ? "#58d532" : "#ff5a00"} strokeWidth="2.4" />
                <path d={`${stat.chart} L250,54 L0,54 Z`} fill={stat.color === "green" ? "rgba(88,213,50,0.10)" : "rgba(255,90,0,0.10)"} />
              </svg>
            )}
            <p className="mt-2 text-xs text-muted 2xl:mt-3 2xl:text-sm">
              <span className="mr-2 font-bold text-success">up {stat.delta}</span>vs last 30 days
            </p>
          </article>
        ))}
      </div>

      <div className="mt-2.5 grid min-h-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.95fr)] 2xl:mt-3 2xl:gap-3">
        <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_92px] gap-2.5 2xl:grid-rows-[minmax(0,1fr)_100px] 2xl:gap-3">
          <section className="panel flex min-h-0 flex-col overflow-hidden p-3 2xl:p-4">
            <div className="mb-2.5 flex items-center justify-between 2xl:mb-3">
              <div className="flex items-center gap-2.5 2xl:gap-3">
                <Star className="h-4 w-4 text-accent 2xl:h-5 2xl:w-5" />
                <h2 className="text-base font-bold 2xl:text-lg">Recommended Jobs</h2>
              </div>
              <button className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent 2xl:gap-2 2xl:text-sm" onClick={onOpenJobs}>
                View all jobs <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
              {jobs.map((job) => (
                <button
                  key={job.id}
                  className="grid min-h-[56px] w-full grid-cols-[46px_minmax(0,1fr)_86px_24px] items-center gap-2.5 border-b border-border px-3 py-2 text-left last:border-0 2xl:min-h-[64px] 2xl:grid-cols-[58px_minmax(0,1fr)_104px_28px] 2xl:gap-3"
                  onClick={onOpenJobs}
                >
                  <CompanyLogo logo={job.logo} />
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold 2xl:text-base">{job.title}</h3>
                    <p className="text-xs text-muted">{job.company}</p>
                    <div className="mt-1 flex gap-2">
                      <span className="tag">Remote</span>
                      <span className="tag">Full-time</span>
                    </div>
                  </div>
                  <div className="hidden text-left sm:block">
                    <p className="text-xs font-semibold text-success 2xl:text-sm">{job.match}% match</p>
                    <p className="mt-0.5 text-xs text-muted 2xl:mt-1">{job.posted}</p>
                  </div>
                  <Bookmark className="h-[18px] w-[18px] text-muted 2xl:h-5 2xl:w-5" />
                </button>
              ))}
            </div>
          </section>

          <section className="panel p-2.5 2xl:p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2.5 2xl:gap-3">
                <Calendar className="h-4 w-4 text-muted" />
                <h2 className="text-sm font-bold 2xl:text-base">Upcoming Interviews</h2>
              </div>
              <a className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent 2xl:gap-2 2xl:text-sm" href="#">
                View all <ChevronRight className="h-4 w-4" />
              </a>
            </div>
            <div className="grid gap-2 rounded-md border border-border px-3 py-2 sm:grid-cols-[42px_1fr_120px_auto_18px] sm:items-center 2xl:grid-cols-[48px_1fr_132px_auto_18px]">
              <div className="text-center">
                <p className="text-[11px] font-bold uppercase text-accent 2xl:text-xs">May</p>
                <p className="text-lg font-bold leading-tight 2xl:text-xl">24</p>
                <p className="text-[11px] text-accent 2xl:text-xs">Fri</p>
              </div>
              <div className="flex items-center gap-2.5 2xl:gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-full bg-white text-lg font-bold text-[#4285f4] 2xl:h-9 2xl:w-9 2xl:text-xl">G</div>
                <div>
                  <p className="text-sm font-semibold">Google</p>
                  <p className="text-xs text-muted">Senior Product Designer</p>
                </div>
              </div>
              <div className="space-y-1 text-[11px] text-muted 2xl:text-xs">
                <p className="flex items-center gap-1.5 2xl:gap-2"><Calendar className="h-3.5 w-3.5 2xl:h-4 2xl:w-4" /> May 24, 2024</p>
                <p className="flex items-center gap-1.5 2xl:gap-2"><CircleDot className="h-3.5 w-3.5 2xl:h-4 2xl:w-4" /> 10:00 AM</p>
              </div>
              <Button variant="outline" size="sm" className="h-7 px-2 text-[11px]">Video Interview</Button>
              <MoreHorizontal className="hidden h-5 w-5 text-muted sm:block" />
            </div>
          </section>
        </div>

        <aside className="grid min-h-0 grid-rows-[minmax(0,1fr)_158px] gap-2.5 2xl:grid-rows-[minmax(0,1fr)_172px] 2xl:gap-3">
          <section className="panel p-3 2xl:p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-bold 2xl:text-lg">Application Overview</h2>
              <Button variant="ghost" size="sm" className="h-7 border border-border px-2 text-[11px] 2xl:text-xs">Last 30 days</Button>
            </div>
            <div className="grid items-center gap-3 sm:grid-cols-[124px_1fr] 2xl:grid-cols-[150px_minmax(0,1fr)] 2xl:gap-4">
              <div className="overview-ring relative mx-auto h-[118px] w-[118px] rounded-full 2xl:h-[138px] 2xl:w-[138px]">
                <div className="absolute inset-[30px] grid place-items-center rounded-full bg-[#131920] 2xl:inset-[34px]">
                  <p className="text-center text-xl font-bold 2xl:text-2xl">24<br /><span className="text-[11px] font-normal text-muted 2xl:text-xs">Total</span></p>
                </div>
              </div>
              <div className="space-y-2.5 2xl:space-y-3">
                {overview.map((item) => (
                  <div key={item.label} className="flex items-center gap-2.5 text-[13px] 2xl:gap-3 2xl:text-sm">
                    <span className={cn("h-3 w-3 rounded-full 2xl:h-3.5 2xl:w-3.5", item.color)} />
                    <span className="flex-1 text-muted">{item.label}</span>
                    <span className="text-[#cbd2dd]">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
            <a className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent 2xl:gap-2 2xl:text-sm" href="#">
              View full report <ChevronRight className="h-4 w-4" />
            </a>
          </section>

          <section className="panel p-2.5 2xl:p-3">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-bold 2xl:text-base">AI Assistant</h2>
              <Button variant="outline" size="sm" className="h-7 px-2 text-[11px]">New Chat</Button>
            </div>
            <div className="rounded-md border border-border p-2.5">
              <div className="grid gap-2 sm:grid-cols-[30px_1fr] 2xl:sm:grid-cols-[34px_1fr]">
                <div className="grid h-8 w-8 place-items-center rounded-full bg-accent/20 text-accent">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="space-y-1 text-[11px] leading-tight text-muted">
                  <p>Hi Alex! I can help you with:</p>
                  <div className="grid grid-cols-2 gap-x-2.5 gap-y-1 2xl:gap-x-3">
                    {["Resume optimization", "Cover letter writing", "Interview preparation", "Job search strategy"].map((item) => (
                      <p key={item} className="flex items-center gap-1.5"><Check className="h-3 w-3 text-accent" /> {item}</p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <Button className="mt-2 h-8 w-full rounded-md bg-gradient-to-r from-[#ff5a00] to-[#e63e00] text-xs">
              Start a conversation <Sparkles className="ml-auto h-5 w-5" />
            </Button>
          </section>
        </aside>
      </div>
    </section>
  );
}

function AppSidebar({ activeView, onChangeView }: { activeView: View; onChangeView: (view: View) => void }) {
  return (
    <aside className="app-sidebar hidden h-screen w-[190px] shrink-0 overflow-y-auto border-r border-border bg-white/[0.025] px-2.5 py-4 lg:flex lg:flex-col 2xl:w-[220px] 2xl:px-3 2xl:py-5">
      <div className="app-sidebar-brand mb-5 flex items-center gap-2.5 px-2 2xl:mb-7 2xl:gap-3">
        <img
          src="/brand/tasko-mark.png"
          alt=""
          className="app-sidebar-mark h-8 w-8 object-contain 2xl:h-10 2xl:w-9"
          aria-hidden="true"
        />
        <div className="min-w-0">
          <p className="bg-gradient-to-b from-[#ff8a1f] to-[#ff4d00] bg-clip-text text-[19px] font-black leading-none text-transparent 2xl:text-[22px]">
            tasko
          </p>
          <p className="mt-0.5 text-[11px] text-muted 2xl:mt-1 2xl:text-xs">AI Career Assistant</p>
        </div>
      </div>

      <nav className="app-sidebar-nav space-y-1.5 2xl:space-y-2">
        {navItems.map((item) => (
          <a
            href={item.href}
            key={item.label}
            onClick={() => {
              if (item.view) {
                onChangeView(item.view);
              }
            }}
            className={cn(
              "app-sidebar-nav-item group flex h-10 w-full items-center gap-2.5 rounded-md px-3 text-left text-[14px] text-[#d9dee7] transition 2xl:h-11 2xl:gap-3 2xl:px-4 2xl:text-[15px]",
              item.view === activeView
                ? "border border-white/[0.12] bg-white/10 text-white shadow-[inset_4px_0_0_#ff5a00]"
                : item.view
                  ? "hover:bg-white/[0.055] hover:text-white"
                  : "cursor-default opacity-70",
            )}
          >
            <item.icon className="h-[18px] w-[18px] 2xl:h-5 2xl:w-5" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      <div className="app-sidebar-footer mt-auto border-t border-border pt-3 2xl:pt-4">
        <div className="app-sidebar-profile mb-2 flex items-center gap-2.5 rounded-md px-2 py-2 2xl:mb-3 2xl:gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-full bg-white text-[11px] font-bold text-slate-900 2xl:h-10 2xl:w-10 2xl:text-xs">
            AJ
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium 2xl:text-base">Alex Johnson</p>
            <p className="text-xs text-muted 2xl:text-sm">Product Designer</p>
          </div>
          <ChevronRight className="h-[18px] w-[18px] text-muted 2xl:h-5 2xl:w-5" />
        </div>
        <a
          href="#"
          className="app-sidebar-settings flex h-10 items-center gap-2.5 rounded-md px-3 text-sm text-muted hover:bg-white/[0.055] hover:text-white 2xl:h-11 2xl:gap-3 2xl:text-base"
        >
          <Settings className="h-[18px] w-[18px] 2xl:h-5 2xl:w-5" />
          <span>Settings</span>
          <ChevronRight className="ml-auto h-[18px] w-[18px] 2xl:h-5 2xl:w-5" />
        </a>
      </div>
    </aside>
  );
}

function JobMainPanel({ job, tab }: { job: Job; tab: string }) {
  if (tab === "Company") {
    return (
      <article className="panel p-3 2xl:p-4">
        <h3 className="text-base font-bold 2xl:text-lg">Company</h3>
        <p className="mt-3 text-[13px] leading-5 text-muted 2xl:mt-4 2xl:text-sm 2xl:leading-6">{job.companyInfo}</p>
        <div className="mt-4 grid gap-2.5 sm:grid-cols-3 2xl:mt-5 2xl:gap-3">
          <InfoStat label="Team" value={job.department} />
          <InfoStat label="Location" value={job.location} />
          <InfoStat label="Role" value={job.type} />
        </div>
      </article>
    );
  }

  if (tab === "AI Match") {
    return (
      <article className="panel p-3 2xl:p-4">
        <h3 className="text-base font-bold 2xl:text-lg">AI Match Analysis</h3>
        <p className="mt-3 text-[13px] leading-5 text-muted 2xl:mt-4 2xl:text-sm 2xl:leading-6">
          Your profile is a strong fit for this role because the portfolio signals, seniority, and product design keywords align with the job description.
        </p>
        <div className="mt-4 space-y-2.5 2xl:mt-5 2xl:space-y-3">
          {["Portfolio relevance", "Experience level", "Skill alignment", "Culture fit"].map((item, index) => (
            <div key={item} className="flex items-center gap-3">
              <div className="h-2 flex-1 rounded-full bg-white/[0.08]">
                <div className="h-full rounded-full bg-success" style={{ width: `${job.match - index * 5}%` }} />
              </div>
              <span className="w-32 text-[13px] text-muted 2xl:w-36 2xl:text-sm">{item}</span>
            </div>
          ))}
        </div>
      </article>
    );
  }

  if (tab === "Reviews") {
    return (
      <article className="panel p-3 2xl:p-4">
        <h3 className="text-base font-bold 2xl:text-lg">Reviews</h3>
        <div className="mt-3 space-y-2.5 2xl:mt-4 2xl:space-y-3">
          {job.reviews.map((review) => (
            <p key={review} className="rounded-md border border-border bg-white/[0.025] p-3 text-[13px] leading-5 text-muted 2xl:text-sm 2xl:leading-6">
              {review}
            </p>
          ))}
        </div>
      </article>
    );
  }

  if (tab === "Similar Jobs") {
    return (
      <article className="panel p-3 2xl:p-4">
        <h3 className="text-base font-bold 2xl:text-lg">Similar Jobs</h3>
        <div className="mt-3 space-y-2.5 2xl:mt-4 2xl:space-y-3">
          {job.similarJobs.map((similarJob) => (
            <div key={similarJob} className="flex items-center justify-between rounded-md border border-border bg-white/[0.025] p-3">
              <p className="text-[13px] font-semibold text-[#d8dee8] 2xl:text-sm">{similarJob}</p>
              <ChevronDown className="h-4 w-4 -rotate-90 text-muted" />
            </div>
          ))}
        </div>
      </article>
    );
  }

  return (
    <article className="panel p-3 2xl:p-4">
      <h3 className="text-base font-bold 2xl:text-lg">Job Description</h3>
      <p className="mt-3 text-[13px] leading-5 text-muted 2xl:mt-4 2xl:text-sm 2xl:leading-6">{job.overview}</p>

      <h4 className="mt-5 text-sm font-bold 2xl:mt-7 2xl:text-base">Key Responsibilities</h4>
      <ul className="mt-2.5 space-y-1.5 text-[13px] leading-5 text-muted 2xl:mt-3 2xl:space-y-2 2xl:text-sm">
        {job.responsibilities.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted" />
            {item}
          </li>
        ))}
      </ul>

      <h4 className="mt-5 text-sm font-bold 2xl:mt-7 2xl:text-base">Requirements</h4>
      <ul className="mt-2.5 space-y-1.5 text-[13px] leading-5 text-muted 2xl:mt-3 2xl:space-y-2 2xl:text-sm">
        {job.requirements.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted" />
            {item}
          </li>
        ))}
      </ul>

      <div className="mt-5 flex flex-wrap gap-2 2xl:mt-7">
        {job.skills.map((skill) => (
          <span key={skill} className="tag font-semibold">
            {skill}
          </span>
        ))}
      </div>
    </article>
  );
}

function MatchPanel({ job }: { job: Job }) {
  return (
    <article className="panel p-4 2xl:p-5">
      <h3 className="text-base font-bold 2xl:text-lg">AI Match Score</h3>
      <p className="mt-3 text-[34px] font-bold leading-none text-success 2xl:mt-4 2xl:text-[40px]">{job.match}%</p>
      <div className="mt-2.5 h-2 rounded-full bg-white/[0.09] 2xl:mt-3">
        <div className="h-full rounded-full bg-success" style={{ width: `${job.match}%` }} />
      </div>
      <h4 className="mt-5 text-[13px] font-bold 2xl:mt-7 2xl:text-sm">Why this match?</h4>
      <ul className="mt-2.5 space-y-1.5 text-[13px] text-muted 2xl:mt-3 2xl:space-y-2 2xl:text-sm">
        {["Strong portfolio match", "Relevant experience", "Skills alignment", "Company culture fit"].map((item) => (
          <li key={item} className="flex items-center gap-2">
            <Check className="h-4 w-4 text-success" />
            {item}
          </li>
        ))}
      </ul>
      <a className="mt-4 inline-flex items-center gap-2 text-[13px] font-bold text-accent 2xl:mt-5 2xl:text-sm" href="#">
        Review full analysis <span aria-hidden="true">-&gt;</span>
      </a>
    </article>
  );
}

function RecommendationsPanel({ job }: { job: Job }) {
  return (
    <article className="panel p-4 2xl:p-5">
      <h3 className="text-base font-bold 2xl:text-lg">AI Recommendations</h3>
      <div className="mt-3 divide-y divide-border">
        {job.recommendations.map((recommendation) => (
          <div key={recommendation.text} className="flex items-center justify-between gap-4 py-2 text-[13px] 2xl:py-2.5 2xl:text-sm">
            <p className="text-muted">{recommendation.text}</p>
            <p className="shrink-0 font-bold text-success">{recommendation.gain}</p>
          </div>
        ))}
      </div>
      <a className="mt-3 inline-flex items-center gap-2 text-[13px] font-bold text-accent 2xl:text-sm" href="#">
        View all recommendations <span aria-hidden="true">-&gt;</span>
      </a>
    </article>
  );
}

function SalaryInsights({ job }: { job: Job }) {
  return (
    <article className="panel p-3 2xl:p-4">
      <h3 className="text-base font-bold 2xl:text-lg">Salary Insights</h3>
      <p className="mt-4 text-[26px] font-bold leading-none 2xl:mt-6 2xl:text-[30px]">{job.salaryAverage}</p>
      <p className="mt-1.5 text-[13px] text-muted 2xl:mt-2 2xl:text-sm">Average total compensation</p>
      <div className="mt-6 2xl:mt-8">
        <div className="relative h-2 rounded-full bg-white/[0.10]">
          <div className="absolute left-0 top-0 h-full w-1/2 rounded-full bg-accent" />
          <span className="absolute left-1/2 top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent" />
        </div>
        <div className="mt-3 flex justify-between text-[13px] font-semibold text-muted 2xl:mt-4 2xl:text-sm">
          <span>{job.salaryMin}</span>
          <span>{job.salaryAverage}</span>
          <span>{job.salaryMax}</span>
        </div>
      </div>
    </article>
  );
}

function JobDetails({ job }: { job: Job }) {
  const details = [
    ["Posted", job.posted.replace("h", " hours").replace("d", " days")],
    ["Job Type", job.type],
    ["Experience", job.experience],
    ["Location", job.location],
    ["Department", job.department],
  ];

  return (
    <article className="panel p-4 2xl:p-5">
      <h3 className="text-base font-bold 2xl:text-lg">Job Details</h3>
      <dl className="mt-4 space-y-2.5 2xl:mt-5 2xl:space-y-3">
        {details.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[112px_1fr] gap-3 text-[13px] 2xl:grid-cols-[130px_1fr] 2xl:gap-4 2xl:text-sm">
            <dt className="text-muted">{label}</dt>
            <dd className="font-semibold text-[#d8dee8]">{value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function InfoStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-white/[0.025] p-2.5 2xl:p-3">
      <p className="text-xs font-semibold uppercase text-muted">{label}</p>
      <p className="mt-1.5 text-[13px] font-bold text-white 2xl:mt-2 2xl:text-sm">{value}</p>
    </div>
  );
}

function CompanyLogo({ logo, large = false }: { logo: Job["logo"]; large?: boolean }) {
  const sizeClass = large ? "h-16 w-16 2xl:h-[88px] 2xl:w-[88px]" : "h-11 w-11 2xl:h-14 2xl:w-14";

  if (logo === "linkedin") {
    return (
      <div className={cn("grid shrink-0 place-items-center rounded-md bg-[#0a66c2] font-black text-white", large ? "text-2xl 2xl:text-3xl" : "text-lg 2xl:text-xl", sizeClass)}>
        in
      </div>
    );
  }

  if (logo === "figma") {
    return (
      <div className={cn("grid shrink-0 place-items-center rounded-md bg-black", sizeClass)}>
        <div className={cn("grid grid-cols-2", large ? "scale-125 2xl:scale-150" : "scale-90 2xl:scale-100")}>
          <span className="h-4 w-4 rounded-l-full bg-[#ff7262]" />
          <span className="h-4 w-4 rounded-r-full bg-[#f24e1e]" />
          <span className="h-4 w-4 rounded-l-full bg-[#a259ff]" />
          <span className="h-4 w-4 rounded-r-full bg-[#1abcfe]" />
          <span className="h-4 w-4 rounded-full bg-[#0acf83]" />
        </div>
      </div>
    );
  }

  return (
    <div className={cn("grid shrink-0 place-items-center rounded-md bg-black font-black text-white", large ? "text-xl 2xl:text-2xl" : "text-base 2xl:text-xl", sizeClass)}>
      stripe
    </div>
  );
}
