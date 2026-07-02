import {
  BriefcaseBusiness,
  Bot,
  Bookmark,
  Calendar,
  CalendarDays,
  Check,
  ChevronRight,
  CircleDot,
  Command,
  FileText,
  Home,
  Mail,
  MoreHorizontal,
  Plus,
  Settings,
  Sparkles,
  Star,
  Target,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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

const jobs = [
  { company: "stripe", title: "Senior Product Designer", source: "Stripe", match: 92, time: "2h ago", logo: "stripe" },
  { company: "figma", title: "Product Design Lead", source: "Figma", match: 88, time: "5h ago", logo: "figma" },
  { company: "notion", title: "UX Designer", source: "Notion", match: 85, time: "1d ago", logo: "notion" },
  { company: "hubspot", title: "Senior UX Designer", source: "HubSpot", match: 80, time: "1d ago", logo: "hubspot" },
];

const overview = [
  { label: "Applied", value: "12 (50%)", color: "bg-[#ff5a00]" },
  { label: "Interview", value: "5 (21%)", color: "bg-[#ff9f1a]" },
  { label: "Assessment", value: "3 (13%)", color: "bg-[#2f80ed]" },
  { label: "Offer", value: "2 (8%)", color: "bg-[#4a9d35]" },
  { label: "Rejected", value: "2 (8%)", color: "bg-[#d94d4d]" },
];

const navItems = [
  { label: "Dashboard", icon: Home, active: true },
  { label: "Jobs", icon: BriefcaseBusiness },
  { label: "Applications", icon: Mail },
  { label: "AI Assistant", icon: Sparkles },
];

export default function HomePage() {
  return (
    <main className="h-screen overflow-hidden bg-background text-foreground">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(255,90,0,0.16),transparent_28%),radial-gradient(circle_at_72%_0%,rgba(35,120,255,0.10),transparent_28%)]" />
      <div className="relative mx-auto flex h-full max-w-[1536px] overflow-hidden rounded-none border-border bg-[#0a0f15]/96 shadow-panel lg:rounded-[18px] lg:border">
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
            <a href="#" className="app-sidebar-settings flex h-11 items-center gap-3 rounded-md px-3 text-muted hover:bg-white/[0.055] hover:text-white">
              <Settings className="h-5 w-5" />
              <span>Settings</span>
              <ChevronRight className="ml-auto h-5 w-5" />
            </a>
          </div>
        </aside>

        <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden px-4 py-4 sm:px-5 xl:px-5">
          <header className="mb-4 flex shrink-0 flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h1 className="text-[26px] font-bold leading-tight tracking-normal text-white xl:text-[28px]">Good morning, Alex!</h1>
              <p className="mt-1.5 text-sm text-muted xl:text-base">Let's find the right opportunity for you today.</p>
            </div>
            <Button size="lg" className="h-11 w-full justify-center rounded-md bg-gradient-to-r from-[#ff5a00] to-[#dd3d00] md:w-auto">
              <Plus className="h-5 w-5" />
              New Search
              <span className="ml-2 inline-flex items-center gap-1 rounded-md bg-white/10 px-2 py-1 text-xs">
                <Command className="h-3 w-3" /> K
              </span>
            </Button>
          </header>

          <div className="grid shrink-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((stat) => (
              <article key={stat.label} className="panel min-h-[142px] p-4">
                <div className="mb-2 flex items-start gap-3">
                  <div
                    className={cn(
                      "grid h-11 w-11 shrink-0 place-items-center rounded-md",
                      stat.color === "green" ? "bg-success/20 text-success" : "bg-accent/20 text-accent",
                    )}
                  >
                    <stat.icon className="h-6 w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[#d6dbe4]">{stat.label}</p>
                    <p className="mt-1 text-[28px] font-bold leading-none">{stat.value}</p>
                    <p className="mt-1 text-sm text-muted">{stat.note}</p>
                  </div>
                  <MoreHorizontal className="h-4 w-4 text-muted" />
                </div>
                {stat.progress ? (
                  <div className="mt-5 h-2 rounded-full bg-white/[0.06]">
                    <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-[#ff5a00] to-[#ff7a1a]" />
                  </div>
                ) : (
                  <svg viewBox="0 0 250 54" className="h-10 w-full" aria-hidden="true">
                    <path d={stat.chart} fill="none" stroke={stat.color === "green" ? "#58d532" : "#ff5a00"} strokeWidth="2.4" />
                    <path d={`${stat.chart} L250,54 L0,54 Z`} fill={stat.color === "green" ? "rgba(88,213,50,0.10)" : "rgba(255,90,0,0.10)"} />
                  </svg>
                )}
                <p className="mt-3 text-sm text-muted">
                  <span className="mr-2 font-bold text-success">up {stat.delta}</span>vs last 30 days
                </p>
              </article>
            ))}
          </div>

          <div className="mt-3 grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.98fr)]">
            <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_100px] gap-3">
              <section className="panel flex min-h-0 flex-col overflow-hidden p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Star className="h-5 w-5 text-accent" />
                    <h2 className="text-lg font-bold">Recommended Jobs</h2>
                  </div>
                  <a className="inline-flex items-center gap-2 text-sm font-semibold text-accent" href="#">
                    View all jobs <ChevronRight className="h-4 w-4" />
                  </a>
                </div>
                <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
                  {jobs.slice(0, 3).map((job) => (
                    <div key={job.title} className="grid min-h-[58px] grid-cols-[52px_minmax(0,1fr)_28px] items-center gap-3 border-b border-border px-3 py-2 last:border-0 sm:grid-cols-[58px_minmax(0,1fr)_104px_28px]">
                      <CompanyLogo logo={job.logo} />
                      <div className="min-w-0">
                        <h3 className="truncate text-base font-semibold">{job.title}</h3>
                        <p className="text-xs text-muted">{job.source}</p>
                        <div className="mt-1 flex gap-2">
                          <span className="tag">Remote</span>
                          <span className="tag">Full-time</span>
                        </div>
                      </div>
                      <div className="hidden text-left sm:block">
                        <p className="text-sm font-semibold text-success">{job.match}% match</p>
                        <p className="mt-1 text-xs text-muted">{job.time}</p>
                      </div>
                      <Bookmark className="h-5 w-5 text-muted" />
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted" />
                    <h2 className="text-base font-bold">Upcoming Interviews</h2>
                  </div>
                  <a className="inline-flex items-center gap-2 text-sm font-semibold text-accent" href="#">
                    View all <ChevronRight className="h-4 w-4" />
                  </a>
                </div>
                <div className="grid gap-3 rounded-md border border-border px-3 py-2 sm:grid-cols-[48px_1fr_132px_auto_18px] sm:items-center">
                  <div className="text-center">
                    <p className="text-xs font-bold uppercase text-accent">May</p>
                    <p className="text-xl font-bold leading-tight">24</p>
                    <p className="text-xs text-accent">Fri</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="grid h-9 w-9 place-items-center rounded-full bg-white text-xl font-bold text-[#4285f4]">G</div>
                    <div>
                      <p className="text-sm font-semibold">Google</p>
                      <p className="text-xs text-muted">Senior Product Designer</p>
                    </div>
                  </div>
                  <div className="space-y-1 text-xs text-muted">
                    <p className="flex items-center gap-2"><Calendar className="h-4 w-4" /> May 24, 2024</p>
                    <p className="flex items-center gap-2"><CircleDot className="h-4 w-4" /> 10:00 AM</p>
                  </div>
                  <Button variant="outline" size="sm" className="h-7 px-2">Video Interview</Button>
                  <MoreHorizontal className="hidden h-5 w-5 text-muted sm:block" />
                </div>
              </section>
            </div>

            <aside className="grid min-h-0 grid-rows-[minmax(0,1fr)_172px] gap-3">
              <section className="panel p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-bold">Application Overview</h2>
                  <Button variant="ghost" size="sm" className="border border-border">Last 30 days</Button>
                </div>
                <div className="grid items-center gap-4 sm:grid-cols-[150px_1fr] xl:grid-cols-[150px_minmax(0,1fr)]">
                  <div className="relative mx-auto h-[138px] w-[138px] rounded-full overview-ring">
                    <div className="absolute inset-[34px] grid place-items-center rounded-full bg-[#131920]">
                      <p className="text-center text-2xl font-bold">24<br /><span className="text-xs font-normal text-muted">Total</span></p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {overview.map((item) => (
                      <div key={item.label} className="flex items-center gap-3 text-sm">
                        <span className={cn("h-3.5 w-3.5 rounded-full", item.color)} />
                        <span className="flex-1 text-muted">{item.label}</span>
                        <span className="text-[#cbd2dd]">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <a className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-accent" href="#">
                  View full report <ChevronRight className="h-4 w-4" />
                </a>
              </section>

              <section className="panel p-3">
                <div className="mb-2 flex items-center justify-between">
                  <h2 className="text-base font-bold">AI Assistant</h2>
                  <Button variant="outline" size="sm" className="h-7 px-2">New Chat</Button>
                </div>
                <div className="rounded-md border border-border p-2.5">
                  <div className="grid gap-2 sm:grid-cols-[34px_1fr]">
                    <div className="grid h-8 w-8 place-items-center rounded-full bg-accent/20 text-accent">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="space-y-1 text-[11px] leading-tight text-muted">
                      <p>Hi Alex! I can help you with:</p>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
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
      </div>
    </main>
  );
}

function CompanyLogo({ logo }: { logo: string }) {
  if (logo === "figma") {
    return (
      <div className="grid h-12 w-12 place-items-center rounded-md bg-black">
        <div className="grid grid-cols-2">
          <span className="h-3 w-3 rounded-l-full bg-[#ff7262]" />
          <span className="h-3 w-3 rounded-r-full bg-[#f24e1e]" />
          <span className="h-3 w-3 rounded-l-full bg-[#a259ff]" />
          <span className="h-3 w-3 rounded-r-full bg-[#1abcfe]" />
          <span className="h-3 w-3 rounded-full bg-[#0acf83]" />
        </div>
      </div>
    );
  }

  if (logo === "notion") {
    return (
      <div className="grid h-12 w-12 place-items-center rounded-md bg-black">
        <div className="grid h-8 w-8 place-items-center border-2 border-white bg-white text-2xl font-black text-black">N</div>
      </div>
    );
  }

  if (logo === "hubspot") {
    return (
      <div className="grid h-12 w-12 place-items-center rounded-md bg-black text-[#ff6b3a]">
        <UserRound className="h-7 w-7" />
      </div>
    );
  }

  return (
    <div className="grid h-12 w-12 place-items-center rounded-md bg-black text-xl font-black text-[#7357ff]">
      stripe
    </div>
  );
}
