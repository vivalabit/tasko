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
  Search,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Star,
  Settings,
  Target,
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
  logo: "stripe" | "figma";
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

export default function HomePage() {
  const [activeView, setActiveView] = useState<View>("Dashboard");
  const [selectedJobId, setSelectedJobId] = useState(jobs[0].id);
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [savedJobs, setSavedJobs] = useState<string[]>([]);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("Best Match");
  const [alertsEnabled, setAlertsEnabled] = useState(false);

  const filteredJobs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const results = normalizedQuery
      ? jobs.filter((job) =>
          [job.title, job.company, job.location, job.type, job.salary].some((value) =>
            value.toLowerCase().includes(normalizedQuery),
          ),
        )
      : jobs;

    return [...results].sort((a, b) => {
      if (sortBy === "Newest") return a.posted.localeCompare(b.posted);
      if (sortBy === "Salary") return Number.parseInt(b.salaryAverage.replace(/\D/g, ""), 10) - Number.parseInt(a.salaryAverage.replace(/\D/g, ""), 10);
      return b.match - a.match;
    });
  }, [query, sortBy]);

  const selectedJob = filteredJobs.find((job) => job.id === selectedJobId) ?? filteredJobs[0] ?? jobs[0];
  const isSelectedSaved = savedJobs.includes(selectedJob.id);

  useEffect(() => {
    const syncViewFromHash = () => {
      setActiveView(getViewFromHash());
    };

    syncViewFromHash();
    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

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
