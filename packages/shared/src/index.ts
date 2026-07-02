export type ApplicationStatus =
  | "applied"
  | "interview"
  | "assessment"
  | "offer"
  | "rejected";

export type WorkMode = "remote" | "hybrid" | "onsite";

export interface JobRecommendation {
  id: string;
  title: string;
  company: string;
  workMode: WorkMode;
  employmentType: "full-time" | "part-time" | "contract";
  matchScore: number;
  postedAt: string;
}

export interface ApplicationSummary {
  total: number;
  applied: number;
  interviews: number;
  offers: number;
  rejected: number;
}
