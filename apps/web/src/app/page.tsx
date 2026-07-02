"use client";

import { useMemo, useState } from "react";
import {
  Bell,
  Bookmark,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Heart,
  Home,
  Mail,
  Search,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Settings,
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
const navItems = [
  { label: "Dashboard", icon: Home },
  { label: "Jobs", icon: BriefcaseBusiness, active: true },
  { label: "Applications", icon: Mail },
  { label: "AI Assistant", icon: Sparkles },
];

export default function HomePage() {
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

  function toggleSaved(jobId: string) {
    setSavedJobs((current) => (current.includes(jobId) ? current.filter((id) => id !== jobId) : [...current, jobId]));
  }

  function toggleFilter(filter: string) {
    setActiveFilters((current) => (current.includes(filter) ? current.filter((item) => item !== filter) : [...current, filter]));
  }

  return (
    <main className="h-screen overflow-hidden bg-background text-foreground">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_16%_8%,rgba(255,90,0,0.12),transparent_26%),radial-gradient(circle_at_80%_0%,rgba(52,120,246,0.10),transparent_28%)]" />
      <div className="relative mx-auto flex h-full max-w-[1536px] overflow-hidden rounded-none border-border bg-[#0a0f15]/96 shadow-panel lg:rounded-[18px] lg:border">
        <AppSidebar />

        <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden px-4 py-4 sm:px-5 xl:px-5">
        <header className="grid shrink-0 gap-4 xl:grid-cols-[150px_minmax(280px,560px)_1fr] xl:items-center">
          <h1 className="text-[27px] font-bold leading-tight tracking-normal text-white sm:text-[31px]">Jobs</h1>

          <label className="flex h-12 min-w-0 items-center gap-3 rounded-md border border-border bg-white/[0.075] px-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] focus-within:border-accent/70">
            <Search className="h-5 w-5 shrink-0 text-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search jobs..."
              className="h-full min-w-0 flex-1 bg-transparent text-sm font-medium text-white outline-none placeholder:text-muted"
            />
          </label>

          <div className="flex flex-wrap gap-2 xl:justify-end">
            <Button
              variant="ghost"
              className="h-12 rounded-md border border-border bg-white/[0.03] px-5 text-[#e6ebf3] hover:bg-white/[0.075]"
              onClick={() => setActiveTab("Overview")}
            >
              <Heart className={cn("h-5 w-5", savedJobs.length > 0 && "fill-accent text-accent")} />
              Saved Jobs
            </Button>
            <Button
              variant="ghost"
              className={cn(
                "h-12 rounded-md border border-border bg-white/[0.03] px-5 text-[#e6ebf3] hover:bg-white/[0.075]",
                alertsEnabled && "border-accent/70 text-white",
              )}
              onClick={() => setAlertsEnabled((enabled) => !enabled)}
            >
              <Bell className="h-5 w-5" />
              Job Alerts
            </Button>
          </div>
        </header>

        <div className="mt-5 flex shrink-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2.5">
            {filters.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => toggleFilter(filter)}
                className={cn(
                  "inline-flex h-10 items-center gap-2 rounded-md border border-transparent bg-white/[0.055] px-4 text-sm font-semibold text-[#d8dee8] transition hover:bg-white/[0.09]",
                  activeFilters.includes(filter) && "border-accent/70 bg-accent/15 text-white",
                )}
              >
                {filter}
                <ChevronDown className="h-4 w-4 text-muted" />
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setActiveFilters([]);
                setSortBy("Best Match");
              }}
              className="inline-flex h-10 items-center rounded-md border border-border bg-white/[0.09] px-5 text-sm font-semibold text-[#d8dee8] transition hover:bg-white/[0.13]"
            >
              Reset
            </button>
          </div>

          <button
            type="button"
            onClick={() => setSortBy((current) => (current === "Best Match" ? "Newest" : current === "Newest" ? "Salary" : "Best Match"))}
            className="inline-flex h-10 w-fit items-center gap-2 whitespace-nowrap rounded-md bg-white/[0.045] px-4 text-sm font-semibold text-[#d8dee8] transition hover:bg-white/[0.08]"
          >
            <SlidersHorizontal className="h-4 w-4 text-muted" />
            Sort by: {sortBy}
            <ChevronDown className="h-4 w-4 text-muted" />
          </button>
        </div>

        <div className="mt-4 grid min-h-0 flex-1 gap-4 xl:grid-cols-[390px_minmax(0,1fr)] 2xl:grid-cols-[440px_minmax(0,1fr)]">
          <aside className="flex min-h-0 flex-col overflow-hidden rounded-md bg-white/[0.02]">
            <p className="shrink-0 px-1 pb-4 pt-5 text-base font-semibold text-muted">{filteredJobs.length} jobs found</p>
            <div className="job-scroll min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
              {filteredJobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => {
                    setSelectedJobId(job.id);
                    setActiveTab("Overview");
                  }}
                  className={cn(
                    "grid w-full grid-cols-[56px_minmax(0,1fr)_88px_24px] items-center gap-3 rounded-md border p-4 text-left transition 2xl:grid-cols-[62px_minmax(0,1fr)_104px_28px] 2xl:gap-4",
                    selectedJob.id === job.id
                      ? "border-accent bg-white/[0.055] shadow-[0_0_0_1px_rgba(255,90,0,0.12)]"
                      : "border-transparent bg-white/[0.035] hover:border-white/[0.13] hover:bg-white/[0.055]",
                  )}
                >
                  <CompanyLogo logo={job.logo} />
                  <div className="min-w-0">
                    <h2 className="truncate text-base font-bold text-white">{job.title}</h2>
                    <p className="mt-1 text-sm font-semibold text-[#cdd4df]">{job.company}</p>
                    <p className="mt-1 text-sm text-muted">
                      {job.location} <span className="text-white/30">•</span> {job.type}
                    </p>
                    <p className="mt-2 text-sm text-muted">
                      {job.salary} <span className="mx-2 text-white/15">|</span> {job.posted}
                    </p>
                  </div>
                  <p className="justify-self-end whitespace-nowrap text-sm font-bold text-success">{job.match}% match</p>
                  <Bookmark
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleSaved(job.id);
                    }}
                    className={cn("h-5 w-5 justify-self-end text-muted", savedJobs.includes(job.id) && "fill-accent text-accent")}
                  />
                </button>
              ))}
            </div>
          </aside>

          <section className="panel job-scroll min-h-0 overflow-y-auto p-4 md:p-5">
            <div className="grid gap-5 lg:grid-cols-[1fr_188px]">
              <div className="flex min-w-0 items-start gap-4">
                <CompanyLogo logo={selectedJob.logo} large />
                <div className="min-w-0 pt-0.5">
                  <h2 className="text-[25px] font-bold leading-tight text-white md:text-[29px]">{selectedJob.title}</h2>
                  <p className="mt-2 text-base font-semibold text-muted">
                    {selectedJob.company} <span className="text-white/35">•</span> {selectedJob.location} <span className="text-white/35">•</span> {selectedJob.type}
                  </p>
                  <p className="mt-3 text-base font-semibold text-muted">{selectedJob.salary}</p>
                </div>
              </div>

              <div className="grid gap-2">
                <Button className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00]">
                  <ExternalLink className="h-4 w-4" />
                  Apply Now
                </Button>
                <Button
                  variant="ghost"
                  className="h-10 rounded-md border border-border bg-transparent text-[#e6ebf3] hover:bg-white/[0.06]"
                  onClick={() => toggleSaved(selectedJob.id)}
                >
                  <Heart className={cn("h-5 w-5", isSelectedSaved && "fill-accent text-accent")} />
                  {isSelectedSaved ? "Saved" : "Save Job"}
                </Button>
                <Button
                  variant="ghost"
                  className="h-10 rounded-md border border-border bg-transparent text-[#e6ebf3] hover:bg-white/[0.06]"
                  onClick={() => navigator.clipboard?.writeText(`${selectedJob.title} at ${selectedJob.company}`)}
                >
                  <Share2 className="h-5 w-5" />
                  Share Job
                </Button>
              </div>
            </div>

            <div className="mt-7 flex gap-4 overflow-x-auto border-b border-border">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "relative h-11 min-w-fit px-5 text-sm font-bold text-muted transition hover:text-white",
                    activeTab === tab && "text-white after:absolute after:bottom-[-1px] after:left-0 after:h-0.5 after:w-full after:bg-accent",
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="mt-5 grid gap-4 2xl:grid-cols-[minmax(0,1.12fr)_minmax(320px,0.9fr)]">
              <div className="grid gap-4">
                <JobMainPanel job={selectedJob} tab={activeTab} />
                <SalaryInsights job={selectedJob} />
              </div>

              <div className="grid content-start gap-4">
                <MatchPanel job={selectedJob} />
                <RecommendationsPanel job={selectedJob} />
                <JobDetails job={selectedJob} />
              </div>
            </div>
          </section>
        </div>
        </section>
      </div>
    </main>
  );
}

function AppSidebar() {
  return (
    <aside className="app-sidebar hidden h-screen w-[220px] shrink-0 overflow-y-auto border-r border-border bg-white/[0.025] px-3 py-5 lg:flex lg:flex-col 2xl:w-[250px]">
      <div className="app-sidebar-brand mb-7 flex items-center gap-3 px-2">
        <img
          src="/brand/tasko-mark.png"
          alt=""
          className="app-sidebar-mark h-10 w-9 object-contain"
          aria-hidden="true"
        />
        <div className="min-w-0">
          <p className="bg-gradient-to-b from-[#ff8a1f] to-[#ff4d00] bg-clip-text text-[22px] font-black leading-none text-transparent">
            tasko
          </p>
          <p className="mt-1 text-xs text-muted">AI Career Assistant</p>
        </div>
      </div>

      <nav className="app-sidebar-nav space-y-2">
        {navItems.map((item) => (
          <a
            href="#"
            key={item.label}
            className={cn(
              "app-sidebar-nav-item group flex h-11 items-center gap-3 rounded-md px-4 text-[15px] text-[#d9dee7] transition",
              item.active
                ? "border border-white/[0.12] bg-white/10 text-white shadow-[inset_4px_0_0_#ff5a00]"
                : "hover:bg-white/[0.055] hover:text-white",
            )}
          >
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      <div className="app-sidebar-footer mt-auto border-t border-border pt-4">
        <div className="app-sidebar-profile mb-3 flex items-center gap-3 rounded-md px-2 py-2">
          <div className="grid h-10 w-10 place-items-center rounded-full bg-white text-xs font-bold text-slate-900">
            AJ
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium">Alex Johnson</p>
            <p className="text-sm text-muted">Product Designer</p>
          </div>
          <ChevronRight className="h-5 w-5 text-muted" />
        </div>
        <a
          href="#"
          className="app-sidebar-settings flex h-11 items-center gap-3 rounded-md px-3 text-muted hover:bg-white/[0.055] hover:text-white"
        >
          <Settings className="h-5 w-5" />
          <span>Settings</span>
          <ChevronRight className="ml-auto h-5 w-5" />
        </a>
      </div>
    </aside>
  );
}

function JobMainPanel({ job, tab }: { job: Job; tab: string }) {
  if (tab === "Company") {
    return (
      <article className="panel p-4">
        <h3 className="text-lg font-bold">Company</h3>
        <p className="mt-4 text-sm leading-6 text-muted">{job.companyInfo}</p>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <InfoStat label="Team" value={job.department} />
          <InfoStat label="Location" value={job.location} />
          <InfoStat label="Role" value={job.type} />
        </div>
      </article>
    );
  }

  if (tab === "AI Match") {
    return (
      <article className="panel p-4">
        <h3 className="text-lg font-bold">AI Match Analysis</h3>
        <p className="mt-4 text-sm leading-6 text-muted">
          Your profile is a strong fit for this role because the portfolio signals, seniority, and product design keywords align with the job description.
        </p>
        <div className="mt-5 space-y-3">
          {["Portfolio relevance", "Experience level", "Skill alignment", "Culture fit"].map((item, index) => (
            <div key={item} className="flex items-center gap-3">
              <div className="h-2 flex-1 rounded-full bg-white/[0.08]">
                <div className="h-full rounded-full bg-success" style={{ width: `${job.match - index * 5}%` }} />
              </div>
              <span className="w-36 text-sm text-muted">{item}</span>
            </div>
          ))}
        </div>
      </article>
    );
  }

  if (tab === "Reviews") {
    return (
      <article className="panel p-4">
        <h3 className="text-lg font-bold">Reviews</h3>
        <div className="mt-4 space-y-3">
          {job.reviews.map((review) => (
            <p key={review} className="rounded-md border border-border bg-white/[0.025] p-3 text-sm leading-6 text-muted">
              {review}
            </p>
          ))}
        </div>
      </article>
    );
  }

  if (tab === "Similar Jobs") {
    return (
      <article className="panel p-4">
        <h3 className="text-lg font-bold">Similar Jobs</h3>
        <div className="mt-4 space-y-3">
          {job.similarJobs.map((similarJob) => (
            <div key={similarJob} className="flex items-center justify-between rounded-md border border-border bg-white/[0.025] p-3">
              <p className="text-sm font-semibold text-[#d8dee8]">{similarJob}</p>
              <ChevronDown className="h-4 w-4 -rotate-90 text-muted" />
            </div>
          ))}
        </div>
      </article>
    );
  }

  return (
    <article className="panel p-4">
      <h3 className="text-lg font-bold">Job Description</h3>
      <p className="mt-4 text-sm leading-6 text-muted">{job.overview}</p>

      <h4 className="mt-7 text-base font-bold">Key Responsibilities</h4>
      <ul className="mt-3 space-y-2 text-sm leading-5 text-muted">
        {job.responsibilities.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted" />
            {item}
          </li>
        ))}
      </ul>

      <h4 className="mt-7 text-base font-bold">Requirements</h4>
      <ul className="mt-3 space-y-2 text-sm leading-5 text-muted">
        {job.requirements.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted" />
            {item}
          </li>
        ))}
      </ul>

      <div className="mt-7 flex flex-wrap gap-2">
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
    <article className="panel p-5">
      <h3 className="text-lg font-bold">AI Match Score</h3>
      <p className="mt-4 text-[40px] font-bold leading-none text-success">{job.match}%</p>
      <div className="mt-3 h-2 rounded-full bg-white/[0.09]">
        <div className="h-full rounded-full bg-success" style={{ width: `${job.match}%` }} />
      </div>
      <h4 className="mt-7 text-sm font-bold">Why this match?</h4>
      <ul className="mt-3 space-y-2 text-sm text-muted">
        {["Strong portfolio match", "Relevant experience", "Skills alignment", "Company culture fit"].map((item) => (
          <li key={item} className="flex items-center gap-2">
            <Check className="h-4 w-4 text-success" />
            {item}
          </li>
        ))}
      </ul>
      <a className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-accent" href="#">
        Review full analysis <span aria-hidden="true">-&gt;</span>
      </a>
    </article>
  );
}

function RecommendationsPanel({ job }: { job: Job }) {
  return (
    <article className="panel p-5">
      <h3 className="text-lg font-bold">AI Recommendations</h3>
      <div className="mt-3 divide-y divide-border">
        {job.recommendations.map((recommendation) => (
          <div key={recommendation.text} className="flex items-center justify-between gap-4 py-2.5 text-sm">
            <p className="text-muted">{recommendation.text}</p>
            <p className="shrink-0 font-bold text-success">{recommendation.gain}</p>
          </div>
        ))}
      </div>
      <a className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-accent" href="#">
        View all recommendations <span aria-hidden="true">-&gt;</span>
      </a>
    </article>
  );
}

function SalaryInsights({ job }: { job: Job }) {
  return (
    <article className="panel p-4">
      <h3 className="text-lg font-bold">Salary Insights</h3>
      <p className="mt-6 text-[30px] font-bold leading-none">{job.salaryAverage}</p>
      <p className="mt-2 text-sm text-muted">Average total compensation</p>
      <div className="mt-8">
        <div className="relative h-2 rounded-full bg-white/[0.10]">
          <div className="absolute left-0 top-0 h-full w-1/2 rounded-full bg-accent" />
          <span className="absolute left-1/2 top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent" />
        </div>
        <div className="mt-4 flex justify-between text-sm font-semibold text-muted">
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
    <article className="panel p-5">
      <h3 className="text-lg font-bold">Job Details</h3>
      <dl className="mt-5 space-y-3">
        {details.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[130px_1fr] gap-4 text-sm">
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
    <div className="rounded-md border border-border bg-white/[0.025] p-3">
      <p className="text-xs font-semibold uppercase text-muted">{label}</p>
      <p className="mt-2 text-sm font-bold text-white">{value}</p>
    </div>
  );
}

function CompanyLogo({ logo, large = false }: { logo: Job["logo"]; large?: boolean }) {
  const sizeClass = large ? "h-[88px] w-[88px]" : "h-14 w-14 2xl:h-[62px] 2xl:w-[62px]";

  if (logo === "figma") {
    return (
      <div className={cn("grid shrink-0 place-items-center rounded-md bg-black", sizeClass)}>
        <div className={cn("grid grid-cols-2", large ? "scale-150" : "")}>
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
    <div className={cn("grid shrink-0 place-items-center rounded-md bg-black font-black text-white", large ? "text-2xl" : "text-xl", sizeClass)}>
      stripe
    </div>
  );
}
