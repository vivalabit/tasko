"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Ban,
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
  Download,
  Edit3,
  ExternalLink,
  FileText,
  Github,
  GraduationCap,
  Globe,
  Heart,
  Home,
  Linkedin,
  Mail,
  MapPin,
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
  Upload,
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

type CandidateProfile = {
  avatar_url: string;
  name: string;
  current_role: string;
  desired_role: string;
  location: string;
  work_format: string;
  headline: string;
  linkedin: string;
  github: string;
  portfolio: string;
  personal_site: string;
  experience: string;
  skills: string;
  education: string;
  job_preferences: string;
  dealbreakers: string;
  additional_notes: string;
  documents: string;
  resume_file_name: string;
  resume_file_size: string;
  resume_updated_at: string;
  resume_data_url: string;
};

type ExperienceEntry = {
  id: string;
  title: string;
  company: string;
  employment_type: string;
  location: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
};

type EducationEntry = {
  id: string;
  institution: string;
  credential: string;
  field_of_study: string;
  location: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
};

type DocumentEntry = {
  id: string;
  title: string;
  category: string;
  issuer: string;
  notes: string;
  file_name: string;
  file_size: string;
  file_type: string;
  uploaded_at: string;
  data_url: string;
};

type JobPreferences = {
  desired_roles: string[];
  seniority: string[];
  locations: string[];
  work_formats: string[];
  employment_types: string[];
  industries: string[];
  salary_min: string;
  salary_currency: string;
  work_authorization: string;
  languages: string[];
  company_sizes: string[];
  priorities: string[];
  notes: string;
  no_preference: PreferenceAnyField[];
};

type PreferenceListField = "desired_roles" | "locations" | "industries" | "languages";
type PreferenceToggleField = "seniority" | "work_formats" | "employment_types" | "company_sizes" | "priorities";
type PreferenceAnyField =
  | PreferenceListField
  | PreferenceToggleField
  | "salary"
  | "work_authorization";
type PreferenceInputs = Record<PreferenceListField, string>;

type ResumeExperienceImportResponse = {
  experience?: Array<Partial<ExperienceEntry>>;
  message?: string;
  detail?: string;
};

type ResumeEducationImportResponse = {
  education?: Array<Partial<EducationEntry>>;
  message?: string;
  detail?: string;
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
type View = "Dashboard" | "Jobs" | "Profile";
type ParserSearchStatus = "idle" | "loading" | "ready" | "error";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const snapshotPollDelayMs = 4000;
const snapshotPollMaxAttempts = 30;
const importedJobsStorageKey = "tasko.importedJobs.v1";
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

const defaultCandidateProfile: CandidateProfile = {
  avatar_url: "/avatars/default-pug.png",
  name: "",
  current_role: "",
  desired_role: "",
  location: "",
  work_format: "",
  headline: "",
  linkedin: "",
  github: "",
  portfolio: "",
  personal_site: "",
  experience: "",
  skills: "",
  education: "",
  job_preferences: "",
  dealbreakers: "",
  additional_notes: "",
  documents: "",
  resume_file_name: "",
  resume_file_size: "",
  resume_updated_at: "",
  resume_data_url: "",
};

const defaultExperienceDraft: ExperienceEntry = {
  id: "",
  title: "",
  company: "",
  employment_type: "Full-time",
  location: "",
  start_date: "",
  end_date: "",
  is_current: false,
  description: "",
};

const defaultEducationDraft: EducationEntry = {
  id: "",
  institution: "",
  credential: "",
  field_of_study: "",
  location: "",
  start_date: "",
  end_date: "",
  is_current: false,
  description: "",
};

const defaultDocumentDraft: DocumentEntry = {
  id: "",
  title: "",
  category: "Other",
  issuer: "",
  notes: "",
  file_name: "",
  file_size: "",
  file_type: "",
  uploaded_at: "",
  data_url: "",
};

const documentCategories = [
  "Diploma",
  "Certificate",
  "Recommendation",
  "Work permit",
  "Portfolio",
  "Transcript",
  "Other",
];

const defaultJobPreferences: JobPreferences = {
  desired_roles: [],
  seniority: [],
  locations: [],
  work_formats: [],
  employment_types: [],
  industries: [],
  salary_min: "",
  salary_currency: "CHF",
  work_authorization: "",
  languages: [],
  company_sizes: [],
  priorities: [],
  notes: "",
  no_preference: [],
};

const defaultPreferenceInputs: PreferenceInputs = {
  desired_roles: "",
  locations: "",
  industries: "",
  languages: "",
};

const preferenceOptions = {
  seniority: ["Intern", "Entry-level", "Junior", "Mid-level", "Senior"],
  work_formats: ["Remote", "Hybrid", "On-site", "Relocation"],
  employment_types: ["Full-time", "Part-time", "Internship", "Contract", "Freelance"],
  company_sizes: ["Startup", "Scale-up", "Mid-size", "Enterprise"],
  priorities: ["Salary", "Learning", "Remote", "Relocation", "Tech stack", "Stability", "Fast hiring"],
  work_authorization: ["Authorized to work", "Needs sponsorship", "EU/EFTA eligible", "Swiss permit", "Student permit", "Not sure"],
};

const preferenceSuggestions: Record<PreferenceListField, string[]> = {
  desired_roles: [
    "Python Developer",
    "Backend Developer",
    "AI Engineer",
    "Full-stack Developer",
    "Data Engineer",
    "Machine Learning Engineer",
  ],
  locations: ["Switzerland", "Zurich", "Remote Europe", "Germany", "Austria", "Netherlands", "Remote worldwide"],
  industries: ["AI", "SaaS", "FinTech", "HealthTech", "Developer tools", "EdTech", "E-commerce", "Cybersecurity"],
  languages: ["English C1", "English B2", "German A2", "German B1", "French B1", "Russian native"],
};

const preferenceListLabels: Record<PreferenceListField, { label: string; placeholder: string }> = {
  desired_roles: { label: "Desired roles", placeholder: "Python Developer, AI Engineer..." },
  locations: { label: "Locations", placeholder: "Zurich, Switzerland, Remote Europe..." },
  industries: { label: "Industries", placeholder: "AI, SaaS, FinTech..." },
  languages: { label: "Languages", placeholder: "English C1, German A2..." },
};

const preferenceSummaryLabels: Record<PreferenceAnyField, string> = {
  desired_roles: "Roles",
  seniority: "Seniority",
  locations: "Locations",
  work_formats: "Work format",
  employment_types: "Employment",
  industries: "Industries",
  salary: "Salary floor",
  work_authorization: "Authorization",
  languages: "Languages",
  company_sizes: "Company size",
  priorities: "Priorities",
};

const suggestedSkills = [
  "Agile Development",
  "AI Agent Development",
  "AI Application Development",
  "AI Engineering",
  "AI Integrations",
  "AI Literacy",
  "AI Model Evaluation",
  "AI Safety",
  "AI Strategy",
  "AJAX",
  "API Design",
  "API Development",
  "API Integration",
  "ASP.NET",
  "AWS",
  "AWS Lambda",
  "Accessibility",
  "Algorithms",
  "Angular",
  "Ansible",
  "Apache Kafka",
  "Application Security",
  "Architecture",
  "AsyncIO",
  "Authentication",
  "Automation",
  "Azure",
  "Bash",
  "Bootstrap",
  "CI/CD",
  "CSS",
  "Celery",
  "Chatbot Development",
  "Clean Architecture",
  "Clean Code",
  "Cloud Applications",
  "Cloud Computing",
  "Cloud Functions",
  "Cloud Security",
  "Code Review",
  "Computer Vision",
  "Continuous Deployment",
  "Continuous Integration",
  "Critical Thinking",
  "Cybersecurity",
  "Django",
  "Django REST Framework",
  "Docker",
  "Docker Compose",
  "Domain-Driven Design",
  "Elasticsearch",
  "Express.js",
  "FastAPI",
  "Firebase",
  "Flask",
  "Frontend Development",
  "Full-stack Development",
  "GCP",
  "Git",
  "GitHub",
  "GitHub Actions",
  "GitLab CI",
  "Go",
  "GraphQL",
  "HTML",
  "Helm",
  "Hugging Face",
  "Java",
  "JavaScript",
  "Jenkins",
  "Jest",
  "Jira",
  "Jupyter",
  "JWT",
  "Kubernetes",
  "LangChain",
  "LangGraph",
  "Large Language Models",
  "Linux",
  "LLM Applications",
  "LLM Evaluation",
  "Machine Learning",
  "Microservices",
  "MongoDB",
  "MySQL",
  "Next.js",
  "Nginx",
  "Node.js",
  "NoSQL",
  "OAuth",
  "Object-Oriented Programming",
  "OpenAPI",
  "PHP",
  "Pandas",
  "Performance Optimization",
  "Playwright",
  "PostgreSQL",
  "Postman",
  "Problem Solving",
  "Prompt Engineering",
  "PyTorch",
  "Pytest",
  "Python",
  "QA Automation",
  "RabbitMQ",
  "React",
  "React Native",
  "Redis",
  "Refactoring",
  "Relational Databases",
  "REST API",
  "Ruby",
  "Ruby on Rails",
  "Rust",
  "SaaS Development",
  "Scikit-learn",
  "Scrum",
  "Security Best Practices",
  "Serverless",
  "Shell Scripting",
  "Software Architecture",
  "Software Design",
  "Software Development",
  "Software Engineering",
  "Software Testing",
  "Spring Boot",
  "SQL",
  "SQLite",
  "System Design",
  "Tailwind CSS",
  "Team Collaboration",
  "TensorFlow",
  "Terraform",
  "Test Automation",
  "Test-Driven Development",
  "TypeScript",
  "UI Development",
  "Unit Testing",
  "Unix",
  "UX Basics",
  "Vector Databases",
  "Vercel",
  "Vue.js",
  "Web APIs",
  "Web Development",
  "WebSockets",
  "Webpack",
  "WordPress",
  "XML",
  "YAML",
  "Zod",
  "NumPy",
  "Data Analysis",
  "Data Engineering",
  "Data Structures",
  "Data Visualization",
  "ETL",
  "MLOps",
  "MLflow",
  "RAG",
  "Retrieval-Augmented Generation",
  "Pinecone",
  "ChromaDB",
  "Qdrant",
  "Supabase",
  "Prisma",
  "SQLAlchemy",
  "ORM",
  "Pydantic",
  "Redux",
  "Zustand",
  "Svelte",
  "Nuxt.js",
  "Vite",
  "ESLint",
  "Prettier",
  "Cypress",
  "Mocha",
  "Vitest",
  "Storybook",
  "Figma",
  "Responsive Design",
  "Mobile Development",
  "Swift",
  "Kotlin",
  "Flutter",
  "Dart",
  "C",
  "C++",
  "C#",
  ".NET",
  "Graph Databases",
  "Neo4j",
  "Observability",
  "Monitoring",
  "Logging",
  "Prometheus",
  "Grafana",
  "Sentry",
  "Datadog",
  "DevOps",
  "Site Reliability Engineering",
  "Backend Development",
  "Infrastructure as Code",
  "Networking",
  "HTTP",
  "DNS",
  "TCP/IP",
  "Web Security",
  "OWASP",
  "Encryption",
  "OAuth 2.0",
  "SAML",
  "JSON",
  "gRPC",
  "Message Queues",
  "Event-Driven Architecture",
  "Distributed Systems",
  "Concurrency",
  "Multithreading",
  "Design Patterns",
  "Technical Documentation",
  "Debugging",
  "Troubleshooting",
  "Production Support",
  "Product Thinking",
  "Cross-functional Collaboration",
  "Communication",
  "Adaptability",
  "Agile Problem Solving",
];

const legacyCandidateProfileValues: Partial<CandidateProfile> = {
  name: "Alex Johnson",
  current_role: "Senior Product Designer",
  desired_role: "Design Manager",
  location: "San Francisco, CA, USA",
  work_format: "Remote, open to hybrid",
  headline:
    "Product designer with 7+ years of experience crafting intuitive B2B and B2C digital experiences. Combines user empathy with data-driven design to ship impactful products.",
  linkedin: "linkedin.com/in/alexjohnson",
  github: "github.com/alexjohnson",
  portfolio: "alexjohnson.design",
  personal_site: "alexjohnson.com",
};

function normalizeCandidateProfile(profile: Partial<CandidateProfile>): CandidateProfile {
  const normalizedProfile = { ...defaultCandidateProfile, ...profile };

  if (!normalizedProfile.avatar_url || normalizedProfile.avatar_url === "/avatars/pug.svg") {
    normalizedProfile.avatar_url = defaultCandidateProfile.avatar_url;
  }

  for (const [field, legacyValue] of Object.entries(legacyCandidateProfileValues) as Array<[keyof CandidateProfile, string]>) {
    if (normalizedProfile[field] === legacyValue) {
      normalizedProfile[field] = "";
    }
  }

  return normalizedProfile;
}

function hasProfileValue(value: string | undefined) {
  return Boolean(value?.trim());
}

function displayProfileValue(value: string, fallback: string) {
  return hasProfileValue(value) ? value : fallback;
}

function displayProfileFirstName(value: string, fallback: string) {
  return hasProfileValue(value) ? value.trim().split(/\s+/)[0] : fallback;
}

function parseProfileLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeExperienceEntry(entry: Partial<ExperienceEntry>): ExperienceEntry {
  return {
    ...defaultExperienceDraft,
    ...entry,
    id: entry.id || createClientId("experience"),
    title: entry.title?.trim() ?? "",
    company: entry.company?.trim() ?? "",
    employment_type: entry.employment_type?.trim() || "Full-time",
    location: entry.location?.trim() ?? "",
    start_date: entry.start_date?.trim() ?? "",
    end_date: entry.is_current ? "" : entry.end_date?.trim() ?? "",
    is_current: Boolean(entry.is_current),
    description: entry.description?.trim() ?? "",
  };
}

function parseExperienceEntries(value: string): ExperienceEntry[] {
  if (!value.trim()) return [];

  try {
    const parsed = JSON.parse(value) as unknown;
    if (Array.isArray(parsed)) {
      return parsed
        .filter((item): item is Partial<ExperienceEntry> => Boolean(item) && typeof item === "object")
        .map((item) => normalizeExperienceEntry(item))
        .filter((item) => item.title || item.company || item.description);
    }
  } catch {
    // Fall back to the previous one-line-per-entry format.
  }

  return parseProfileLines(value).map((item, index) =>
    normalizeExperienceEntry({
      id: `legacy-experience-${index}`,
      title: item,
      description: item,
    }),
  );
}

function serializeExperienceEntries(entries: ExperienceEntry[]) {
  return JSON.stringify(entries.map((entry) => normalizeExperienceEntry(entry)));
}

function getExperienceFingerprint(entry: ExperienceEntry) {
  return [entry.title, entry.company, entry.start_date, entry.end_date]
    .map((value) => value.trim().toLowerCase())
    .join("|");
}

function mergeExperienceEntries(currentEntries: ExperienceEntry[], importedEntries: ExperienceEntry[]) {
  const existingFingerprints = new Set(currentEntries.map(getExperienceFingerprint));
  const nextEntries = [...currentEntries];

  for (const entry of importedEntries) {
    const fingerprint = getExperienceFingerprint(entry);
    if (!entry.title || !entry.company || existingFingerprints.has(fingerprint)) {
      continue;
    }

    existingFingerprints.add(fingerprint);
    nextEntries.push(entry);
  }

  return nextEntries;
}

function normalizeEducationEntry(entry: Partial<EducationEntry>): EducationEntry {
  return {
    ...defaultEducationDraft,
    ...entry,
    id: entry.id || createClientId("education"),
    institution: entry.institution?.trim() ?? "",
    credential: entry.credential?.trim() ?? "",
    field_of_study: entry.field_of_study?.trim() ?? "",
    location: entry.location?.trim() ?? "",
    start_date: entry.start_date?.trim() ?? "",
    end_date: entry.is_current ? "" : entry.end_date?.trim() ?? "",
    is_current: Boolean(entry.is_current),
    description: entry.description?.trim() ?? "",
  };
}

function parseEducationEntries(value: string): EducationEntry[] {
  if (!value.trim()) return [];

  try {
    const parsed = JSON.parse(value) as unknown;
    if (Array.isArray(parsed)) {
      return parsed
        .filter((item): item is Partial<EducationEntry> => Boolean(item) && typeof item === "object")
        .map((item) => normalizeEducationEntry(item))
        .filter((item) => item.institution || item.credential || item.field_of_study || item.description);
    }
  } catch {
    // Fall back to the previous one-line-per-entry format.
  }

  return parseProfileLines(value).map((item, index) =>
    normalizeEducationEntry({
      id: `legacy-education-${index}`,
      credential: item,
      description: item,
    }),
  );
}

function serializeEducationEntries(entries: EducationEntry[]) {
  return JSON.stringify(entries.map((entry) => normalizeEducationEntry(entry)));
}

function getEducationFingerprint(entry: EducationEntry) {
  return [entry.institution, entry.credential, entry.field_of_study, entry.start_date, entry.end_date]
    .map((value) => value.trim().toLowerCase())
    .join("|");
}

function mergeEducationEntries(currentEntries: EducationEntry[], importedEntries: EducationEntry[]) {
  const existingFingerprints = new Set(currentEntries.map(getEducationFingerprint));
  const nextEntries = [...currentEntries];

  for (const entry of importedEntries) {
    const fingerprint = getEducationFingerprint(entry);
    if ((!entry.institution && !entry.credential) || existingFingerprints.has(fingerprint)) {
      continue;
    }

    existingFingerprints.add(fingerprint);
    nextEntries.push(entry);
  }

  return nextEntries;
}

function normalizeDocumentEntry(entry: Partial<DocumentEntry>): DocumentEntry {
  return {
    ...defaultDocumentDraft,
    ...entry,
    id: entry.id || createClientId("document"),
    title: entry.title?.trim() ?? "",
    category: entry.category?.trim() || "Other",
    issuer: entry.issuer?.trim() ?? "",
    notes: entry.notes?.trim() ?? "",
    file_name: entry.file_name?.trim() ?? "",
    file_size: entry.file_size?.trim() ?? "",
    file_type: entry.file_type?.trim() ?? "",
    uploaded_at: entry.uploaded_at?.trim() ?? "",
    data_url: entry.data_url ?? "",
  };
}

function parseDocumentEntries(value: string): DocumentEntry[] {
  if (!value.trim()) return [];

  try {
    const parsed = JSON.parse(value) as unknown;
    if (Array.isArray(parsed)) {
      return parsed
        .filter((item): item is Partial<DocumentEntry> => Boolean(item) && typeof item === "object")
        .map((item) => normalizeDocumentEntry(item))
        .filter((item) => item.title || item.file_name || item.data_url);
    }
  } catch {
    return [];
  }

  return [];
}

function serializeDocumentEntries(entries: DocumentEntry[]) {
  if (entries.length === 0) return "";

  return JSON.stringify(entries.map((entry) => normalizeDocumentEntry(entry)));
}

function normalizePreferenceList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  return Array.from(
    new Map(
      value
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.trim())
        .filter(Boolean)
        .map((item) => [item.toLowerCase(), item]),
    ).values(),
  );
}

function normalizeNoPreferenceFields(value: unknown): PreferenceAnyField[] {
  const allowedFields = new Set<PreferenceAnyField>([
    "desired_roles",
    "seniority",
    "locations",
    "work_formats",
    "employment_types",
    "industries",
    "salary",
    "work_authorization",
    "languages",
    "company_sizes",
    "priorities",
  ]);

  return normalizePreferenceList(value).filter((item): item is PreferenceAnyField =>
    allowedFields.has(item as PreferenceAnyField),
  );
}

function normalizeJobPreferences(value: Partial<JobPreferences>): JobPreferences {
  return {
    ...defaultJobPreferences,
    ...value,
    desired_roles: normalizePreferenceList(value.desired_roles),
    seniority: normalizePreferenceList(value.seniority),
    locations: normalizePreferenceList(value.locations),
    work_formats: normalizePreferenceList(value.work_formats),
    employment_types: normalizePreferenceList(value.employment_types),
    industries: normalizePreferenceList(value.industries),
    salary_min: value.salary_min?.trim() ?? "",
    salary_currency: value.salary_currency?.trim() || "CHF",
    work_authorization: value.work_authorization?.trim() ?? "",
    languages: normalizePreferenceList(value.languages),
    company_sizes: normalizePreferenceList(value.company_sizes),
    priorities: normalizePreferenceList(value.priorities),
    notes: value.notes?.trim() ?? "",
    no_preference: normalizeNoPreferenceFields(value.no_preference),
  };
}

function parseJobPreferences(value: string): JobPreferences {
  if (!value.trim()) return defaultJobPreferences;

  try {
    const parsed = JSON.parse(value) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return normalizeJobPreferences(parsed as Partial<JobPreferences>);
    }
  } catch {
    // Fall back to the previous one-line-per-preference format.
  }

  return normalizeJobPreferences({ notes: parseProfileLines(value).join("\n") });
}

function serializeJobPreferences(preferences: JobPreferences) {
  const normalizedPreferences = normalizeJobPreferences(preferences);
  const hasValues =
    normalizedPreferences.desired_roles.length > 0 ||
    normalizedPreferences.seniority.length > 0 ||
    normalizedPreferences.locations.length > 0 ||
    normalizedPreferences.work_formats.length > 0 ||
    normalizedPreferences.employment_types.length > 0 ||
    normalizedPreferences.industries.length > 0 ||
    hasProfileValue(normalizedPreferences.salary_min) ||
    hasProfileValue(normalizedPreferences.work_authorization) ||
    normalizedPreferences.languages.length > 0 ||
    normalizedPreferences.company_sizes.length > 0 ||
    normalizedPreferences.priorities.length > 0 ||
    normalizedPreferences.no_preference.length > 0 ||
    hasProfileValue(normalizedPreferences.notes);

  return hasValues ? JSON.stringify(normalizedPreferences) : "";
}

function formatPreferenceSummary(preferences: JobPreferences) {
  const preferenceValue = (field: PreferenceAnyField, values: string[]) =>
    preferences.no_preference.includes(field) ? ["No preference"] : values;

  const items: Array<{ label: string; values: string[] }> = [
    { label: "Roles", values: preferenceValue("desired_roles", preferences.desired_roles) },
    { label: "Seniority", values: preferenceValue("seniority", preferences.seniority) },
    { label: "Locations", values: preferenceValue("locations", preferences.locations) },
    { label: "Work format", values: preferenceValue("work_formats", preferences.work_formats) },
    { label: "Employment", values: preferenceValue("employment_types", preferences.employment_types) },
    { label: "Industries", values: preferenceValue("industries", preferences.industries) },
    { label: "Languages", values: preferenceValue("languages", preferences.languages) },
    { label: "Company size", values: preferenceValue("company_sizes", preferences.company_sizes) },
    { label: "Priorities", values: preferenceValue("priorities", preferences.priorities) },
  ].filter((item) => item.values.length > 0);

  if (preferences.no_preference.includes("salary")) {
    items.splice(6, 0, { label: "Salary floor", values: ["No preference"] });
  } else if (hasProfileValue(preferences.salary_min)) {
    items.splice(6, 0, { label: "Salary floor", values: [`${preferences.salary_currency} ${preferences.salary_min}`] });
  }

  if (preferences.no_preference.includes("work_authorization")) {
    items.splice(7, 0, { label: "Authorization", values: ["No preference"] });
  } else if (hasProfileValue(preferences.work_authorization)) {
    items.splice(7, 0, { label: "Authorization", values: [preferences.work_authorization] });
  }

  if (hasProfileValue(preferences.notes)) {
    items.push({ label: "Notes", values: [preferences.notes] });
  }

  return items;
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatProfileDate(value: string) {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getProfileCompletion(profile: CandidateProfile) {
  const fields: Array<keyof CandidateProfile> = [
    "name",
    "current_role",
    "desired_role",
    "location",
    "work_format",
    "headline",
    "linkedin",
    "github",
    "portfolio",
    "personal_site",
    "experience",
    "skills",
    "education",
    "job_preferences",
    "dealbreakers",
    "additional_notes",
    "documents",
    "resume_file_name",
  ];
  const completedFields = fields.filter((field) => hasProfileValue(profile[field]));

  return Math.round((completedFields.length / fields.length) * 100);
}

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

  if (window.location.hash === "#profile") {
    return "Profile";
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

function isImportedJob(job: Job) {
  return job.id.startsWith("linkedin-");
}

function normalizeStoredJobs(value: unknown) {
  if (!Array.isArray(value)) return [];

  return value.filter((job): job is Job => {
    if (!job || typeof job !== "object") return false;
    const candidate = job as Partial<Job>;
    return (
      typeof candidate.id === "string" &&
      typeof candidate.company === "string" &&
      typeof candidate.title === "string" &&
      typeof candidate.location === "string" &&
      typeof candidate.type === "string" &&
      typeof candidate.salary === "string" &&
      typeof candidate.posted === "string" &&
      typeof candidate.experience === "string" &&
      typeof candidate.department === "string" &&
      typeof candidate.match === "number" &&
      (candidate.logo === "stripe" || candidate.logo === "figma" || candidate.logo === "linkedin") &&
      typeof candidate.overview === "string" &&
      Array.isArray(candidate.responsibilities) &&
      Array.isArray(candidate.requirements) &&
      Array.isArray(candidate.skills)
    );
  });
}

function mergeJobs(importedJobs: Job[], currentJobs: Job[]) {
  const importedIds = new Set(importedJobs.map((job) => job.id));
  return [...importedJobs, ...currentJobs.filter((job) => !importedIds.has(job.id))];
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
  const [profile, setProfile] = useState<CandidateProfile>(defaultCandidateProfile);
  const [profileDraft, setProfileDraft] = useState<CandidateProfile>(defaultCandidateProfile);
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);
  const [isExperienceDialogOpen, setIsExperienceDialogOpen] = useState(false);
  const [isExperienceEditMode, setIsExperienceEditMode] = useState(false);
  const [experienceDraft, setExperienceDraft] = useState<ExperienceEntry>(defaultExperienceDraft);
  const [isExperienceImporting, setIsExperienceImporting] = useState(false);
  const [experienceImportMessage, setExperienceImportMessage] = useState("");
  const [isEducationDialogOpen, setIsEducationDialogOpen] = useState(false);
  const [isEducationEditMode, setIsEducationEditMode] = useState(false);
  const [educationDraft, setEducationDraft] = useState<EducationEntry>(defaultEducationDraft);
  const [isEducationImporting, setIsEducationImporting] = useState(false);
  const [educationImportMessage, setEducationImportMessage] = useState("");
  const [isDocumentDialogOpen, setIsDocumentDialogOpen] = useState(false);
  const [isDocumentEditMode, setIsDocumentEditMode] = useState(false);
  const [documentDraft, setDocumentDraft] = useState<DocumentEntry>(defaultDocumentDraft);
  const [isPreferencesDialogOpen, setIsPreferencesDialogOpen] = useState(false);
  const [preferencesDraft, setPreferencesDraft] = useState<JobPreferences>(defaultJobPreferences);
  const [preferenceInputs, setPreferenceInputs] = useState<PreferenceInputs>(defaultPreferenceInputs);
  const [isSkillsDialogOpen, setIsSkillsDialogOpen] = useState(false);
  const [skillsDraft, setSkillsDraft] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [profileSaveStatus, setProfileSaveStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [profileSaveMessage, setProfileSaveMessage] = useState("");

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

  useEffect(() => {
    const abortController = new AbortController();

    try {
      const rawImportedJobs = window.localStorage.getItem(importedJobsStorageKey);
      const importedJobs = normalizeStoredJobs(rawImportedJobs ? JSON.parse(rawImportedJobs) : []);
      if (importedJobs.length > 0) {
        setJobList((currentJobs) => mergeJobs(importedJobs, currentJobs));
        setSelectedJobId((currentId) => currentId || importedJobs[0].id);
      }
    } catch {
      window.localStorage.removeItem(importedJobsStorageKey);
    }

    async function loadStoredJobs() {
      try {
        const response = await fetch(`${apiBaseUrl}/jobs`, {
          cache: "no-store",
          signal: abortController.signal,
        });

        if (!response.ok) return;

        const storedJobs = (await response.json()) as Array<{ id: string; data: unknown }>;
        const importedJobs = normalizeStoredJobs(storedJobs.map((job) => job.data));
        if (importedJobs.length === 0) return;

        setJobList((currentJobs) => mergeJobs(importedJobs, currentJobs));
        window.localStorage.setItem(importedJobsStorageKey, JSON.stringify(importedJobs));
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }

    async function loadProfile() {
      try {
        const response = await fetch(`${apiBaseUrl}/profile`, {
          cache: "no-store",
          signal: abortController.signal,
        });

        if (!response.ok) return;

        const loadedProfile = normalizeCandidateProfile((await response.json()) as Partial<CandidateProfile>);
        setProfile(loadedProfile);
        setProfileDraft(loadedProfile);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }

    loadStoredJobs();
    loadProfile();

    return () => {
      abortController.abort();
    };
  }, []);

  function changeView(view: View) {
    setActiveView(view);
    const viewHash: Record<View, string> = {
      Dashboard: "#dashboard",
      Jobs: "#jobs",
      Profile: "#profile",
    };
    window.history.replaceState(null, "", viewHash[view]);
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

  function openProfileEditor() {
    setProfileDraft(profile);
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
    setIsProfileDialogOpen(true);
  }

  function openExperienceEditor(experience?: ExperienceEntry) {
    setExperienceDraft(experience ? normalizeExperienceEntry(experience) : { ...defaultExperienceDraft, id: createClientId("experience") });
    setIsExperienceEditMode(Boolean(experience));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
    setIsExperienceDialogOpen(true);
  }

  function openEducationEditor(education?: EducationEntry) {
    setEducationDraft(education ? normalizeEducationEntry(education) : { ...defaultEducationDraft, id: createClientId("education") });
    setIsEducationEditMode(Boolean(education));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
    setIsEducationDialogOpen(true);
  }

  function openDocumentEditor(document?: DocumentEntry) {
    setDocumentDraft(document ? normalizeDocumentEntry(document) : { ...defaultDocumentDraft, id: createClientId("document") });
    setIsDocumentEditMode(Boolean(document));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
    setIsDocumentDialogOpen(true);
  }

  function openPreferencesEditor() {
    setPreferencesDraft(parseJobPreferences(profile.job_preferences));
    setPreferenceInputs(defaultPreferenceInputs);
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
    setIsPreferencesDialogOpen(true);
  }

  function openSkillsEditor() {
    setSkillsDraft(parseProfileLines(profile.skills));
    setSkillInput("");
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
    setIsSkillsDialogOpen(true);
  }

  function addSkillToDraft(skill: string) {
    const normalizedSkill = skill.trim();
    if (!normalizedSkill) return;

    setSkillsDraft((currentSkills) => {
      const existingSkills = new Set(currentSkills.map((item) => item.toLowerCase()));
      if (existingSkills.has(normalizedSkill.toLowerCase())) {
        return currentSkills;
      }

      return [...currentSkills, normalizedSkill];
    });
    setSkillInput("");
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function removeSkillFromDraft(skill: string) {
    setSkillsDraft((currentSkills) => currentSkills.filter((item) => item !== skill));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function updateProfileDraft<Field extends keyof CandidateProfile>(
    field: Field,
    value: CandidateProfile[Field],
  ) {
    setProfileDraft((current) => ({ ...current, [field]: value }));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function updatePreferencesDraft<Field extends keyof JobPreferences>(
    field: Field,
    value: JobPreferences[Field],
  ) {
    setPreferencesDraft((current) => {
      const noPreferenceField =
        field === "salary_min"
          ? "salary"
          : field === "work_authorization"
            ? "work_authorization"
            : (["desired_roles", "seniority", "locations", "work_formats", "employment_types", "industries", "languages", "company_sizes", "priorities"] as string[]).includes(field)
              ? (field as PreferenceAnyField)
              : "";

      return normalizeJobPreferences({
        ...current,
        [field]: value,
        no_preference: noPreferenceField
          ? current.no_preference.filter((item) => item !== noPreferenceField)
          : current.no_preference,
      });
    });
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function updatePreferenceInput(field: PreferenceListField, value: string) {
    setPreferenceInputs((current) => ({ ...current, [field]: value }));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function addPreferenceListItem(field: PreferenceListField) {
    const values = preferenceInputs[field]
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (values.length === 0) return;

    setPreferencesDraft((current) =>
      normalizeJobPreferences({
        ...current,
        [field]: [...current[field], ...values],
        no_preference: current.no_preference.filter((item) => item !== field),
      }),
    );
    setPreferenceInputs((current) => ({ ...current, [field]: "" }));
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function removePreferenceListItem(field: PreferenceListField, value: string) {
    setPreferencesDraft((current) =>
      normalizeJobPreferences({
        ...current,
        [field]: current[field].filter((item) => item !== value),
      }),
    );
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function togglePreferenceOption<Field extends "seniority" | "work_formats" | "employment_types" | "company_sizes" | "priorities">(
    field: Field,
    value: string,
  ) {
    setPreferencesDraft((current) => {
      const existingValues = current[field];
      return normalizeJobPreferences({
        ...current,
        [field]: existingValues.includes(value)
          ? existingValues.filter((item) => item !== value)
          : [...existingValues, value],
        no_preference: current.no_preference.filter((item) => item !== field),
      });
    });
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  function setPreferenceAny(field: PreferenceAnyField) {
    setPreferencesDraft((current) => {
      const nextPreferences = normalizeJobPreferences({
        ...current,
        no_preference: current.no_preference.includes(field)
          ? current.no_preference.filter((item) => item !== field)
          : [...current.no_preference, field],
      });

      if (!nextPreferences.no_preference.includes(field)) {
        return nextPreferences;
      }

      if (field === "salary") {
        nextPreferences.salary_min = "";
      } else if (field === "work_authorization") {
        nextPreferences.work_authorization = "";
      } else {
        nextPreferences[field] = [];
      }

      return nextPreferences;
    });
    setProfileSaveStatus("idle");
    setProfileSaveMessage("");
  }

  async function saveProfile() {
    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileDraft),
      });

      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Profile save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("Saved to database");
      setIsProfileDialogOpen(false);
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Profile save failed");
    }
  }

  async function saveExperience() {
    const normalizedExperience = normalizeExperienceEntry(experienceDraft);

    if (!normalizedExperience.title || !normalizedExperience.company) {
      setProfileSaveStatus("error");
      setProfileSaveMessage("Enter role title and company");
      return;
    }

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    const experienceEntries = parseExperienceEntries(profile.experience);
    const existingExperience = experienceEntries.some((entry) => entry.id === normalizedExperience.id);
    const nextExperienceEntries = existingExperience
      ? experienceEntries.map((entry) => (entry.id === normalizedExperience.id ? normalizedExperience : entry))
      : [...experienceEntries, normalizedExperience];
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      experience: serializeExperienceEntries(nextExperienceEntries),
    });

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Experience save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setIsExperienceDialogOpen(false);
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Experience save failed");
    }
  }

  async function saveEducation() {
    const normalizedEducation = normalizeEducationEntry(educationDraft);

    if (!normalizedEducation.institution || !normalizedEducation.credential) {
      setProfileSaveStatus("error");
      setProfileSaveMessage("Enter institution and credential");
      return;
    }

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    const educationEntries = parseEducationEntries(profile.education);
    const existingEducation = educationEntries.some((entry) => entry.id === normalizedEducation.id);
    const nextEducationEntries = existingEducation
      ? educationEntries.map((entry) => (entry.id === normalizedEducation.id ? normalizedEducation : entry))
      : [...educationEntries, normalizedEducation];
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      education: serializeEducationEntries(nextEducationEntries),
    });

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Education save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setIsEducationDialogOpen(false);
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Education save failed");
    }
  }

  async function saveDocument() {
    const normalizedDocument = normalizeDocumentEntry(documentDraft);

    if (!normalizedDocument.title) {
      setProfileSaveStatus("error");
      setProfileSaveMessage("Enter document title");
      return;
    }

    if (!normalizedDocument.data_url || !normalizedDocument.file_name) {
      setProfileSaveStatus("error");
      setProfileSaveMessage("Attach a file");
      return;
    }

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    const documentEntries = parseDocumentEntries(profile.documents);
    const existingDocument = documentEntries.some((entry) => entry.id === normalizedDocument.id);
    const nextDocumentEntries = existingDocument
      ? documentEntries.map((entry) => (entry.id === normalizedDocument.id ? normalizedDocument : entry))
      : [...documentEntries, normalizedDocument];
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      documents: serializeDocumentEntries(nextDocumentEntries),
    });

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Document save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setIsDocumentDialogOpen(false);
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Document save failed");
    }
  }

  async function savePreferences() {
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      job_preferences: serializeJobPreferences(preferencesDraft),
    });

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Preferences save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setIsPreferencesDialogOpen(false);
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Preferences save failed");
    }
  }

  async function saveSkills() {
    const normalizedSkills = Array.from(
      new Map(skillsDraft.map((skill) => [skill.trim().toLowerCase(), skill.trim()])).values(),
    ).filter(Boolean);
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      skills: normalizedSkills.join("\n"),
    });

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Skills save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setIsSkillsDialogOpen(false);
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Skills save failed");
    }
  }

  async function deleteExperience(experienceId: string) {
    const nextExperienceEntries = parseExperienceEntries(profile.experience).filter((entry) => entry.id !== experienceId);
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      experience: serializeExperienceEntries(nextExperienceEntries),
    });

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Experience delete failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Experience delete failed");
      window.alert(error instanceof Error ? error.message : "Experience delete failed");
    }
  }

  async function deleteEducation(educationId: string) {
    const nextEducationEntries = parseEducationEntries(profile.education).filter((entry) => entry.id !== educationId);
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      education: serializeEducationEntries(nextEducationEntries),
    });

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Education delete failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Education delete failed");
      window.alert(error instanceof Error ? error.message : "Education delete failed");
    }
  }

  async function deleteDocument(documentId: string) {
    const nextDocumentEntries = parseDocumentEntries(profile.documents).filter((entry) => entry.id !== documentId);
    const nextProfile = normalizeCandidateProfile({
      ...profile,
      documents: serializeDocumentEntries(nextDocumentEntries),
    });

    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!response.ok) {
        throw new Error(savedProfile.detail ?? "Document delete failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
    } catch (error) {
      setProfileSaveStatus("error");
      setProfileSaveMessage(error instanceof Error ? error.message : "Document delete failed");
      window.alert(error instanceof Error ? error.message : "Document delete failed");
    }
  }

  async function importExperienceFromCv() {
    if (!profile.resume_data_url || !profile.resume_file_name) {
      setExperienceImportMessage("Attach a resume first");
      window.alert("Attach a resume before importing experience.");
      return;
    }

    setIsExperienceImporting(true);
    setExperienceImportMessage("");
    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const importResponse = await fetch(`${apiBaseUrl}/profile/import-experience-from-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_file_name: profile.resume_file_name,
          resume_data_url: profile.resume_data_url,
        }),
      });
      const importResult = (await importResponse.json()) as ResumeExperienceImportResponse;

      if (!importResponse.ok) {
        throw new Error(importResult.detail ?? "Experience import failed");
      }

      const importedEntries = (importResult.experience ?? []).map((entry) =>
        normalizeExperienceEntry({
          ...entry,
          id: entry.id || createClientId("cv-experience"),
        }),
      );

      if (importedEntries.length === 0) {
        setProfileSaveStatus("ready");
        setExperienceImportMessage(importResult.message || "No experience entries were found in the attached CV");
        return;
      }

      const currentEntries = parseExperienceEntries(profile.experience);
      const mergedEntries = mergeExperienceEntries(currentEntries, importedEntries);
      const addedCount = mergedEntries.length - currentEntries.length;

      if (addedCount === 0) {
        setProfileSaveStatus("ready");
        setExperienceImportMessage("No new experience entries found in the attached CV");
        return;
      }

      const nextProfile = normalizeCandidateProfile({
        ...profile,
        experience: serializeExperienceEntries(mergedEntries),
      });
      const saveResponse = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await saveResponse.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!saveResponse.ok) {
        throw new Error(savedProfile.detail ?? "Experience import save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setExperienceImportMessage(
        importResult.message || `Imported ${addedCount} experience entr${addedCount === 1 ? "y" : "ies"} from CV`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Experience import failed";
      setProfileSaveStatus("error");
      setProfileSaveMessage(message);
      setExperienceImportMessage(message);
    } finally {
      setIsExperienceImporting(false);
    }
  }

  async function importEducationFromCv() {
    if (!profile.resume_data_url || !profile.resume_file_name) {
      setEducationImportMessage("Attach a resume first");
      window.alert("Attach a resume before importing education.");
      return;
    }

    setIsEducationImporting(true);
    setEducationImportMessage("");
    setProfileSaveStatus("loading");
    setProfileSaveMessage("");

    try {
      const importResponse = await fetch(`${apiBaseUrl}/profile/import-education-from-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_file_name: profile.resume_file_name,
          resume_data_url: profile.resume_data_url,
        }),
      });
      const importResult = (await importResponse.json()) as ResumeEducationImportResponse;

      if (!importResponse.ok) {
        throw new Error(importResult.detail ?? "Education import failed");
      }

      const importedEntries = (importResult.education ?? []).map((entry) =>
        normalizeEducationEntry({
          ...entry,
          id: entry.id || createClientId("cv-education"),
        }),
      );

      if (importedEntries.length === 0) {
        setProfileSaveStatus("ready");
        setEducationImportMessage(importResult.message || "No education entries were found in the attached CV");
        return;
      }

      const currentEntries = parseEducationEntries(profile.education);
      const mergedEntries = mergeEducationEntries(currentEntries, importedEntries);
      const addedCount = mergedEntries.length - currentEntries.length;

      if (addedCount === 0) {
        setProfileSaveStatus("ready");
        setEducationImportMessage("No new education entries found in the attached CV");
        return;
      }

      const nextProfile = normalizeCandidateProfile({
        ...profile,
        education: serializeEducationEntries(mergedEntries),
      });
      const saveResponse = await fetch(`${apiBaseUrl}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextProfile),
      });
      const savedProfile = (await saveResponse.json()) as Partial<CandidateProfile> & { detail?: string };

      if (!saveResponse.ok) {
        throw new Error(savedProfile.detail ?? "Education import save failed");
      }

      const normalizedProfile = normalizeCandidateProfile(savedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setProfileSaveStatus("ready");
      setProfileSaveMessage("");
      setEducationImportMessage(
        importResult.message || `Imported ${addedCount} education entr${addedCount === 1 ? "y" : "ies"} from CV`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Education import failed";
      setProfileSaveStatus("error");
      setProfileSaveMessage(message);
      setEducationImportMessage(message);
    } finally {
      setIsEducationImporting(false);
    }
  }

  function attachDocumentFile(file: File) {
    const allowedTypes = new Set([
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "image/png",
      "image/jpeg",
      "image/webp",
    ]);
    const allowedExtensions = [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp"];
    const lowerFileName = file.name.toLowerCase();
    const hasAllowedExtension = allowedExtensions.some((extension) => lowerFileName.endsWith(extension));

    if (!allowedTypes.has(file.type) && !hasAllowedExtension) {
      window.alert("Upload a PDF, DOC, DOCX, PNG, JPG, or WebP file.");
      return;
    }

    if (file.size > 5_000_000) {
      window.alert("Document file must be under 5MB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") return;

      const titleFromFile = file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim();
      setDocumentDraft((current) =>
        normalizeDocumentEntry({
          ...current,
          title: current.title || titleFromFile,
          file_name: file.name,
          file_size: formatFileSize(file.size),
          file_type: file.type || "application/octet-stream",
          uploaded_at: new Date().toISOString(),
          data_url: reader.result as string,
        }),
      );
      setProfileSaveStatus("idle");
      setProfileSaveMessage("");
    };
    reader.readAsDataURL(file);
  }

  async function saveResumeFile(file: File) {
    const allowedTypes = new Set([
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]);
    const allowedExtensions = [".pdf", ".doc", ".docx"];
    const hasAllowedExtension = allowedExtensions.some((extension) => file.name.toLowerCase().endsWith(extension));

    if (!allowedTypes.has(file.type) && !hasAllowedExtension) {
      window.alert("Upload a PDF, DOC, or DOCX resume.");
      return;
    }

    if (file.size > 5_000_000) {
      window.alert("Resume file must be under 5MB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = async () => {
      if (typeof reader.result !== "string") return;

      const nextProfile = normalizeCandidateProfile({
        ...profile,
        resume_file_name: file.name,
        resume_file_size: formatFileSize(file.size),
        resume_updated_at: new Date().toISOString(),
        resume_data_url: reader.result,
      });

      setProfile(nextProfile);
      setProfileDraft(nextProfile);

      try {
        const response = await fetch(`${apiBaseUrl}/profile`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(nextProfile),
        });
        const savedProfile = (await response.json()) as Partial<CandidateProfile> & { detail?: string };

        if (!response.ok) {
          throw new Error(savedProfile.detail ?? "Resume save failed");
        }

        const normalizedProfile = normalizeCandidateProfile(savedProfile);
        setProfile(normalizedProfile);
        setProfileDraft(normalizedProfile);
      } catch (error) {
        window.alert(error instanceof Error ? error.message : "Resume save failed");
      }
    };
    reader.readAsDataURL(file);
  }

  async function persistImportedJobs(importedJobs: Job[]) {
    window.localStorage.setItem(importedJobsStorageKey, JSON.stringify(importedJobs));

    try {
      await fetch(`${apiBaseUrl}/jobs`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jobs: importedJobs.map((job) => ({ id: job.id, data: job })),
        }),
      });
    } catch {
      // localStorage keeps imported jobs available even when the API is offline.
    }
  }

  function addParsedJobsToList(parsedJobs: ParsedJob[]) {
    const importedJobs = parsedJobs.map((job, index) => mapParsedJobToJob(job, index));

    if (importedJobs.length > 0) {
      setJobList((currentJobs) => {
        const nextJobs = mergeJobs(importedJobs, currentJobs);
        const nextImportedJobs = nextJobs.filter(isImportedJob);
        void persistImportedJobs(nextImportedJobs);
        return nextJobs;
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
        <AppSidebar activeView={activeView} onChangeView={changeView} profile={profile} />

        {activeView === "Dashboard" ? (
          <DashboardView onOpenJobs={() => changeView("Jobs")} />
        ) : activeView === "Profile" ? (
          <ProfileView
            profile={profile}
            onEditProfile={openProfileEditor}
            onAddExperience={() => openExperienceEditor()}
            onEditExperience={openExperienceEditor}
            onDeleteExperience={deleteExperience}
            onImportExperienceFromCv={importExperienceFromCv}
            isExperienceImporting={isExperienceImporting}
            experienceImportMessage={experienceImportMessage}
            onAddEducation={() => openEducationEditor()}
            onEditEducation={openEducationEditor}
            onDeleteEducation={deleteEducation}
            onImportEducationFromCv={importEducationFromCv}
            isEducationImporting={isEducationImporting}
            educationImportMessage={educationImportMessage}
            onAddDocument={() => openDocumentEditor()}
            onEditDocument={openDocumentEditor}
            onDeleteDocument={deleteDocument}
            onEditPreferences={openPreferencesEditor}
            onEditSkills={openSkillsEditor}
            onSaveResume={saveResumeFile}
          />
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
      {isProfileDialogOpen && (
        <ProfileEditorDialog
          profile={profileDraft}
          status={profileSaveStatus}
          message={profileSaveMessage}
          onChange={updateProfileDraft}
          onClose={() => setIsProfileDialogOpen(false)}
          onSave={saveProfile}
        />
      )}
      {isExperienceDialogOpen && (
        <ExperienceEditorDialog
          experience={experienceDraft}
          isEditMode={isExperienceEditMode}
          status={profileSaveStatus}
          message={profileSaveMessage}
          onChange={(field, value) => {
            setExperienceDraft((current) => ({ ...current, [field]: value }));
            setProfileSaveStatus("idle");
            setProfileSaveMessage("");
          }}
          onClose={() => setIsExperienceDialogOpen(false)}
          onSave={saveExperience}
        />
      )}
      {isEducationDialogOpen && (
        <EducationEditorDialog
          education={educationDraft}
          isEditMode={isEducationEditMode}
          status={profileSaveStatus}
          message={profileSaveMessage}
          onChange={(field, value) => {
            setEducationDraft((current) => ({ ...current, [field]: value }));
            setProfileSaveStatus("idle");
            setProfileSaveMessage("");
          }}
          onClose={() => setIsEducationDialogOpen(false)}
          onSave={saveEducation}
        />
      )}
      {isDocumentDialogOpen && (
        <DocumentEditorDialog
          document={documentDraft}
          isEditMode={isDocumentEditMode}
          status={profileSaveStatus}
          message={profileSaveMessage}
          onChange={(field, value) => {
            setDocumentDraft((current) => ({ ...current, [field]: value }));
            setProfileSaveStatus("idle");
            setProfileSaveMessage("");
          }}
          onAttachFile={attachDocumentFile}
          onClose={() => setIsDocumentDialogOpen(false)}
          onSave={saveDocument}
        />
      )}
      {isPreferencesDialogOpen && (
        <PreferencesEditorDialog
          preferences={preferencesDraft}
          inputs={preferenceInputs}
          status={profileSaveStatus}
          message={profileSaveMessage}
          onChange={updatePreferencesDraft}
          onInputChange={updatePreferenceInput}
          onAddListItem={addPreferenceListItem}
          onRemoveListItem={removePreferenceListItem}
          onToggleOption={togglePreferenceOption}
          onSetAny={setPreferenceAny}
          onClose={() => setIsPreferencesDialogOpen(false)}
          onSave={savePreferences}
        />
      )}
      {isSkillsDialogOpen && (
        <SkillsEditorDialog
          skills={skillsDraft}
          skillInput={skillInput}
          status={profileSaveStatus}
          message={profileSaveMessage}
          onSkillInputChange={(value) => {
            setSkillInput(value);
            setProfileSaveStatus("idle");
            setProfileSaveMessage("");
          }}
          onAddSkill={addSkillToDraft}
          onRemoveSkill={removeSkillFromDraft}
          onClose={() => setIsSkillsDialogOpen(false)}
          onSave={saveSkills}
        />
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
            Good morning!
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
                  <p>I can help you with:</p>
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

function getProfileLinks(profile: CandidateProfile) {
  return [
    { label: "LinkedIn", value: profile.linkedin, icon: Linkedin },
    { label: "GitHub", value: profile.github, icon: Github },
    { label: "Portfolio", value: profile.portfolio, icon: FileText },
    { label: "Personal Site", value: profile.personal_site, icon: Globe },
  ];
}

function ProfileView({
  profile,
  onEditProfile,
  onAddExperience,
  onEditExperience,
  onDeleteExperience,
  onImportExperienceFromCv,
  isExperienceImporting,
  experienceImportMessage,
  onAddEducation,
  onEditEducation,
  onDeleteEducation,
  onImportEducationFromCv,
  isEducationImporting,
  educationImportMessage,
  onAddDocument,
  onEditDocument,
  onDeleteDocument,
  onEditPreferences,
  onEditSkills,
  onSaveResume,
}: {
  profile: CandidateProfile;
  onEditProfile: () => void;
  onAddExperience: () => void;
  onEditExperience: (experience: ExperienceEntry) => void;
  onDeleteExperience: (experienceId: string) => void;
  onImportExperienceFromCv: () => void;
  isExperienceImporting: boolean;
  experienceImportMessage: string;
  onAddEducation: () => void;
  onEditEducation: (education: EducationEntry) => void;
  onDeleteEducation: (educationId: string) => void;
  onImportEducationFromCv: () => void;
  isEducationImporting: boolean;
  educationImportMessage: string;
  onAddDocument: () => void;
  onEditDocument: (document: DocumentEntry) => void;
  onDeleteDocument: (documentId: string) => void;
  onEditPreferences: () => void;
  onEditSkills: () => void;
  onSaveResume: (file: File) => void;
}) {
  return (
    <section className="job-scroll flex h-screen min-w-0 flex-1 flex-col overflow-y-auto px-3 py-3 sm:px-4 xl:px-4 2xl:px-5 2xl:py-4">
      <header className="mb-4 flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-[24px] font-bold leading-tight tracking-normal text-white sm:text-[27px] 2xl:text-[31px]">My Profile</h1>
          <p className="mt-1 text-[13px] text-muted 2xl:mt-1.5 2xl:text-base">Your professional profile and job preferences</p>
        </div>
      </header>

      <ProfileHero profile={profile} onEditProfile={onEditProfile} />

      <div className="mt-4 grid shrink-0 gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)] 2xl:gap-5">
        <div className="grid content-start gap-4 2xl:gap-5">
          <ResumePanel profile={profile} onSaveResume={onSaveResume} />
          <ExperiencePanel
            profile={profile}
            onAddExperience={onAddExperience}
            onEditExperience={onEditExperience}
            onDeleteExperience={onDeleteExperience}
            onImportExperienceFromCv={onImportExperienceFromCv}
            isExperienceImporting={isExperienceImporting}
            importMessage={experienceImportMessage}
          />
          <SkillsPanel profile={profile} onEditSkills={onEditSkills} />
          <EducationPanel
            profile={profile}
            onAddEducation={onAddEducation}
            onEditEducation={onEditEducation}
            onDeleteEducation={onDeleteEducation}
            onImportEducationFromCv={onImportEducationFromCv}
            isEducationImporting={isEducationImporting}
            importMessage={educationImportMessage}
          />
          <DocumentsPanel
            profile={profile}
            onAddDocument={onAddDocument}
            onEditDocument={onEditDocument}
            onDeleteDocument={onDeleteDocument}
          />
        </div>

        <aside className="grid content-start gap-4 2xl:gap-5">
          <ActivityPanel profile={profile} onEditProfile={onEditProfile} />
          <AiMatchProfilePanel profile={profile} onEditProfile={onEditProfile} />
          <PreferencesPanel profile={profile} onEditPreferences={onEditPreferences} />
          <DealbreakersPanel profile={profile} onEditProfile={onEditProfile} />
          <AdditionalNotesPanel profile={profile} onEditProfile={onEditProfile} />
        </aside>
      </div>
    </section>
  );
}

function ProfileHero({ profile, onEditProfile }: { profile: CandidateProfile; onEditProfile: () => void }) {
  const links = getProfileLinks(profile).filter((link) => hasProfileValue(link.value));

  return (
    <section className="panel grid shrink-0 overflow-hidden md:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[minmax(0,1fr)_410px]">
      <div className="relative flex flex-col gap-4 p-4 sm:flex-row sm:items-start sm:p-5 2xl:gap-5 2xl:p-6">
        <Button
          variant="ghost"
          className="absolute right-4 top-4 z-10 h-9 rounded-md border border-border bg-white/[0.03] px-3 text-xs font-bold text-[#e6ebf3] hover:bg-white/[0.075] sm:right-5 sm:top-5 2xl:h-10 2xl:px-4 2xl:text-[13px]"
          onClick={onEditProfile}
        >
          <Edit3 className="h-4 w-4" />
          Edit Profile
        </Button>
        <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-full bg-white/[0.06] ring-1 ring-white/10 2xl:h-28 2xl:w-28">
          <img
            src={profile.avatar_url || defaultCandidateProfile.avatar_url}
            alt={displayProfileValue(profile.name, "Profile avatar")}
            className="h-full w-full object-cover"
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-[24px] font-bold leading-tight text-white 2xl:text-[30px]">
              {displayProfileValue(profile.name, "Set up your profile")}
            </h2>
          </div>
          <p className="mt-2 text-base font-semibold text-[#d8dee8] 2xl:text-lg">
            {displayProfileValue(profile.current_role, "Add your current role")}
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm font-semibold text-muted 2xl:text-base">
            <span>Target role:</span>
            <button
              type="button"
              className="rounded-sm text-left font-bold text-accent transition hover:text-[#ff7a1a] focus:outline-none focus:ring-2 focus:ring-accent/45"
              onClick={onEditProfile}
            >
              {displayProfileValue(profile.desired_role, "Add the roles you want")}
            </button>
          </p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[13px] font-medium text-muted 2xl:text-sm">
            <span className="inline-flex items-center gap-1.5"><MapPin className="h-4 w-4" /> {displayProfileValue(profile.location, "Add location")}</span>
            <span className="inline-flex items-center gap-1.5"><Globe className="h-4 w-4" /> {displayProfileValue(profile.work_format, "Remote, hybrid, onsite")}</span>
          </div>
          {hasProfileValue(profile.headline) ? (
            <p className="mt-4 max-w-[720px] text-[13px] leading-5 text-[#c6ceda] 2xl:text-sm 2xl:leading-6">
              {profile.headline}
            </p>
          ) : (
            <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md border border-dashed border-white/[0.16] bg-white/[0.025] p-3">
              <p className="min-w-0 flex-1 text-[13px] leading-5 text-muted">
                Add a short summary so job matching can understand your background and goals.
              </p>
              <Button variant="ghost" className="h-8 rounded-md border border-border px-3 text-xs text-[#e6ebf3] hover:bg-white/[0.06]" onClick={onEditProfile}>
                <Plus className="h-4 w-4" />
                Add summary
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border p-4 md:border-l md:border-t-0 sm:p-5 2xl:p-6">
        <h3 className="text-sm font-bold text-white 2xl:text-base">Contact & Links</h3>
        {links.length > 0 ? (
          <div className="mt-3 grid gap-2.5 2xl:gap-3">
            {links.map((link) => (
              <a key={link.label} href="#" className="grid grid-cols-[36px_minmax(0,1fr)] items-center gap-3 rounded-md border border-transparent p-1.5 transition hover:border-white/[0.10] hover:bg-white/[0.035]">
                <span className="grid h-9 w-9 place-items-center rounded-md border border-border bg-white/[0.035] text-[#d8dee8]">
                  <link.icon className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] font-bold text-white 2xl:text-sm">{link.label}</span>
                  <span className="block truncate text-xs text-muted 2xl:text-[13px]">{link.value}</span>
                </span>
              </a>
            ))}
          </div>
        ) : (
          <EmptyProfileState
            className="mt-3"
            title="No links yet"
            description="Add LinkedIn, GitHub, portfolio, or a personal site."
            action="Add links"
            onAction={onEditProfile}
          />
        )}
      </div>
    </section>
  );
}

function EmptyProfileState({
  title,
  description,
  action,
  onAction,
  className,
}: {
  title: string;
  description: string;
  action: string;
  onAction: () => void;
  className?: string;
}) {
  return (
    <div className={cn("rounded-md border border-dashed border-white/[0.16] bg-white/[0.025] p-3", className)}>
      <p className="text-sm font-bold text-white">{title}</p>
      <p className="mt-1 text-xs leading-5 text-muted 2xl:text-[13px]">{description}</p>
      <Button
        type="button"
        variant="ghost"
        className="mt-3 h-8 rounded-md border border-border bg-transparent px-3 text-xs text-[#e6ebf3] hover:bg-white/[0.06]"
        onClick={onAction}
      >
        <Plus className="h-4 w-4" />
        {action}
      </Button>
    </div>
  );
}

function ResumeUploadButton({
  label,
  onSaveResume,
  className,
}: {
  label: string;
  onSaveResume: (file: File) => void;
  className?: string;
}) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border border-border text-[#e6ebf3] transition hover:bg-white/[0.06]", className)}>
      <Upload className="h-4 w-4" />
      {label}
      <input
        type="file"
        accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            onSaveResume(file);
          }
          event.currentTarget.value = "";
        }}
      />
    </label>
  );
}

function ResumePanel({ profile, onSaveResume }: { profile: CandidateProfile; onSaveResume: (file: File) => void }) {
  const hasResume = hasProfileValue(profile.resume_file_name);

  return (
    <section className="panel p-4 2xl:p-5">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-bold 2xl:text-lg">Resume / CV</h2>
      </div>
      {hasResume ? (
        <div className="mt-4 grid gap-3 rounded-md border border-border bg-white/[0.025] p-3 sm:grid-cols-[48px_minmax(0,1fr)_auto] sm:items-center">
          <div className="grid h-12 w-12 place-items-center rounded-md bg-[#ef4444] text-xs font-black text-white">
            {profile.resume_file_name.toLowerCase().endsWith(".pdf") ? "PDF" : "DOC"}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate text-sm font-bold text-white">{profile.resume_file_name}</p>
              <span className="rounded bg-success/18 px-2 py-0.5 text-[11px] font-bold text-success">Attached</span>
            </div>
            <p className="mt-1 text-xs font-medium text-muted">
              {profile.resume_updated_at ? `Updated ${formatProfileDate(profile.resume_updated_at)}` : "Attached"}
              {profile.resume_file_size ? ` • ${profile.resume_file_size}` : ""}
            </p>
          </div>
          <ResumeUploadButton
            label="Replace"
            onSaveResume={onSaveResume}
            className="h-9 px-3 text-xs font-semibold"
          />
        </div>
      ) : (
        <div className="mt-4 rounded-md border border-dashed border-white/[0.16] bg-white/[0.025] p-3">
          <p className="text-sm font-bold text-white">No resume uploaded</p>
          <p className="mt-1 text-xs leading-5 text-muted 2xl:text-[13px]">Attach a PDF, DOC, or DOCX resume. Maximum file size is 5MB.</p>
          <ResumeUploadButton
            label="Attach resume"
            onSaveResume={onSaveResume}
            className="mt-3 h-8 px-3 text-xs font-semibold"
          />
        </div>
      )}
    </section>
  );
}

function ExperiencePanel({
  profile,
  onAddExperience,
  onEditExperience,
  onDeleteExperience,
  onImportExperienceFromCv,
  isExperienceImporting,
  importMessage,
}: {
  profile: CandidateProfile;
  onAddExperience: () => void;
  onEditExperience: (experience: ExperienceEntry) => void;
  onDeleteExperience: (experienceId: string) => void;
  onImportExperienceFromCv: () => void;
  isExperienceImporting: boolean;
  importMessage: string;
}) {
  const experienceItems = parseExperienceEntries(profile.experience);
  const hasResume = hasProfileValue(profile.resume_data_url) && hasProfileValue(profile.resume_file_name);

  return (
    <section className="panel p-4 2xl:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-base font-bold 2xl:text-lg">Experience</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-xs font-bold text-[#e6ebf3] transition hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-45 2xl:text-[13px]"
            onClick={onImportExperienceFromCv}
            disabled={!hasResume || isExperienceImporting}
            title={hasResume ? "Import experience from attached CV" : "Attach a CV first"}
          >
            <FileText className="h-4 w-4" />
            {isExperienceImporting ? "Importing..." : "Import from CV"}
          </button>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-bold text-accent transition hover:bg-accent/10 hover:text-[#ff7a1a] 2xl:text-[13px]"
            onClick={onAddExperience}
          >
            <Plus className="h-4 w-4" />
            Add Experience
          </button>
        </div>
      </div>
      {importMessage && (
        <p className="mt-3 text-xs font-semibold text-muted 2xl:text-[13px]">{importMessage}</p>
      )}
      {experienceItems.length > 0 ? (
        <div className="mt-4 space-y-4">
          {experienceItems.map((item) => (
            <article key={item.id} className="grid grid-cols-[40px_minmax(0,1fr)_auto] gap-3 rounded-md border border-border bg-white/[0.025] p-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-white/[0.06] text-[#d8dee8]">
                <BriefcaseBusiness className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-white 2xl:text-base">{item.title}</h3>
                <p className="mt-0.5 text-[13px] font-semibold text-[#d8dee8] 2xl:text-sm">{item.company}</p>
                <p className="mt-1 text-xs text-muted 2xl:text-[13px]">
                  {[item.employment_type, item.location].filter(Boolean).join(" • ")}
                </p>
                <p className="mt-1 text-xs text-muted 2xl:text-[13px]">
                  {item.start_date || "Start date"} - {item.is_current ? "Present" : item.end_date || "End date"}
                </p>
                {item.description && (
                  <p className="mt-2 whitespace-pre-line text-[13px] leading-5 text-muted 2xl:text-sm">{item.description}</p>
                )}
              </div>
              <div className="flex shrink-0 gap-1">
                <button
                  type="button"
                  aria-label="Edit experience"
                  onClick={() => onEditExperience(item)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  aria-label="Delete experience"
                  onClick={() => onDeleteExperience(item.id)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-[#ff6b6b]/12 hover:text-[#ff7a7a]"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No experience yet"
          description="Add work, internship, freelance, or project experience in a structured format."
          action="Add experience"
          onAction={onAddExperience}
        />
      )}
    </section>
  );
}

function SkillsPanel({ profile, onEditSkills }: { profile: CandidateProfile; onEditSkills: () => void }) {
  const skillItems = parseProfileLines(profile.skills);

  return (
    <section className="panel p-4 2xl:p-5">
      <ProfileSectionHeader title="Skills" action="Edit Skills" onAction={onEditSkills} />
      {skillItems.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {skillItems.map((skill) => (
            <span key={skill} className="inline-flex min-h-7 items-center rounded-md border border-border bg-white/[0.035] px-2.5 text-xs font-semibold text-[#d8dee8]">
              {skill}
            </span>
          ))}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No skills yet"
          description="Add tools, technologies, languages, and strengths. Use one skill per line."
          action="Add skills"
          onAction={onEditSkills}
        />
      )}
    </section>
  );
}

function EducationPanel({
  profile,
  onAddEducation,
  onEditEducation,
  onDeleteEducation,
  onImportEducationFromCv,
  isEducationImporting,
  importMessage,
}: {
  profile: CandidateProfile;
  onAddEducation: () => void;
  onEditEducation: (education: EducationEntry) => void;
  onDeleteEducation: (educationId: string) => void;
  onImportEducationFromCv: () => void;
  isEducationImporting: boolean;
  importMessage: string;
}) {
  const educationItems = parseEducationEntries(profile.education);
  const hasResume = hasProfileValue(profile.resume_data_url) && hasProfileValue(profile.resume_file_name);

  return (
    <section className="panel p-4 2xl:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-base font-bold 2xl:text-lg">Education & Certifications</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-xs font-bold text-[#e6ebf3] transition hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-45 2xl:text-[13px]"
            onClick={onImportEducationFromCv}
            disabled={!hasResume || isEducationImporting}
            title={hasResume ? "Import education from attached CV" : "Attach a CV first"}
          >
            <FileText className="h-4 w-4" />
            {isEducationImporting ? "Importing..." : "Import from CV"}
          </button>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-bold text-accent transition hover:bg-accent/10 hover:text-[#ff7a1a] 2xl:text-[13px]"
            onClick={onAddEducation}
          >
            <Plus className="h-4 w-4" />
            Add Education
          </button>
        </div>
      </div>
      {importMessage && (
        <p className="mt-3 text-xs font-semibold text-muted 2xl:text-[13px]">{importMessage}</p>
      )}
      {educationItems.length > 0 ? (
        <div className="mt-4 space-y-4">
          {educationItems.map((item) => (
            <article key={item.id} className="grid grid-cols-[40px_minmax(0,1fr)_auto] gap-3 rounded-md border border-border bg-white/[0.025] p-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-white/[0.06] text-[#d8dee8]">
                <GraduationCap className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-white 2xl:text-base">
                  {item.credential || "Education"}
                </h3>
                <p className="mt-0.5 text-[13px] font-semibold text-[#d8dee8] 2xl:text-sm">
                  {item.institution || "Institution not specified"}
                </p>
                {(item.field_of_study || item.location) && (
                  <p className="mt-1 text-xs text-muted 2xl:text-[13px]">
                    {[item.field_of_study, item.location].filter(Boolean).join(" • ")}
                  </p>
                )}
                {(item.start_date || item.end_date || item.is_current) && (
                  <p className="mt-1 text-xs text-muted 2xl:text-[13px]">
                    {item.start_date || "Start date"} - {item.is_current ? "Present" : item.end_date || "End date"}
                  </p>
                )}
                {item.description && (
                  <p className="mt-2 whitespace-pre-line text-[13px] leading-5 text-muted 2xl:text-sm">{item.description}</p>
                )}
              </div>
              <div className="flex shrink-0 gap-1">
                <button
                  type="button"
                  aria-label="Edit education"
                  onClick={() => onEditEducation(item)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  aria-label="Delete education"
                  onClick={() => onDeleteEducation(item.id)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-[#ff6b6b]/12 hover:text-[#ff7a7a]"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No education added"
          description="Add degrees, courses, certifications, or relevant training."
          action="Add education"
          onAction={onAddEducation}
        />
      )}
    </section>
  );
}

function DocumentsPanel({
  profile,
  onAddDocument,
  onEditDocument,
  onDeleteDocument,
}: {
  profile: CandidateProfile;
  onAddDocument: () => void;
  onEditDocument: (document: DocumentEntry) => void;
  onDeleteDocument: (documentId: string) => void;
}) {
  const documentItems = parseDocumentEntries(profile.documents);

  return (
    <section className="panel p-4 2xl:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-bold 2xl:text-lg">Supporting Documents</h2>
          <p className="mt-1 text-xs font-medium text-muted 2xl:text-[13px]">Personal files you choose to reuse across applications.</p>
        </div>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-bold text-accent transition hover:bg-accent/10 hover:text-[#ff7a1a] 2xl:text-[13px]"
          onClick={onAddDocument}
        >
          <Plus className="h-4 w-4" />
          Add Document
        </button>
      </div>

      {documentItems.length > 0 ? (
        <div className="mt-4 space-y-4">
          {documentItems.map((item) => (
            <article key={item.id} className="grid grid-cols-[40px_minmax(0,1fr)_auto] gap-3 rounded-md border border-border bg-white/[0.025] p-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-white/[0.06] text-[#d8dee8]">
                <FileText className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="min-w-0 text-sm font-bold text-white 2xl:text-base">{item.title || item.file_name}</h3>
                  <span className="rounded bg-white/[0.06] px-2 py-0.5 text-[11px] font-bold text-muted">{item.category}</span>
                </div>
                {item.issuer && (
                  <p className="mt-0.5 text-[13px] font-semibold text-[#d8dee8] 2xl:text-sm">{item.issuer}</p>
                )}
                <p className="mt-1 truncate text-xs text-muted 2xl:text-[13px]">
                  {item.file_name}
                  {item.file_size ? ` • ${item.file_size}` : ""}
                  {item.uploaded_at ? ` • ${formatProfileDate(item.uploaded_at)}` : ""}
                </p>
                {item.notes && (
                  <p className="mt-2 whitespace-pre-line text-[13px] leading-5 text-muted 2xl:text-sm">{item.notes}</p>
                )}
              </div>
              <div className="flex shrink-0 gap-1">
                <a
                  aria-label="Download document"
                  href={item.data_url}
                  download={item.file_name || item.title}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
                >
                  <Download className="h-4 w-4" />
                </a>
                <button
                  type="button"
                  aria-label="Edit document"
                  onClick={() => onEditDocument(item)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  aria-label="Delete document"
                  onClick={() => onDeleteDocument(item.id)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-[#ff6b6b]/12 hover:text-[#ff7a7a]"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No supporting documents yet"
          description="Add diplomas, certificates, recommendations, permits, transcripts, portfolio PDFs, or other reusable files."
          action="Add document"
          onAction={onAddDocument}
        />
      )}
    </section>
  );
}

function ActivityPanel({ profile, onEditProfile }: { profile: CandidateProfile; onEditProfile: () => void }) {
  const completion = getProfileCompletion(profile);

  return (
    <section className="panel p-4 2xl:p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-bold 2xl:text-lg">Profile Snapshot</h2>
        <Button variant="ghost" size="sm" className="h-8 border border-border px-2 text-[11px] text-[#e6ebf3]" onClick={onEditProfile}>
          Edit
        </Button>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <MiniMetric icon={FileText} value={parseExperienceEntries(profile.experience).length.toString()} label="Experience" color="blue" />
        <MiniMetric icon={Star} value={parseProfileLines(profile.skills).length.toString()} label="Skills" color="orange" />
        <MiniMetric icon={Globe} value={getProfileLinks(profile).filter((link) => hasProfileValue(link.value)).length.toString()} label="Links" color="green" />
      </div>
      <div className="mt-4 rounded-md border border-border bg-white/[0.025] p-3">
        <div className="flex items-end gap-3">
          <p className="text-[28px] font-bold leading-none text-white">{completion}%</p>
          <p className="pb-1 text-xs font-medium text-muted">Profile completeness</p>
        </div>
        <div className="mt-3 h-2 rounded-full bg-white/[0.08]">
          <div className="h-full rounded-full bg-success" style={{ width: `${completion}%` }} />
        </div>
        <p className="mt-2 text-xs font-medium text-muted">
          {completion < 50 ? "Add basics, experience, and skills to improve matching." : "Profile has enough signal for better matching."}
        </p>
      </div>
    </section>
  );
}

function AiMatchProfilePanel({ profile, onEditProfile }: { profile: CandidateProfile; onEditProfile: () => void }) {
  const hasEnoughSignal = hasProfileValue(profile.current_role) && hasProfileValue(profile.desired_role) && parseProfileLines(profile.skills).length > 0;

  return (
    <section className="panel p-4 2xl:p-5">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-[#2f80ed]/20 text-sm font-black text-[#9cc6ff]">AI</span>
        <h2 className="text-base font-bold 2xl:text-lg">AI Match Profile</h2>
      </div>
      {hasEnoughSignal ? (
        <div className="mt-4 divide-y divide-border rounded-md border border-border">
          <AiProfileGroup title="Signals" icon={Check} iconClassName="text-success" items={[profile.current_role, profile.desired_role, `${parseProfileLines(profile.skills).length} skills added`]} />
          <AiProfileGroup title="Next gaps" icon={CircleDot} iconClassName="text-[#ffb020]" items={["Add quantified achievements", "Add preferred industries or countries", "Add dealbreakers"]} />
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="Not enough profile signal"
          description="Add your current role, target role, and a few skills to unlock useful match analysis."
          action="Add profile signal"
          onAction={onEditProfile}
        />
      )}
    </section>
  );
}

function PreferencesPanel({
  profile,
  onEditPreferences,
}: {
  profile: CandidateProfile;
  onEditPreferences: () => void;
}) {
  const preferences = parseJobPreferences(profile.job_preferences);
  const preferenceSummary = formatPreferenceSummary(preferences);

  return (
    <section className="panel p-4 2xl:p-5">
      <ProfileSectionHeader title="Job Preferences" action="Edit Preferences" onAction={onEditPreferences} />
      {preferenceSummary.length > 0 ? (
        <div className="mt-4 space-y-3">
          {preferenceSummary.map((group) => (
            <div key={group.label} className="rounded-md border border-border bg-white/[0.025] p-3">
              <p className="text-[11px] font-bold uppercase tracking-normal text-muted">{group.label}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {group.values.map((value) => (
                  <span key={value} className="inline-flex min-h-7 items-center rounded-md border border-border bg-white/[0.035] px-2.5 text-xs font-semibold text-[#d8dee8]">
                    {value}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No preferences set"
          description="Add desired roles, industries, countries, salary range, visa needs, or work format."
          action="Add preferences"
          onAction={onEditPreferences}
        />
      )}
    </section>
  );
}

function DealbreakersPanel({ profile, onEditProfile }: { profile: CandidateProfile; onEditProfile: () => void }) {
  const dealbreakers = parseProfileLines(profile.dealbreakers);

  return (
    <section className="panel p-4 2xl:p-5">
      <ProfileSectionHeader title="Dealbreakers" action="Edit Dealbreakers" onAction={onEditProfile} />
      {dealbreakers.length > 0 ? (
        <div className="mt-4 space-y-2.5">
          {dealbreakers.map((item) => (
          <p key={item} className="flex items-center gap-2 text-[13px] text-muted 2xl:text-sm">
            <Ban className="h-4 w-4 text-[#ff6b6b]" />
            {item}
          </p>
          ))}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No dealbreakers"
          description="Add hard limits such as onsite-only roles, industries, salary floor, or contract type."
          action="Add dealbreakers"
          onAction={onEditProfile}
        />
      )}
    </section>
  );
}

function AdditionalNotesPanel({ profile, onEditProfile }: { profile: CandidateProfile; onEditProfile: () => void }) {
  const completion = getProfileCompletion(profile);

  return (
    <section className="panel p-4 2xl:p-5">
      <ProfileSectionHeader title="Additional Notes" action="Edit Notes" onAction={onEditProfile} />
      {hasProfileValue(profile.additional_notes) ? (
        <div className="mt-4 whitespace-pre-line rounded-md border border-border bg-white/[0.025] p-3 text-[13px] leading-5 text-[#d8dee8]">
          {profile.additional_notes}
        </div>
      ) : (
        <EmptyProfileState
          className="mt-4"
          title="No notes"
          description="Add context that does not fit elsewhere: availability, motivation, constraints, or personal positioning."
          action="Add notes"
          onAction={onEditProfile}
        />
      )}
      <div className="mt-5">
        <div className="mb-2 flex justify-between text-xs font-semibold text-muted">
          <span>Profile completeness</span>
          <span className="text-white">{completion}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/[0.08]">
          <div className="h-full rounded-full bg-success" style={{ width: `${completion}%` }} />
        </div>
        <p className="mt-2 text-xs text-muted">
          {completion === 0 ? "Start with the basics, then add experience and skills." : "Keep adding details to improve job matching."}
        </p>
      </div>
    </section>
  );
}

function ProfileTextItem({ icon: Icon, text, compact = false }: { icon: typeof FileText; text: string; compact?: boolean }) {
  return (
    <div className={cn("grid gap-3 rounded-md border border-border bg-white/[0.025] p-3", compact ? "grid-cols-[24px_minmax(0,1fr)]" : "grid-cols-[32px_minmax(0,1fr)]")}>
      <Icon className="mt-0.5 h-5 w-5 text-[#d8dee8]" />
      <p className="min-w-0 text-[13px] leading-5 text-muted 2xl:text-sm">{text}</p>
    </div>
  );
}

function ProfileSectionHeader({ title, action, onAction }: { title: string; action: string; onAction: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <h2 className="text-base font-bold 2xl:text-lg">{title}</h2>
      <button type="button" className="text-xs font-bold text-accent transition hover:text-[#ff7a1a] 2xl:text-[13px]" onClick={onAction}>
        {action}
      </button>
    </div>
  );
}

function MiniMetric({ icon: Icon, value, label, color }: { icon: typeof FileText; value: string; label: string; color: "blue" | "orange" | "green" }) {
  return (
    <div className="rounded-md border border-border bg-white/[0.025] p-3">
      <Icon className={cn("h-5 w-5", color === "blue" ? "text-[#2f80ed]" : color === "green" ? "text-success" : "text-accent")} />
      <p className="mt-2 text-xl font-bold leading-none text-white">{value}</p>
      <p className="mt-1 text-[11px] text-muted">{label}</p>
    </div>
  );
}

function AiProfileGroup({ title, items, icon: Icon, iconClassName }: { title: string; items: string[]; icon: typeof Check; iconClassName: string }) {
  return (
    <div className="p-3">
      <h3 className="text-[13px] font-bold text-white">{title}</h3>
      <ul className="mt-2 space-y-1.5 text-[13px] text-muted">
        {items.map((item) => (
          <li key={item} className="flex items-center gap-2">
            <Icon className={cn("h-4 w-4", iconClassName)} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SkillsEditorDialog({
  skills,
  skillInput,
  status,
  message,
  onSkillInputChange,
  onAddSkill,
  onRemoveSkill,
  onClose,
  onSave,
}: {
  skills: string[];
  skillInput: string;
  status: "idle" | "loading" | "ready" | "error";
  message: string;
  onSkillInputChange: (value: string) => void;
  onAddSkill: (skill: string) => void;
  onRemoveSkill: (skill: string) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const normalizedQuery = skillInput.trim().toLowerCase();
  const availableSuggestions = suggestedSkills.filter(
    (suggestion) =>
      !skills.some((skill) => skill.toLowerCase() === suggestion.toLowerCase()) &&
      (!normalizedQuery || suggestion.toLowerCase().includes(normalizedQuery)),
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
      <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[720px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">Edit Skills</h2>
            <p className="mt-1 text-sm font-medium text-muted">Add skills one at a time, similar to LinkedIn.</p>
          </div>
          <button
            type="button"
            aria-label="Close skills editor"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border p-4">
          <form
            className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]"
            onSubmit={(event) => {
              event.preventDefault();
              onAddSkill(skillInput);
            }}
          >
            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Skill</span>
              <input
                value={skillInput}
                onChange={(event) => onSkillInputChange(event.target.value)}
                placeholder="e.g. Python, FastAPI, Docker"
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
              <span className="text-xs font-medium text-muted">Type to search suggestions, then click a chip or press Add.</span>
            </label>
            <Button
              type="submit"
              variant="ghost"
              className="mt-6 h-10 rounded-md border border-border bg-white/[0.035] px-4 text-[13px] text-[#e6ebf3] hover:bg-white/[0.07]"
            >
              <Plus className="h-4 w-4" />
              Add
            </Button>
          </form>

          <div className="mt-5">
            <h3 className="text-sm font-bold text-white">Selected skills</h3>
            {skills.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span key={skill} className="inline-flex min-h-8 items-center gap-2 rounded-md border border-border bg-white/[0.04] px-2.5 text-xs font-semibold text-[#d8dee8]">
                    {skill}
                    <button
                      type="button"
                      aria-label={`Remove ${skill}`}
                      className="inline-flex h-5 w-5 items-center justify-center rounded text-muted transition hover:bg-white/[0.08] hover:text-white"
                      onClick={() => onRemoveSkill(skill)}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-3 rounded-md border border-dashed border-white/[0.16] bg-white/[0.025] p-3 text-sm text-muted">
                No skills selected yet.
              </p>
            )}
          </div>

          <div className="mt-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-white">Suggested skills</h3>
              <p className="text-xs font-medium text-muted">
                {normalizedQuery ? `${availableSuggestions.length} matches` : `${availableSuggestions.length} available`}
              </p>
            </div>
            {availableSuggestions.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {availableSuggestions.map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    className="inline-flex min-h-8 items-center gap-1.5 rounded-md border border-border bg-white/[0.025] px-2.5 text-xs font-semibold text-[#d8dee8] transition hover:border-accent/60 hover:bg-accent/10 hover:text-white"
                    onClick={() => onAddSkill(skill)}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {skill}
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-3 rounded-md border border-dashed border-white/[0.16] bg-white/[0.025] p-3 text-sm text-muted">
                No suggestions match this search. Press Add to save it as a custom skill.
              </p>
            )}
          </div>
        </div>

        <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={cn("text-sm font-semibold", status === "error" ? "text-[#ff7a7a]" : "text-muted")}>
            {message || `${skills.length} skills selected`}
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
              disabled={status === "loading"}
              onClick={onSave}
            >
              <Save className="h-4 w-4" />
              {status === "loading" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ExperienceEditorDialog({
  experience,
  isEditMode,
  status,
  message,
  onChange,
  onClose,
  onSave,
}: {
  experience: ExperienceEntry;
  isEditMode: boolean;
  status: "idle" | "loading" | "ready" | "error";
  message: string;
  onChange: <Field extends keyof ExperienceEntry>(
    field: Field,
    value: ExperienceEntry[Field],
  ) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
      <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[760px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">
              {isEditMode ? "Edit Experience" : "Add Experience"}
            </h2>
            <p className="mt-1 text-sm font-medium text-muted">
              {isEditMode ? "Update this role, internship, freelance project, or relevant IT project." : "Add one role, internship, freelance project, or relevant IT project."}
            </p>
          </div>
          <button
            type="button"
            aria-label="Close experience editor"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Role title</span>
              <input
                value={experience.title}
                onChange={(event) => onChange("title", event.target.value)}
                placeholder="e.g. Junior Python Developer"
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Company / project</span>
              <input
                value={experience.company}
                onChange={(event) => onChange("company", event.target.value)}
                placeholder="Company name or project name"
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Employment type</span>
              <select
                value={experience.employment_type}
                onChange={(event) => onChange("employment_type", event.target.value)}
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
              >
                <option>Full-time</option>
                <option>Part-time</option>
                <option>Internship</option>
                <option>Freelance</option>
                <option>Contract</option>
                <option>Project</option>
              </select>
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Location</span>
              <input
                value={experience.location}
                onChange={(event) => onChange("location", event.target.value)}
                placeholder="Remote, Zurich, Switzerland..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Start date</span>
              <input
                type="month"
                value={experience.start_date}
                onChange={(event) => onChange("start_date", event.target.value)}
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">End date</span>
              <input
                type="month"
                value={experience.end_date}
                disabled={experience.is_current}
                onChange={(event) => onChange("end_date", event.target.value)}
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none disabled:opacity-45 focus:border-accent/70"
              />
            </label>

            <label className="flex items-start gap-3 rounded-md border border-border bg-white/[0.025] p-3 md:col-span-2">
              <input
                type="checkbox"
                checked={experience.is_current}
                onChange={(event) => {
                  onChange("is_current", event.target.checked);
                  if (event.target.checked) {
                    onChange("end_date", "");
                  }
                }}
                className="mt-1 h-4 w-4 accent-accent"
              />
              <span>
                <span className="block text-sm font-bold text-white">I currently work here</span>
                <span className="mt-1 block text-xs text-muted">End date will be shown as Present.</span>
              </span>
            </label>

            <label className="grid gap-2 md:col-span-2">
              <span className="text-xs font-bold text-[#d8dee8]">Description</span>
              <textarea
                value={experience.description}
                onChange={(event) => onChange("description", event.target.value)}
                placeholder="What did you build, support, automate, or improve?"
                rows={5}
                className="min-h-[128px] resize-none rounded-md border border-border bg-[#0d131a] px-3 py-2.5 text-sm font-semibold leading-5 text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>
          </div>
        </div>

        <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={cn("text-sm font-semibold", status === "error" ? "text-[#ff7a7a]" : "text-muted")}>
            {message || "Role title and company are required"}
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
              disabled={status === "loading"}
              onClick={onSave}
            >
              <Save className="h-4 w-4" />
              {status === "loading" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EducationEditorDialog({
  education,
  isEditMode,
  status,
  message,
  onChange,
  onClose,
  onSave,
}: {
  education: EducationEntry;
  isEditMode: boolean;
  status: "idle" | "loading" | "ready" | "error";
  message: string;
  onChange: <Field extends keyof EducationEntry>(
    field: Field,
    value: EducationEntry[Field],
  ) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
      <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[760px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">
              {isEditMode ? "Edit Education" : "Add Education"}
            </h2>
            <p className="mt-1 text-sm font-medium text-muted">
              {isEditMode ? "Update this degree, course, certification, or training." : "Add one degree, course, certification, or training."}
            </p>
          </div>
          <button
            type="button"
            aria-label="Close education editor"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Institution</span>
              <input
                value={education.institution}
                onChange={(event) => onChange("institution", event.target.value)}
                placeholder="University, school, provider..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Credential</span>
              <input
                value={education.credential}
                onChange={(event) => onChange("credential", event.target.value)}
                placeholder="Bachelor, certificate, course name..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Field of study</span>
              <input
                value={education.field_of_study}
                onChange={(event) => onChange("field_of_study", event.target.value)}
                placeholder="Computer Science, Data Analytics..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Location</span>
              <input
                value={education.location}
                onChange={(event) => onChange("location", event.target.value)}
                placeholder="Remote, Zurich, Switzerland..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Start date</span>
              <input
                type="month"
                value={education.start_date}
                onChange={(event) => onChange("start_date", event.target.value)}
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">End date</span>
              <input
                type="month"
                value={education.end_date}
                disabled={education.is_current}
                onChange={(event) => onChange("end_date", event.target.value)}
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none disabled:opacity-45 focus:border-accent/70"
              />
            </label>

            <label className="flex items-start gap-3 rounded-md border border-border bg-white/[0.025] p-3 md:col-span-2">
              <input
                type="checkbox"
                checked={education.is_current}
                onChange={(event) => {
                  onChange("is_current", event.target.checked);
                  if (event.target.checked) {
                    onChange("end_date", "");
                  }
                }}
                className="mt-1 h-4 w-4 accent-accent"
              />
              <span>
                <span className="block text-sm font-bold text-white">I currently study here</span>
                <span className="mt-1 block text-xs text-muted">End date will be shown as Present.</span>
              </span>
            </label>

            <label className="grid gap-2 md:col-span-2">
              <span className="text-xs font-bold text-[#d8dee8]">Details</span>
              <textarea
                value={education.description}
                onChange={(event) => onChange("description", event.target.value)}
                placeholder="Relevant coursework, honors, thesis, certification ID, or training details..."
                rows={5}
                className="min-h-[128px] resize-none rounded-md border border-border bg-[#0d131a] px-3 py-2.5 text-sm font-semibold leading-5 text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>
          </div>
        </div>

        <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={cn("text-sm font-semibold", status === "error" ? "text-[#ff7a7a]" : "text-muted")}>
            {message || "Institution and credential are required"}
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
              disabled={status === "loading"}
              onClick={onSave}
            >
              <Save className="h-4 w-4" />
              {status === "loading" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DocumentEditorDialog({
  document,
  isEditMode,
  status,
  message,
  onChange,
  onAttachFile,
  onClose,
  onSave,
}: {
  document: DocumentEntry;
  isEditMode: boolean;
  status: "idle" | "loading" | "ready" | "error";
  message: string;
  onChange: <Field extends keyof DocumentEntry>(
    field: Field,
    value: DocumentEntry[Field],
  ) => void;
  onAttachFile: (file: File) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
      <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[720px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">
              {isEditMode ? "Edit Document" : "Add Document"}
            </h2>
            <p className="mt-1 text-sm font-medium text-muted">Label a reusable personal file and attach it to your profile library.</p>
          </div>
          <button
            type="button"
            aria-label="Close document editor"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Document title</span>
              <input
                value={document.title}
                onChange={(event) => onChange("title", event.target.value)}
                placeholder="Swiss work permit, AWS certificate..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Type</span>
              <select
                value={document.category}
                onChange={(event) => onChange("category", event.target.value)}
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
              >
                {documentCategories.map((category) => (
                  <option key={category}>{category}</option>
                ))}
              </select>
            </label>

            <label className="grid gap-2 md:col-span-2">
              <span className="text-xs font-bold text-[#d8dee8]">Issued by / source</span>
              <input
                value={document.issuer}
                onChange={(event) => onChange("issuer", event.target.value)}
                placeholder="University, certification provider, employer, immigration office..."
                className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>

            <div className="rounded-md border border-border bg-white/[0.025] p-3 md:col-span-2">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-white">Attached file</p>
                  <p className="mt-1 truncate text-xs text-muted">
                    {document.file_name ? `${document.file_name}${document.file_size ? ` • ${document.file_size}` : ""}` : "PDF, DOC, DOCX, PNG, JPG, or WebP under 5MB"}
                  </p>
                </div>
                <label className="inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-md border border-border bg-white/[0.035] px-3 text-xs font-semibold text-[#e6ebf3] transition hover:bg-white/[0.07]">
                  <Upload className="h-4 w-4" />
                  {document.file_name ? "Replace file" : "Attach file"}
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg,image/webp"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) {
                        onAttachFile(file);
                      }
                      event.currentTarget.value = "";
                    }}
                  />
                </label>
              </div>
            </div>

            <label className="grid gap-2 md:col-span-2">
              <span className="text-xs font-bold text-[#d8dee8]">Notes</span>
              <textarea
                value={document.notes}
                onChange={(event) => onChange("notes", event.target.value)}
                placeholder="When to use it, expiration date, original language, or anything important..."
                rows={4}
                className="min-h-[112px] resize-none rounded-md border border-border bg-[#0d131a] px-3 py-2.5 text-sm font-semibold leading-5 text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>
          </div>
        </div>

        <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={cn("text-sm font-semibold", status === "error" ? "text-[#ff7a7a]" : "text-muted")}>
            {message || "Title and file are required"}
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
              disabled={status === "loading"}
              onClick={onSave}
            >
              <Save className="h-4 w-4" />
              {status === "loading" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PreferencesEditorDialog({
  preferences,
  inputs,
  status,
  message,
  onChange,
  onInputChange,
  onAddListItem,
  onRemoveListItem,
  onToggleOption,
  onSetAny,
  onClose,
  onSave,
}: {
  preferences: JobPreferences;
  inputs: PreferenceInputs;
  status: "idle" | "loading" | "ready" | "error";
  message: string;
  onChange: <Field extends keyof JobPreferences>(
    field: Field,
    value: JobPreferences[Field],
  ) => void;
  onInputChange: (field: PreferenceListField, value: string) => void;
  onAddListItem: (field: PreferenceListField) => void;
  onRemoveListItem: (field: PreferenceListField, value: string) => void;
  onToggleOption: (
    field: PreferenceToggleField,
    value: string,
  ) => void;
  onSetAny: (field: PreferenceAnyField) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
      <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[880px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">Edit Job Preferences</h2>
            <p className="mt-1 text-sm font-medium text-muted">Define the roles and conditions that should guide search, matching, and recommendations.</p>
          </div>
          <button
            type="button"
            aria-label="Close preferences editor"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border p-4">
          <div className="grid gap-4">
            {(Object.keys(preferenceListLabels) as PreferenceListField[]).map((field) => (
              <PreferenceListEditor
                key={field}
                field={field}
                values={preferences[field]}
                inputValue={inputs[field]}
                isAny={preferences.no_preference.includes(field)}
                onInputChange={onInputChange}
                onAdd={onAddListItem}
                onRemove={onRemoveListItem}
                onSetAny={onSetAny}
              />
            ))}

            <PreferenceToggleGroup
              title="Seniority"
              field="seniority"
              options={preferenceOptions.seniority}
              selectedValues={preferences.seniority}
              isAny={preferences.no_preference.includes("seniority")}
              onToggle={onToggleOption}
              onSetAny={onSetAny}
            />
            <PreferenceToggleGroup
              title="Work format"
              field="work_formats"
              options={preferenceOptions.work_formats}
              selectedValues={preferences.work_formats}
              isAny={preferences.no_preference.includes("work_formats")}
              onToggle={onToggleOption}
              onSetAny={onSetAny}
            />
            <PreferenceToggleGroup
              title="Employment type"
              field="employment_types"
              options={preferenceOptions.employment_types}
              selectedValues={preferences.employment_types}
              isAny={preferences.no_preference.includes("employment_types")}
              onToggle={onToggleOption}
              onSetAny={onSetAny}
            />
            <PreferenceToggleGroup
              title="Company size"
              field="company_sizes"
              options={preferenceOptions.company_sizes}
              selectedValues={preferences.company_sizes}
              isAny={preferences.no_preference.includes("company_sizes")}
              onToggle={onToggleOption}
              onSetAny={onSetAny}
            />
            <PreferenceToggleGroup
              title="Search priority"
              field="priorities"
              options={preferenceOptions.priorities}
              selectedValues={preferences.priorities}
              isAny={preferences.no_preference.includes("priorities")}
              onToggle={onToggleOption}
              onSetAny={onSetAny}
            />

            <div className="grid gap-4 rounded-md border border-border bg-white/[0.025] p-3 sm:grid-cols-[130px_minmax(0,1fr)]">
              <label className="grid gap-2">
                <span className="text-xs font-bold text-[#d8dee8]">Currency</span>
                <select
                  value={preferences.salary_currency}
                  onChange={(event) => onChange("salary_currency", event.target.value)}
                  className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none focus:border-accent/70"
                >
                  {["CHF", "EUR", "USD", "GBP"].map((currency) => (
                    <option key={currency}>{currency}</option>
                  ))}
                </select>
              </label>
              <label className="grid gap-2">
                <span className="text-xs font-bold text-[#d8dee8]">Minimum salary</span>
                <input
                  inputMode="numeric"
                  value={preferences.salary_min}
                  disabled={preferences.no_preference.includes("salary")}
                  onChange={(event) => onChange("salary_min", event.target.value.replace(/[^\d\s.,']/g, ""))}
                  placeholder="90000"
                  className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 disabled:opacity-45 focus:border-accent/70"
                />
              </label>
              <button
                type="button"
                className={cn(
                  "inline-flex min-h-9 items-center justify-center rounded-md border px-3 text-xs font-bold transition sm:col-span-2",
                  preferences.no_preference.includes("salary")
                    ? "border-accent/65 bg-accent/14 text-white"
                    : "border-border bg-white/[0.025] text-[#d8dee8] hover:border-accent/45 hover:bg-accent/10",
                )}
                onClick={() => onSetAny("salary")}
              >
                No salary preference
              </button>
            </div>

            <label className="grid gap-2 rounded-md border border-border bg-white/[0.025] p-3">
              <span className="text-xs font-bold text-[#d8dee8]">Work authorization</span>
              <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_180px]">
                <select
                  value={preferences.work_authorization}
                  disabled={preferences.no_preference.includes("work_authorization")}
                  onChange={(event) => onChange("work_authorization", event.target.value)}
                  className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none disabled:opacity-45 focus:border-accent/70"
                >
                  <option value="">Not specified</option>
                  {preferenceOptions.work_authorization.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className={cn(
                    "inline-flex min-h-10 items-center justify-center rounded-md border px-3 text-xs font-bold transition",
                    preferences.no_preference.includes("work_authorization")
                      ? "border-accent/65 bg-accent/14 text-white"
                      : "border-border bg-white/[0.025] text-[#d8dee8] hover:border-accent/45 hover:bg-accent/10",
                  )}
                  onClick={() => onSetAny("work_authorization")}
                >
                  No preference
                </button>
              </div>
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-bold text-[#d8dee8]">Notes</span>
              <textarea
                value={preferences.notes}
                onChange={(event) => onChange("notes", event.target.value)}
                placeholder="Availability, preferred tech stack, relocation timing, or other matching context..."
                rows={4}
                className="min-h-[112px] resize-none rounded-md border border-border bg-[#0d131a] px-3 py-2.5 text-sm font-semibold leading-5 text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
              />
            </label>
          </div>
        </div>

        <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={cn("text-sm font-semibold", status === "error" ? "text-[#ff7a7a]" : "text-muted")}>
            {message || "Empty preferences stay hidden"}
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
              disabled={status === "loading"}
              onClick={onSave}
            >
              <Save className="h-4 w-4" />
              {status === "loading" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PreferenceListEditor({
  field,
  values,
  inputValue,
  isAny,
  onInputChange,
  onAdd,
  onRemove,
  onSetAny,
}: {
  field: PreferenceListField;
  values: string[];
  inputValue: string;
  isAny: boolean;
  onInputChange: (field: PreferenceListField, value: string) => void;
  onAdd: (field: PreferenceListField) => void;
  onRemove: (field: PreferenceListField, value: string) => void;
  onSetAny: (field: PreferenceAnyField) => void;
}) {
  const config = preferenceListLabels[field];
  const suggestionListId = `${field}-suggestions`;

  return (
    <div className="rounded-md border border-border bg-white/[0.025] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-bold text-[#d8dee8]">{config.label}</p>
        <button
          type="button"
          className={cn(
            "inline-flex min-h-7 items-center rounded-md border px-2.5 text-[11px] font-bold transition",
            isAny
              ? "border-accent/65 bg-accent/14 text-white"
              : "border-border bg-white/[0.025] text-muted hover:border-accent/45 hover:bg-accent/10 hover:text-[#d8dee8]",
          )}
          onClick={() => onSetAny(field)}
        >
          No preference
        </button>
      </div>
      <div className="mt-2 flex gap-2">
        <input
          value={inputValue}
          disabled={isAny}
          list={suggestionListId}
          onChange={(event) => onInputChange(field, event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAdd(field);
            }
          }}
          placeholder={config.placeholder}
          className="h-9 min-w-0 flex-1 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 disabled:opacity-45 focus:border-accent/70"
        />
        <datalist id={suggestionListId}>
          {preferenceSuggestions[field].map((suggestion) => (
            <option key={suggestion} value={suggestion} />
          ))}
        </datalist>
        <button
          type="button"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border text-[#e6ebf3] transition hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-45"
          onClick={() => onAdd(field)}
          disabled={isAny}
          aria-label={`Add ${config.label.toLowerCase()}`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {isAny && (
        <p className="mt-3 rounded-md border border-accent/25 bg-accent/10 px-3 py-2 text-xs font-semibold text-[#ffd1b0]">
          Any {config.label.toLowerCase()} is acceptable.
        </p>
      )}
      {values.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {values.map((value) => (
            <button
              key={value}
              type="button"
              className="inline-flex min-h-7 items-center gap-1.5 rounded-md border border-border bg-white/[0.04] px-2.5 text-xs font-semibold text-[#d8dee8] transition hover:border-[#ff6b6b]/50 hover:text-white"
              onClick={() => onRemove(field, value)}
            >
              {value}
              <X className="h-3.5 w-3.5 text-muted" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PreferenceToggleGroup({
  title,
  field,
  options,
  selectedValues,
  isAny,
  onToggle,
  onSetAny,
  className,
}: {
  title: string;
  field: PreferenceToggleField;
  options: string[];
  selectedValues: string[];
  onToggle: (
    field: PreferenceToggleField,
    value: string,
  ) => void;
  isAny: boolean;
  onSetAny: (field: PreferenceAnyField) => void;
  className?: string;
}) {
  return (
    <div className={cn("rounded-md border border-border bg-white/[0.025] p-3", className)}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-bold text-[#d8dee8]">{title}</p>
        <button
          type="button"
          className={cn(
            "inline-flex min-h-7 items-center rounded-md border px-2.5 text-[11px] font-bold transition",
            isAny
              ? "border-accent/65 bg-accent/14 text-white"
              : "border-border bg-white/[0.025] text-muted hover:border-accent/45 hover:bg-accent/10 hover:text-[#d8dee8]",
          )}
          onClick={() => onSetAny(field)}
        >
          No preference
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => {
          const isSelected = selectedValues.includes(option) && !isAny;
          return (
            <button
              key={option}
              type="button"
              className={cn(
                "inline-flex min-h-8 items-center rounded-md border px-2.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-45",
                isSelected
                  ? "border-accent/65 bg-accent/14 text-white"
                  : "border-border bg-white/[0.025] text-[#d8dee8] hover:border-accent/45 hover:bg-accent/10",
              )}
              disabled={isAny}
              onClick={() => onToggle(field, option)}
            >
              {option}
            </button>
          );
        })}
      </div>
      {isAny && (
        <p className="mt-3 rounded-md border border-accent/25 bg-accent/10 px-3 py-2 text-xs font-semibold text-[#ffd1b0]">
          Any {title.toLowerCase()} is acceptable.
        </p>
      )}
    </div>
  );
}

function ProfileEditorDialog({
  profile,
  status,
  message,
  onChange,
  onClose,
  onSave,
}: {
  profile: CandidateProfile;
  status: "idle" | "loading" | "ready" | "error";
  message: string;
  onChange: <Field extends keyof CandidateProfile>(
    field: Field,
    value: CandidateProfile[Field],
  ) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const fields: Array<{
    field: keyof CandidateProfile;
    label: string;
    placeholder: string;
    type?: "input" | "textarea";
  }> = [
    { field: "name", label: "Name", placeholder: "Your full name" },
    { field: "current_role", label: "Current role", placeholder: "Frontend Engineer, Product Manager, Student..." },
    { field: "desired_role", label: "Target role", placeholder: "Roles you want to apply for" },
    { field: "location", label: "Location", placeholder: "City, country, timezone, or remote" },
    { field: "work_format", label: "Work format", placeholder: "Remote, hybrid, onsite, relocation" },
    { field: "headline", label: "Headline / summary", placeholder: "Short positioning statement", type: "textarea" },
    { field: "linkedin", label: "LinkedIn", placeholder: "linkedin.com/in/username" },
    { field: "github", label: "GitHub", placeholder: "github.com/username" },
    { field: "portfolio", label: "Portfolio", placeholder: "portfolio.com" },
    { field: "personal_site", label: "Personal site", placeholder: "your-site.com" },
  ];

  function handleAvatarFile(file: File | undefined) {
    if (!file) return;

    if (file.size > 1_000_000) {
      window.alert("Avatar image must be under 1MB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        onChange("avatar_url", reader.result);
      }
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-3 py-4 backdrop-blur-sm">
      <div className="panel flex max-h-[calc(100vh-32px)] w-full max-w-[820px] flex-col overflow-hidden border-white/[0.11] bg-[#111820]/96 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.52)] sm:p-5">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-bold leading-tight text-white 2xl:text-[24px]">Edit Profile</h2>
            <p className="mt-1 text-sm font-medium text-muted">Add the details you want job matching and applications to use.</p>
          </div>
          <button
            type="button"
            aria-label="Close profile editor"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="job-scroll mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-border p-4">
          <div className="mb-5 flex flex-col gap-4 rounded-md border border-border bg-white/[0.025] p-4 sm:flex-row sm:items-center">
            <img
              src={profile.avatar_url || defaultCandidateProfile.avatar_url}
              alt=""
              className="h-20 w-20 shrink-0 rounded-full object-cover ring-1 ring-white/10"
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-white">Avatar</p>
              <p className="mt-1 text-xs leading-5 text-muted">Default is the pug image. Upload PNG, JPG, WebP, GIF, or SVG under 1MB.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <label className="inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-md border border-border bg-white/[0.035] px-3 text-xs font-semibold text-[#e6ebf3] transition hover:bg-white/[0.07]">
                  <Upload className="h-4 w-4" />
                  Change Avatar
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
                    className="hidden"
                    onChange={(event) => handleAvatarFile(event.target.files?.[0])}
                  />
                </label>
                <button
                  type="button"
                  className="inline-flex h-9 items-center justify-center rounded-md border border-border bg-transparent px-3 text-xs font-semibold text-[#e6ebf3] transition hover:bg-white/[0.06]"
                  onClick={() => onChange("avatar_url", defaultCandidateProfile.avatar_url)}
                >
                  Use Default
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {fields.map((item) => (
              <label
                key={item.field}
                className={cn("grid gap-2", item.type === "textarea" && "md:col-span-2")}
              >
                <span className="text-xs font-bold text-[#d8dee8]">{item.label}</span>
                {item.type === "textarea" ? (
                  <textarea
                    value={profile[item.field]}
                    onChange={(event) => onChange(item.field, event.target.value)}
                    placeholder={item.placeholder}
                    rows={4}
                    className="min-h-[112px] resize-none rounded-md border border-border bg-[#0d131a] px-3 py-2.5 text-sm font-semibold leading-5 text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
                  />
                ) : (
                  <input
                    value={profile[item.field]}
                    onChange={(event) => onChange(item.field, event.target.value)}
                    placeholder={item.placeholder}
                    className="h-10 rounded-md border border-border bg-[#0d131a] px-3 text-sm font-semibold text-white outline-none placeholder:text-muted/70 focus:border-accent/70"
                  />
                )}
              </label>
            ))}
          </div>
        </div>

        <div className="mt-4 flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={cn("text-sm font-semibold", status === "error" ? "text-[#ff7a7a]" : "text-muted")}>
            {message || "Empty fields stay hidden on the profile page"}
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="h-10 rounded-md border border-border bg-transparent px-6 text-[13px] text-[#e6ebf3] hover:bg-white/[0.06]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="h-10 rounded-md bg-gradient-to-r from-[#ff5a00] to-[#ff3d00] px-7 text-[13px] text-white shadow-[0_12px_28px_rgba(255,90,0,0.25)] hover:from-[#ff6a14] hover:to-[#ff4a12]"
              disabled={status === "loading"}
              onClick={onSave}
            >
              <Save className="h-4 w-4" />
              {status === "loading" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AppSidebar({
  activeView,
  onChangeView,
  profile,
}: {
  activeView: View;
  onChangeView: (view: View) => void;
  profile: CandidateProfile;
}) {
  return (
    <aside className="app-sidebar hidden h-screen w-[190px] shrink-0 overflow-y-auto border-r border-border bg-white/[0.025] px-2.5 py-4 lg:flex lg:flex-col 2xl:w-[220px] 2xl:px-3 2xl:py-5">
      <div className="app-sidebar-brand mb-5 flex items-center gap-2.5 px-2 2xl:mb-7 2xl:gap-3">
        <img
          src="/brand/tasko-mark.png"
          alt=""
          className="app-sidebar-mark h-[52px] w-[52px] object-contain 2xl:h-[58px] 2xl:w-[58px]"
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
        <a
          href="#profile"
          onClick={() => onChangeView("Profile")}
          className={cn(
            "app-sidebar-profile mb-2 flex items-center gap-1.5 rounded-md px-1.5 py-1.5 text-left transition hover:bg-white/[0.055] 2xl:mb-3 2xl:gap-2",
            activeView === "Profile" && "border border-white/[0.12] bg-white/10 shadow-[inset_4px_0_0_#ff5a00]",
          )}
        >
          <img
            src={profile.avatar_url || defaultCandidateProfile.avatar_url}
            alt=""
            className="h-8 w-8 shrink-0 rounded-full object-cover 2xl:h-8 2xl:w-8"
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold leading-tight text-white 2xl:text-xs">
              {displayProfileFirstName(profile.name, "Set up profile")}
            </p>
            <p className="truncate text-[10px] leading-tight text-muted 2xl:text-[11px]">
              {displayProfileValue(profile.current_role, "Add your role")}
            </p>
          </div>
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted 2xl:h-4 2xl:w-4" />
        </a>
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

function CompanyLogo({ logo, large = false }: { logo: Job["logo"] | "airbnb"; large?: boolean }) {
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

  if (logo === "airbnb") {
    return (
      <div className={cn("grid shrink-0 place-items-center rounded-md bg-black text-[#ff385c]", sizeClass)}>
        <span className={cn("font-black", large ? "text-3xl 2xl:text-4xl" : "text-xl 2xl:text-2xl")}>A</span>
      </div>
    );
  }

  return (
    <div className={cn("grid shrink-0 place-items-center rounded-md bg-black font-black text-white", large ? "text-xl 2xl:text-2xl" : "text-base 2xl:text-xl", sizeClass)}>
      stripe
    </div>
  );
}
