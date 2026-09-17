"use client";

import React, { use, useCallback, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useApi } from "@/hooks/use-api";
import { apiService } from "@/services/api";
import { QueryLoader } from "@/components/query-loader";
import { CandidateDetailResponse, CareerHistorySchema, EducationSchema, SkillSchema, JobDescription } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  ArrowLeft,
  Briefcase,
  GraduationCap,
  Award,
  MapPin,
  TrendingUp,
  ShieldCheck,
  ShieldAlert,
  Calendar,
  DollarSign,
  Clock,
  Phone,
  Mail,
  Linkedin,
  Info,
  CheckCircle,
  AlertTriangle,
  UserCheck
} from "lucide-react";

export default function CandidateDetails() {
  const params = useParams();
  const router = useRouter();
  const candidateId = params.id as string;
  const [showAllSkills, setShowAllSkills] = React.useState<boolean>(false);

  const fetchCandidateDetail = useCallback(() => apiService.getCandidateDetail(candidateId), [candidateId]);
  const detailQuery = useApi<CandidateDetailResponse, []>(fetchCandidateDetail, true);

  const [candidate, setCandidate] = React.useState<any | null>(null);
  const [jd, setJd] = React.useState<JobDescription | null>(null);

  // Load from sessionStorage strictly as fallback / initial state (FIX 14)
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const cachedDetail = sessionStorage.getItem(`candidate_detail_${candidateId}`);
      if (cachedDetail) {
        setCandidate(JSON.parse(cachedDetail));
      } else {
        const cachedListItem = sessionStorage.getItem(`candidate_list_item_${candidateId}`);
        if (cachedListItem) {
          const parsedItem = JSON.parse(cachedListItem);
          setCandidate({
            candidate_id: parsedItem.candidate_id,
            name: parsedItem.name || `Candidate ${parsedItem.candidate_id}`,
            headline: parsedItem.current_title || "Software Engineer",
            summary: parsedItem.reasoning || "Factual screening results loaded.",
            current_title: parsedItem.current_title || "Software Engineer",
            current_company: parsedItem.current_company || "Company",
            years_of_experience: parsedItem.years_of_experience || 0,
            location: parsedItem.location || "Location",
            is_honeypot: parsedItem.is_honeypot || false,
            score_breakdown: parsedItem.score_breakdown,
            reasoning: parsedItem.reasoning || "",
            skills: (parsedItem.skills || []).map((s: string) => ({ name: s, proficiency: "advanced", endorsements: 0, duration_months: 0 })),
            career_history: [],
            education: [],
            behavioral_signals: {
              profile_completeness_score: 90,
              signup_date: "2020-01-01",
              last_active_date: "2026-06-01",
              open_to_work_flag: parsedItem.open_to_work || false,
              profile_views_received_30d: 0,
              applications_submitted_30d: 0,
              recruiter_response_rate: 0.9,
              avg_response_time_hours: 12,
              skill_assessment_scores: {},
              connection_count: 50,
              endorsements_received: 0,
              notice_period_days: parsedItem.notice_period_days || 0,
              expected_salary_range_inr_lpa: { min: 10, max: 20 },
              preferred_work_mode: "remote",
              willing_to_relocate: true,
              github_activity_score: 50,
              search_appearance_30d: 50,
              saved_by_recruiters_30d: 0,
              interview_completion_rate: 0.9,
              offer_acceptance_rate: 0.8,
              verified_email: true,
              verified_phone: true,
              linkedin_connected: true
            }
          });
        }
      }
      
      const cachedJd = sessionStorage.getItem("active_jd");
      if (cachedJd) {
        setJd(JSON.parse(cachedJd));
      }
    }
  }, [candidateId]);

  // Update candidate when backend returns response
  React.useEffect(() => {
    if (detailQuery.data) {
      setCandidate(detailQuery.data);
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`candidate_detail_${candidateId}`, JSON.stringify(detailQuery.data));
      }
    }
  }, [detailQuery.data, candidateId]);

  // Formatting and helpers
  const scoreBreakdown = candidate?.score_breakdown || {
    skill_score: 0,
    experience_score: 0,
    education_score: 0,
    project_score: 0,
    behavior_score: 0,
    availability_score: 0,
    final_score: 0,
  };

  const jdQuery = useApi<JobDescription, []>(apiService.getActiveJd, true);

  // Update JD when backend returns response
  React.useEffect(() => {
    if (jdQuery.data) {
      setJd(jdQuery.data);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("active_jd", JSON.stringify(jdQuery.data));
      }
    }
  }, [jdQuery.data]);

  const matchedRequirements = useMemo(() => {
    const activeJd = jd || jdQuery.data;
    if (!candidate || !activeJd) return [];
    
    const rawMatched = [
      ...(candidate.critical_skills_matched || []),
      ...(candidate.important_skills_matched || []),
      ...(candidate.nice_to_have_skills_matched || []),
      ...(candidate.matched_skills || [])
    ];
    const matchedSet = new Set(rawMatched.map((s: string) => s.split(" (via")[0].toLowerCase().trim()));

    const rawMissing = [
      ...(candidate.missing_skills || []),
      ...(candidate.missing_critical_skills || [])
    ];
    const missingSet = new Set(rawMissing.map((s: string) => s.split(" (via")[0].toLowerCase().trim()));

    const list: { name: string; required: boolean; matched: boolean }[] = [];
    
    const reqs = activeJd.requirements || [];
    reqs.forEach((r: string) => {
      const name = r.trim();
      if (!name) return;
      const nameLower = name.toLowerCase();
      let matched = false;
      const hasConstituentMatch = Array.from(matchedSet).some(m => {
        if (m.length < 2) return false;
        const escaped = m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`\\b${escaped}\\b`, 'i').test(nameLower);
      });
      if (missingSet.has(nameLower) && !hasConstituentMatch) {
        matched = false;
      } else if (matchedSet.has(nameLower) || hasConstituentMatch || Array.from(matchedSet).some(m => m === nameLower || m.includes(nameLower) || nameLower.includes(m))) {
        matched = true;
      }
      list.push({ name, required: true, matched });
    });
    
    const prefs = activeJd.preferred_skills || [];
    prefs.forEach((p: string) => {
      const name = p.trim();
      if (!name || name.toLowerCase() === "none specified") return;
      const nameLower = name.toLowerCase();
      let matched = false;
      const hasConstituentMatch = Array.from(matchedSet).some(m => {
        if (m.length < 2) return false;
        const escaped = m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`\\b${escaped}\\b`, 'i').test(nameLower);
      });
      if (missingSet.has(nameLower) && !hasConstituentMatch) {
        matched = false;
      } else if (matchedSet.has(nameLower) || hasConstituentMatch || Array.from(matchedSet).some(m => m === nameLower || m.includes(nameLower) || nameLower.includes(m))) {
        matched = true;
      }
      list.push({ name, required: false, matched });
    });
    
    return list;
  }, [candidate, jd, jdQuery.data]);

  const signals = candidate?.behavioral_signals;
  const career = candidate?.career_history || [];
  const education = candidate?.education || [];
  const skills = candidate?.skills || [];

  // Recruiter Advisor Banner
  const getEvaluationAdvice = () => {
    if (!candidate) return { action: "Pending", description: "" };
    
    if (candidate.is_honeypot) {
      return {
        action: "Do Not Interview",
        color: "text-destructive border-destructive/20 bg-destructive/5",
        description: "Profile flagged with critical chronological discrepancies in career history. Security verification failed."
      };
    }

    if (scoreBreakdown.final_score >= 80) {
      return {
        action: "Strong Candidate - Highly Recommended",
        color: "text-emerald-500 border-emerald-500/20 bg-emerald-500/5",
        description: "Solid technical alignment against job requirements. Strong background and verified candidate signals."
      };
    } else if (scoreBreakdown.final_score >= 60) {
      return {
        action: "Recommended for Preliminary Screening",
        color: "text-primary border-primary/20 bg-primary/5",
        description: "Good general compatibility. Recommended for initial recruiter screening."
      };
    } else {
      return {
        action: "Review Qualifications",
        color: "text-amber-500 border-amber-500/20 bg-amber-500/5",
        description: "Key requirements unverified or missing. Review candidate credentials manually."
      };
    }
  };

  const advice = getEvaluationAdvice();

  const strengthsList = useMemo(() => {
    const list: string[] = [];
    if (!candidate) return list;

    const matched = candidate.matched_skills 
      || [...(candidate.critical_skills_matched || []), ...(candidate.important_skills_matched || [])];

    if (matched.length > 0) {
      matched.forEach((s: string) => {
        const clean = s.split(" (via")[0].trim();
        list.push(`Verified coverage: ${clean}`);
      });
    } else {
      list.push("General technical domain background.");
    }
    
    if (!candidate.is_honeypot) {
      list.push("Timeline integrity clear: no duration anomalies.");
    }
    if (signals?.open_to_work_flag) {
      list.push("Actively seeking opportunities (Open to Work).");
    }
    return list;
  }, [candidate, signals]);

  const gapsList = useMemo(() => {
    const list: string[] = [];
    if (!candidate) return list;

    if (candidate.is_honeypot) {
      list.push("Chronological anomalies detected in career history duration records.");
    }
    
    const matchedRaw = [
      ...(candidate.critical_skills_matched || []),
      ...(candidate.important_skills_matched || []),
      ...(candidate.nice_to_have_skills_matched || []),
      ...(candidate.matched_skills || [])
    ];
    const matchedLower = matchedRaw.map((s: string) => s.split(" (via")[0].toLowerCase().trim());

    const isRequirementSatisfied = (cleanText: string) => {
      const textLower = cleanText.toLowerCase();
      if (matchedLower.includes(textLower)) return true;
      return matchedLower.some(m => {
        if (m.length < 2) return false;
        const escaped = m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`\\b${escaped}\\b`, 'i').test(textLower);
      });
    };

    const missing = candidate.missing_skills || candidate.missing_critical_skills || [];
    if (missing.length > 0) {
      missing.forEach((m: string) => {
        const clean = m.split(" (via")[0].trim();
        if (!isRequirementSatisfied(clean)) {
          list.push(`Lacks documented evidence for: ${clean}`);
        }
      });
    }

    if (signals && signals.notice_period_days >= 60) {
      list.push(`Long notice period requirement (${signals.notice_period_days} days).`);
    }
    return list;
  }, [candidate, signals]);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 py-4">
      {/* Top action header */}
      <div className="flex items-center gap-4 select-none">
        <Button variant="outline" size="icon" onClick={() => router.back()} className="h-9 w-9 border-border hover:bg-accent">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Candidate Profile</h1>
          <p className="text-muted-foreground font-mono text-sm">{candidateId}</p>
        </div>
      </div>

      <QueryLoader loading={detailQuery.loading && !candidate} error={detailQuery.error} retry={detailQuery.execute}>
        {candidate && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column: Core Profile Info */}
            <div className="lg:col-span-1 space-y-6">
              <Card className="border-border bg-card shadow-sm">
                <CardContent className="pt-6 space-y-4">
                  <div className="flex flex-col items-center justify-center text-center pb-4 border-b">
                    <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-2xl mb-3 border">
                      {candidate.name.split(" ").map((n: string) => n[0]).join("")}
                    </div>
                    <h2 className="text-xl font-bold text-foreground">{candidate.name}</h2>
                    <p className="text-sm text-primary font-medium mt-1">{candidate.current_title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{candidate.current_company}</p>
                    
                    {candidate.is_honeypot ? (
                      <Badge variant="destructive" className="mt-4 gap-1.5 whitespace-nowrap font-bold">
                        <ShieldAlert className="h-3.5 w-3.5" /> Flagged Risk
                      </Badge>
                    ) : (
                      <Badge variant="success" className="mt-4 gap-1.5 whitespace-nowrap font-bold">
                        <ShieldCheck className="h-3.5 w-3.5" /> Verified Clear
                      </Badge>
                    )}
                  </div>

                  <div className="space-y-3.5 py-2">
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <MapPin className="h-4 w-4 text-primary" />
                      <span>{candidate.location}</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <Briefcase className="h-4 w-4 text-primary" />
                      <span>{candidate.years_of_experience.toFixed(1)} Years of Experience</span>
                    </div>
                    {signals && (
                      <>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                          <DollarSign className="h-4 w-4 text-primary" />
                          <span>
                            INR {signals.expected_salary_range_inr_lpa.min}L -{" "}
                            {signals.expected_salary_range_inr_lpa.max}L Expected LPA
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                          <Clock className="h-4 w-4 text-primary" />
                          <span>
                            {signals.notice_period_days === 0 ? "Immediate Availability" : signals.notice_period_days <= 30 ? "Short Notice (≤30 days)" : `${signals.notice_period_days} Days Notice Period`}
                          </span>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Verification Badges */}
                  {signals && (
                    <div className="flex flex-wrap gap-2 pt-4 border-t">
                      {signals.verified_email && (
                        <Badge variant="outline" className="text-emerald-500 border-emerald-500/20 bg-emerald-500/5 whitespace-nowrap text-[10px] py-0.5">
                          <Mail className="h-3 w-3 mr-1" /> Email Verified
                        </Badge>
                      )}
                      {signals.verified_phone && (
                        <Badge variant="outline" className="text-emerald-500 border-emerald-500/20 bg-emerald-500/5 whitespace-nowrap text-[10px] py-0.5">
                          <Phone className="h-3 w-3 mr-1" /> Phone Verified
                        </Badge>
                      )}
                      {signals.linkedin_connected && (
                        <Badge variant="outline" className="text-indigo-400 border-indigo-500/20 bg-indigo-500/5 whitespace-nowrap text-[10px] py-0.5">
                          <Linkedin className="h-3 w-3 mr-1" /> LinkedIn Synced
                        </Badge>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Match Breakdown Card */}
              <Card className="border-border bg-card shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-1.5 text-sm font-bold text-foreground select-none">
                    Match Breakdown
                    <span className="relative group">
                      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-48 p-2 text-[10px] bg-slate-900 border border-border text-slate-100 rounded shadow-md font-normal tooltip-custom-fade z-50">
                        Visual breakdown of the candidate's skills relevance, tenure compliance, and behavioral engagement.
                      </span>
                    </span>
                  </CardTitle>
                  <CardDescription className="text-xs">Summary of evaluated credentials match</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-col items-center justify-center p-6 border rounded-xl bg-muted/20">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider flex items-center gap-1 select-none">
                      Sentinel Fit Score
                    </span>
                    <span className="text-3xl font-extrabold text-foreground mt-1.5 whitespace-nowrap">
                      {Math.round(scoreBreakdown.final_score)} / 100
                    </span>
                  </div>

                  <div className="space-y-3 pt-2">
                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span>Skills Match (40%)</span>
                        <span>{scoreBreakdown.skill_score.toFixed(1)}/40 ({Math.round((scoreBreakdown.skill_score / 40) * 100)}%)</span>
                      </div>
                      <Progress value={(scoreBreakdown.skill_score / 40) * 100} />
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span>Experience Match (25%)</span>
                        <span>{scoreBreakdown.experience_score.toFixed(1)}/25 ({Math.round((scoreBreakdown.experience_score / 25) * 100)}%)</span>
                      </div>
                      <Progress value={(scoreBreakdown.experience_score / 25) * 100} />
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span>Education Match (10%)</span>
                        <span>{scoreBreakdown.education_score.toFixed(1)}/10 ({Math.round((scoreBreakdown.education_score / 10) * 100)}%)</span>
                      </div>
                      <Progress value={(scoreBreakdown.education_score / 10) * 100} />
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span>Project Evidence (10%)</span>
                        <span>{scoreBreakdown.project_score.toFixed(1)}/10 ({Math.round((scoreBreakdown.project_score / 10) * 100)}%)</span>
                      </div>
                      <Progress value={(scoreBreakdown.project_score / 10) * 100} />
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span>Behaviour (10%)</span>
                        <span>{scoreBreakdown.behavior_score.toFixed(1)}/10 ({Math.round((scoreBreakdown.behavior_score / 10) * 100)}%)</span>
                      </div>
                      <Progress value={(scoreBreakdown.behavior_score / 10) * 100} />
                    </div>
                    <div className="pb-3 border-b">
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span>Availability (5%)</span>
                        <span>{scoreBreakdown.availability_score.toFixed(1)}/5 ({Math.round((scoreBreakdown.availability_score / 5) * 100)}%)</span>
                      </div>
                      <Progress value={(scoreBreakdown.availability_score / 5) * 100} />
                    </div>

                    <div className="space-y-1.5 pt-1">
                      <div className="flex justify-between text-xs font-medium text-muted-foreground">
                        <span>Base Component Score</span>
                        <span className="text-foreground font-semibold">
                          {(scoreBreakdown.skill_score + scoreBreakdown.experience_score + scoreBreakdown.education_score + scoreBreakdown.project_score + scoreBreakdown.behavior_score + scoreBreakdown.availability_score).toFixed(1)} / 100.0
                        </span>
                      </div>
                      {scoreBreakdown.engagement_bonus !== undefined && (
                        <div className="flex justify-between text-xs font-medium text-muted-foreground">
                          <span>Engagement/Profile Adjustment</span>
                          <span className={scoreBreakdown.engagement_bonus > 0 ? "text-emerald-500 font-semibold" : scoreBreakdown.engagement_bonus < 0 ? "text-rose-500 font-semibold" : "text-foreground font-semibold"}>
                            {scoreBreakdown.engagement_bonus > 0 ? "+" : ""}{scoreBreakdown.engagement_bonus.toFixed(1)}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between text-sm font-bold text-foreground pt-1 border-t">
                        <span>Final Sentinel Fit Score</span>
                        <span className="text-primary">{scoreBreakdown.final_score.toFixed(1)} / 100.0</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Columns: Main Tabs (Timeline, Skills, Signals, Explainability) */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Recruiter Advisor Banner (Confidently Interview section) */}
              <Card className={`border p-5 rounded-xl ${advice.color} shadow-sm transition-all duration-300`}>
                <div className="flex items-start gap-4">
                  <div className="mt-0.5">
                    {candidate.is_honeypot ? (
                      <AlertTriangle className="h-6 w-6 text-destructive" />
                    ) : (
                      <CheckCircle className="h-6 w-6 text-emerald-500" />
                    )}
                  </div>
                  <div className="space-y-1">
                    <h3 className="font-bold text-sm text-foreground">{advice.action}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {advice.description}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Requirement Checklist Widget (FIX 13) */}
              {jdQuery.data && matchedRequirements.length > 0 && (
                <Card className="border-border bg-card shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-foreground flex items-center gap-1.5 select-none">
                      <UserCheck className="h-4.5 w-4.5 text-primary" /> Screening Checklist
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Mandatory and preferred requirements matched against candidate skills
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Mandatory Requirements */}
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-primary select-none">MANDATORY</h4>
                        <div className="space-y-1.5">
                          {matchedRequirements.filter(r => r.required).map((r, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                              {r.matched ? (
                                <Badge variant="outline" className="text-emerald-500 bg-emerald-500/10 border-emerald-500/20 py-0.5 font-bold">
                                  ✓ Matched
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-destructive bg-destructive/10 border-destructive/20 py-0.5 font-bold">
                                  ✗ Lacking
                                </Badge>
                              )}
                              <span className="text-foreground font-semibold">{r.name}</span>
                            </div>
                          ))}
                          {matchedRequirements.filter(r => r.required).length === 0 && (
                            <span className="text-xs text-muted-foreground/60 italic">No mandatory requirements specified.</span>
                          )}
                        </div>
                      </div>

                      {/* Preferred Requirements */}
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-indigo-500 select-none">PREFERRED</h4>
                        <div className="space-y-1.5">
                          {matchedRequirements.filter(r => !r.required).map((r, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                              {r.matched ? (
                                <Badge variant="outline" className="text-indigo-500 bg-indigo-500/10 border-indigo-500/20 py-0.5 font-bold">
                                  ✓ Matched
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-muted-foreground bg-muted border-border py-0.5 font-bold">
                                  ✗ Lacking
                                </Badge>
                              )}
                              <span className="text-foreground font-medium">{r.name}</span>
                            </div>
                          ))}
                          {matchedRequirements.filter(r => !r.required).length === 0 && (
                            <span className="text-xs text-muted-foreground/60 italic">No preferred requirements specified.</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Factual Justification Explanation */}
              <Card className="border-border bg-card shadow-sm">
                <CardHeader className="flex flex-row items-center gap-2 pb-2">
                  <TrendingUp className="h-4.5 w-4.5 text-primary" />
                  <CardTitle className="text-sm font-bold text-foreground">Why Ranked Here</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground leading-relaxed leading-6 font-medium">
                    {candidate.reasoning}
                  </p>
                </CardContent>
              </Card>

              {/* Strengths & Potential Gaps Lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Key Strengths */}
                <Card className="border-border bg-card shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-bold text-emerald-500 uppercase tracking-wider select-none">Key Strengths</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {strengthsList.length > 0 ? (
                      <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-2">
                        {strengthsList.map((str, idx) => (
                          <li key={idx} className="leading-relaxed">{str}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground/60 italic">No specific strengths flagged.</p>
                    )}
                  </CardContent>
                </Card>

                {/* Identified Gaps / Risks */}
                <Card className="border-border bg-card shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-bold text-amber-500 uppercase tracking-wider select-none">Potential Gaps / Risks</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {gapsList.length > 0 ? (
                      <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-2">
                        {gapsList.map((gap, idx) => (
                          <li key={idx} className="leading-relaxed">{gap}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground/60 italic">No structural risks identified.</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Sub items Tabs */}
              <Tabs defaultValue="timeline" className="w-full">
                <TabsList className="grid w-full grid-cols-3 select-none">
                  <TabsTrigger value="timeline" className="gap-2 text-xs font-semibold">
                    <Briefcase className="h-3.5 w-3.5" /> Career History
                  </TabsTrigger>
                  <TabsTrigger value="skills" className="gap-2 text-xs font-semibold">
                    <GraduationCap className="h-3.5 w-3.5" /> Skills & Education
                  </TabsTrigger>
                  <TabsTrigger value="signals" className="gap-2 text-xs font-semibold">
                    <Award className="h-3.5 w-3.5" /> Candidate Signals
                  </TabsTrigger>
                </TabsList>

                {/* Timeline Content */}
                <TabsContent value="timeline" className="pt-4 animate-in fade-in duration-200">
                  <Card className="border-border bg-card">
                    <CardContent className="pt-6">
                      {detailQuery.loading && career.length === 0 ? (
                        <div className="space-y-6 py-4 select-none animate-pulse">
                          {[1, 2].map((i) => (
                            <div key={i} className="space-y-2.5">
                              <div className="h-4.5 bg-muted/60 rounded w-1/3" />
                              <div className="h-3.5 bg-muted/50 rounded w-1/2" />
                              <div className="h-3.5 bg-muted/40 rounded w-full" />
                            </div>
                          ))}
                        </div>
                      ) : career.length > 0 ? (
                        <div className="relative border-l border-border/80 pl-6 space-y-8 ml-3">
                          {career.map((job: CareerHistorySchema, idx: number) => (
                            <div key={idx} className="relative">
                              {/* Indicator dot */}
                              <div className="absolute -left-[31px] top-1.5 h-2.5 w-2.5 rounded-full border bg-background border-primary shadow-sm" />
                              <div className="space-y-1">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <h4 className="font-bold text-xs text-foreground">{job.title}</h4>
                                  <span className="text-[10px] text-muted-foreground flex items-center gap-1 font-mono">
                                    <Calendar className="h-3 w-3" />
                                    {job.start_date} to {job.end_date || "Present"} ({job.duration_months} mos)
                                  </span>
                                </div>
                                <p className="text-xs text-primary font-semibold">
                                  {job.company} · {job.company_size} employees · {job.industry}
                                </p>
                                <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                                  {job.description}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground text-center py-6">
                          No career timeline recorded.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Skills & Education Content */}
                <TabsContent value="skills" className="pt-4 space-y-6 animate-in fade-in duration-200">
                  {/* Skills Grid */}
                  <Card className="border-border bg-card">
                    <CardContent className="pt-6 space-y-4">
                      <div className="flex flex-wrap gap-2">
                        {(showAllSkills ? skills : skills.slice(0, 15)).map((skill: SkillSchema, idx: number) => (
                          <div
                            key={idx}
                            className="inline-flex items-center gap-2 rounded-lg border bg-background px-3 py-1.5 text-xs shadow-sm hover:bg-accent transition-colors animate-in fade-in duration-200"
                          >
                            <span className="font-bold text-foreground">{skill.name}</span>
                            <span className="text-muted-foreground text-[10px] font-mono">
                              ({skill.proficiency} · {skill.endorsements} endorsements)
                            </span>
                          </div>
                        ))}
                      </div>
                      {skills.length > 15 && (
                        <div className="flex justify-center select-none pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setShowAllSkills(!showAllSkills)}
                            className="text-xs font-bold px-4 border-border"
                          >
                            {showAllSkills ? "Show Less" : `Show More (+${skills.length - 15})`}
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Education Grid */}
                  <Card className="border-border bg-card">
                    <CardContent className="space-y-4 pt-6">
                      {detailQuery.loading && education.length === 0 ? (
                        <div className="space-y-4 py-2 select-none animate-pulse">
                          {[1].map((i) => (
                            <div key={i} className="flex gap-4 items-center">
                              <div className="rounded-lg p-4 bg-muted/60 w-10 h-10" />
                              <div className="space-y-2 flex-1">
                                <div className="h-4 bg-muted/50 rounded w-1/3" />
                                <div className="h-3 bg-muted/40 rounded w-1/2" />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : education.length > 0 ? (
                        education.map((edu: EducationSchema, idx: number) => (
                          <div key={idx} className="flex items-start gap-4 border-b border-border/40 pb-4 last:border-b-0 last:pb-0">
                            <div className="rounded-lg p-2.5 bg-primary/5 text-primary border border-border/80">
                              <GraduationCap className="h-4.5 w-4.5" />
                            </div>
                            <div>
                              <h4 className="font-bold text-xs text-foreground">{edu.institution}</h4>
                              <p className="text-xs text-primary font-semibold mt-0.5">
                                {edu.degree} in {edu.field_of_study}
                              </p>
                              <p className="text-[10px] text-muted-foreground font-mono mt-1 select-none">
                                Class of {edu.end_year} · Academic Tier {edu.tier}
                              </p>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground text-center py-6">
                          No education history recorded.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Behavior Signals Content */}
                <TabsContent value="signals" className="pt-4 animate-in fade-in duration-200">
                  <Card className="border-border bg-card">
                    <CardContent className="pt-6">
                      {detailQuery.loading && !detailQuery.data ? (
                        <div className="space-y-4 py-2 select-none animate-pulse">
                          {[1, 2, 3].map((i) => (
                            <div key={i} className="flex justify-between items-center">
                              <div className="h-4 bg-muted/50 rounded w-1/3" />
                              <div className="h-4 bg-muted/40 rounded w-10" />
                            </div>
                          ))}
                        </div>
                      ) : signals ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-4">
                            <h4 className="font-bold text-xs border-b pb-1 text-foreground select-none">Activity Metrics</h4>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Profile Completeness</span>
                              <span className="font-bold">{signals.profile_completeness_score}%</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Response Rate</span>
                              <span className="font-bold">{(signals.recruiter_response_rate * 100).toFixed(0)}%</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Interview Completion Rate</span>
                              <span className="font-bold">{(signals.interview_completion_rate * 100).toFixed(0)}%</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Offer Acceptance Rate</span>
                              <span className="font-bold">
                                {signals.offer_acceptance_rate >= 0 ? `${(signals.offer_acceptance_rate * 100).toFixed(0)}%` : "N/A"}
                              </span>
                            </div>
                          </div>

                          <div className="space-y-4">
                            <h4 className="font-bold text-xs border-b pb-1 text-foreground select-none">Preferences & Socials</h4>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Preferred Work Mode</span>
                              <span className="font-bold uppercase">{signals.preferred_work_mode}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Willing to Relocate</span>
                              <span className="font-bold">{signals.willing_to_relocate ? "Yes" : "No"}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Connection Count</span>
                              <span className="font-bold">{signals.connection_count} connections</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">GitHub Activity Score</span>
                              <span className="font-bold font-mono">
                                {signals.github_activity_score >= 0 ? signals.github_activity_score : "Not Synced"}
                              </span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground text-center py-6">
                          No candidate signals recorded.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        )}
      </QueryLoader>
    </div>
  );
}
