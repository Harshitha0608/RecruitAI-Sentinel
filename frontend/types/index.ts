export interface HealthResponse {
  status: string;
}

export interface PrecomputeResponse {
  status: string;
  message: string;
}

export interface RankResponseItem {
  candidate_id: string;
  rank: number;
  score: number;
  reasoning: string;
  // Dynamic fields lazy-loaded in the frontend for Rankings table:
  name?: string;
  headline?: string;
  current_title?: string;
  current_company?: string;
  years_of_experience?: number;
  location?: string;
  is_honeypot?: boolean;
  score_breakdown?: ScoreBreakdown;
  open_to_work?: boolean;
  notice_period_days?: number;
  skills?: string[];
  critical_skills_matched?: string[];
  important_skills_matched?: string[];
  nice_to_have_skills_matched?: string[];
  missing_critical_skills?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
}

export interface RankResponse {
  success: boolean;
  candidates: RankResponseItem[];
}

export interface ScoreBreakdown {
  skill_score: number;
  experience_score: number;
  education_score: number;
  project_score: number;
  behavior_score: number;
  availability_score: number;
  engagement_bonus?: number;
  final_score: number;
}

export interface JobDescription {
  title: string;
  company: string;
  summary: string;
  requirements: string[];
  preferred_skills: string[];
  keywords: string[];
  technical_skills?: string[];
  education?: string;
  location?: string;
  employment_type?: string;
  experience_requirement?: {
    raw_text: string;
    min_years?: number;
    max_years?: number;
  };
}

export interface SkillSchema {
  name: string;
  proficiency: string;
  endorsements: number;
  duration_months: number;
}

export interface EducationSchema {
  institution: string;
  degree: string;
  field_of_study: string;
  start_year: number;
  end_year: number;
  grade?: string;
  tier: string;
}

export interface CertificationSchema {
  name: string;
  issuer: string;
  year: number;
}

export interface LanguageSchema {
  language: string;
  proficiency: string;
}

export interface ExpectedSalarySchema {
  min: number;
  max: number;
}

export interface RedrobSignalsSchema {
  profile_completeness_score: number;
  signup_date: string;
  last_active_date: string;
  open_to_work_flag: boolean;
  profile_views_received_30d: number;
  applications_submitted_30d: number;
  recruiter_response_rate: number;
  avg_response_time_hours: number;
  skill_assessment_scores: Record<string, number>;
  connection_count: number;
  endorsements_received: number;
  notice_period_days: number;
  expected_salary_range_inr_lpa: ExpectedSalarySchema;
  preferred_work_mode: string;
  willing_to_relocate: boolean;
  github_activity_score: number;
  search_appearance_30d: number;
  saved_by_recruiters_30d: number;
  interview_completion_rate: number;
  offer_acceptance_rate: number;
  verified_email: boolean;
  verified_phone: boolean;
  linkedin_connected: boolean;
}

export interface CareerHistorySchema {
  company: string;
  title: string;
  start_date: string;
  end_date?: string;
  duration_months: number;
  is_current: boolean;
  industry: string;
  company_size: string;
  description: string;
}

export interface CandidateDetailResponse {
  candidate_id: string;
  name: string;
  headline: string;
  summary: string;
  current_title: string;
  current_company: string;
  years_of_experience: number;
  location: string;
  is_honeypot: boolean;
  score_breakdown: ScoreBreakdown;
  reasoning: string;
  // Sub-objects for the Details page:
  skills?: SkillSchema[];
  education?: EducationSchema[];
  certifications?: CertificationSchema[];
  languages?: LanguageSchema[];
  career_history?: CareerHistorySchema[];
  behavioral_signals?: RedrobSignalsSchema;
  notice_period?: number;
  critical_skills_matched?: string[];
  important_skills_matched?: string[];
  nice_to_have_skills_matched?: string[];
  missing_critical_skills?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
}

export interface AnalyticsResponse {
  candidate_count: number;
  indexed_candidates: number;
  embedding_dimension: number;
  faiss_loaded: boolean;
  tfidf_loaded: boolean;
  model_loaded: boolean;
  retrieval_timings?: number[];
  ranking_timings?: number[];
  latest_retrieval_latency_ms?: number;
  latest_pipeline_runtime_ms?: number;
  latest_honeypot_rate?: number;
  sqlite_connected: boolean;
  top_missing_skills?: { name: string; count: number }[];
  top_universities?: { name: string; count: number }[];
  top_locations?: { name: string; count: number }[];
  work_mode_distribution?: { range: string; count: number }[];
  education_distribution?: { range: string; count: number }[];
}

export interface PrecomputeStatusResponse {
  status: string;
  progress: number;
  message: string;
}
