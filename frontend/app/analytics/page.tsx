"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useApi } from "@/hooks/use-api";
import { apiService } from "@/services/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BarChart3, Clock, Award, ShieldAlert, RefreshCw, Cpu, Server, CheckCircle2, AlertCircle, Users, Activity, GraduationCap, Building, Briefcase, Zap, Info } from "lucide-react";
import { CandidateDetailResponse, RankResponseItem, JobDescription } from "@/types";

// Premium UI placeholder for charts when rankings have not been run yet
const ChartPlaceholder = ({ title, type = "bar" }: { title: string; type?: "bar" | "list" }) => {
  return (
    <div className="w-full h-full min-h-[200px] flex flex-col items-center justify-center border border-dashed rounded-lg p-6 bg-muted/5 animate-in fade-in duration-300">
      <div className="flex flex-col items-center text-center gap-1">
        <BarChart3 className="h-6 w-6 text-muted-foreground/30 mb-1" />
        <span className="text-xs font-bold text-muted-foreground">{title} Preview</span>
        <span className="text-[10px] text-muted-foreground/75">No active evaluation run loaded. Submit requirements to populate charts.</span>
      </div>
      {type === "bar" ? (
        <div className="flex gap-2 w-full max-w-[200px] h-16 items-end mt-4 opacity-10 select-none">
          <div className="bg-foreground w-full h-[40%] rounded-t" />
          <div className="bg-foreground w-full h-[70%] rounded-t" />
          <div className="bg-foreground w-full h-[50%] rounded-t" />
          <div className="bg-foreground w-full h-[90%] rounded-t" />
          <div className="bg-foreground w-full h-[60%] rounded-t" />
        </div>
      ) : (
        <div className="flex flex-col gap-2 w-full max-w-[200px] mt-4 opacity-10 select-none">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <div className="h-2 bg-foreground rounded w-16" />
              <div className="w-full bg-foreground/20 h-1.5 rounded-full" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default function InsightsPage() {
  const rankingQuery = useApi(apiService.getTop100, true);
  const analyticsQuery = useApi(apiService.getAnalytics, true);
  const jdQuery = useApi<JobDescription, []>(apiService.getActiveJd, true);

  const handleRefresh = () => {
    rankingQuery.execute().catch(() => {});
    analyticsQuery.execute().catch(() => {});
  };

  const isRefreshing = rankingQuery.loading || analyticsQuery.loading;
  const candidates = rankingQuery.data?.candidates || [];


  // Factual technical execution metrics from backend
  const aiSearchTime = analyticsQuery.data?.latest_retrieval_latency_ms !== undefined && analyticsQuery.data?.latest_retrieval_latency_ms !== null
    ? `${(analyticsQuery.data.latest_retrieval_latency_ms / 1000).toFixed(2)} s`
    : "N/A";
    
  const screeningRuntime = analyticsQuery.data?.latest_pipeline_runtime_ms !== undefined && analyticsQuery.data?.latest_pipeline_runtime_ms !== null
    ? `${(analyticsQuery.data.latest_pipeline_runtime_ms / 1000).toFixed(2)} s`
    : "N/A";
    
  const honeypotRateVal = analyticsQuery.data?.latest_honeypot_rate !== undefined && analyticsQuery.data?.latest_honeypot_rate !== null
    ? `${(analyticsQuery.data.latest_honeypot_rate * 100).toFixed(1)}%`
    : "N/A";

  const totalDatasetCount = analyticsQuery.data?.candidate_count || 100000;

  // 1. Score Distribution
  const scoreDistribution = useMemo(() => {
    if (candidates.length === 0) return [];
    const buckets = { "0-30 pts": 0, "31-60 pts": 0, "61-90 pts": 0, "91-120 pts": 0, "121-150 pts": 0 };
    candidates.forEach((c) => {
      const score = c.score;
      if (score <= 30) buckets["0-30 pts"]++;
      else if (score <= 60) buckets["31-60 pts"]++;
      else if (score <= 90) buckets["61-90 pts"]++;
      else if (score <= 120) buckets["91-120 pts"]++;
      else buckets["121-150 pts"]++;
    });
    return Object.entries(buckets).map(([range, count]) => ({ range, count }));
  }, [candidates]);

  // 2. Experience Distribution (Computed directly from list data!)
  const experienceDistribution = useMemo(() => {
    const buckets = { "0-2 yrs": 0, "3-5 yrs": 0, "6-9 yrs": 0, "10+ yrs": 0 };
    let totalValid = 0;
    candidates.forEach((c) => {
      if (c.years_of_experience === undefined || c.years_of_experience === null) return;
      totalValid++;
      const exp = c.years_of_experience;
      if (exp <= 2) buckets["0-2 yrs"]++;
      else if (exp <= 5) buckets["3-5 yrs"]++;
      else if (exp <= 9) buckets["6-9 yrs"]++;
      else buckets["10+ yrs"]++;
    });
    if (totalValid === 0) return [];
    return Object.entries(buckets).map(([range, count]) => ({ range, count }));
  }, [candidates]);

  // 3. Notice Period Distribution (Computed directly from list data!)
  const noticePeriodDistribution = useMemo(() => {
    const buckets = { "Immediate": 0, "1-30 days": 0, "31-60 days": 0, "60+ days": 0 };
    let totalValid = 0;
    candidates.forEach((c) => {
      const notice = c.notice_period_days;
      if (notice === undefined || notice === null) return;
      totalValid++;
      if (notice === 0) buckets["Immediate"]++;
      else if (notice <= 30) buckets["1-30 days"]++;
      else if (notice <= 60) buckets["31-60 days"]++;
      else buckets["60+ days"]++;
    });
    if (totalValid === 0) return [];
    return Object.entries(buckets).map(([range, count]) => ({ range, count }));
  }, [candidates]);

  // 4. Top Skills (Computed directly from list data!)
  const topSkills = useMemo(() => {
    const skillCounts: Record<string, number> = {};
    candidates.forEach((c) => {
      c.skills?.forEach((skill: string) => {
        const name = skill.trim();
        if (!name || name.toLowerCase() === "unknown" || name.toLowerCase() === "not specified") return;
        skillCounts[name] = (skillCounts[name] || 0) + 1;
      });
    });
    return Object.entries(skillCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({ name, count }));
  }, [candidates]);

  // 5. Top Companies (Computed directly from list data!)
  const topCompanies = useMemo(() => {
    const counts: Record<string, number> = {};
    candidates.forEach((c) => {
      const company = c.current_company?.trim();
      if (!company || company.toLowerCase() === "unknown" || company.toLowerCase() === "not specified" || company.toLowerCase() === "none") return;
      counts[company] = (counts[company] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({ name, count }));
  }, [candidates]);

  // 6. Top Universities (Direct from server-side analytics response)
  const topUniversities = useMemo(() => {
    return (analyticsQuery.data?.top_universities || []) as { name: string; count: number }[];
  }, [analyticsQuery.data]);

  // 7. Risk Distribution (Computed directly from list data!)
  const riskDistribution = useMemo(() => {
    const counts = { "Verified Clear": 0, "Flagged Risk": 0 };
    let totalValid = 0;
    candidates.forEach((c) => {
      totalValid++;
      if (c.is_honeypot) counts["Flagged Risk"]++;
      else counts["Verified Clear"]++;
    });
    if (totalValid === 0) return [];
    return Object.entries(counts).map(([range, count]) => ({ range, count }));
  }, [candidates]);

  // 8. Work Mode Distribution (Direct from server-side analytics response)
  const workModeDistribution = useMemo(() => {
    return (analyticsQuery.data?.work_mode_distribution || []) as { range: string; count: number }[];
  }, [analyticsQuery.data]);

  // 9. Education Distribution (Direct from server-side analytics response)
  const educationDistribution = useMemo(() => {
    return (analyticsQuery.data?.education_distribution || []) as { range: string; count: number }[];
  }, [analyticsQuery.data]);

  // 10. Average Subscores (Computed directly from list data!)
  const averageSubscores = useMemo(() => {
    if (candidates.length === 0) {
      return { skill: 0, experience: 0, education: 0, project: 0, behavior: 0, availability: 0 };
    }
    let sSum = 0, eSum = 0, eduSum = 0, pSum = 0, bSum = 0, aSum = 0;
    candidates.forEach((c) => {
      const sb = c.score_breakdown || { skill_score: 0, experience_score: 0, education_score: 0, project_score: 0, behavior_score: 0, availability_score: 0 };
      sSum += sb.skill_score || 0;
      eSum += sb.experience_score || 0;
      eduSum += sb.education_score || 0;
      pSum += sb.project_score || 0;
      bSum += sb.behavior_score || 0;
      aSum += sb.availability_score || 0;
    });
    const len = candidates.length;
    return {
      skill: sSum / len,
      experience: eSum / len,
      education: eduSum / len,
      project: pSum / len,
      behavior: bSum / len,
      availability: aSum / len
    };
  }, [candidates]);

  // 11. Location Distribution (Direct from server-side analytics response)
  const locationDistribution = useMemo(() => {
    return (analyticsQuery.data?.top_locations || []) as { name: string; count: number }[];
  }, [analyticsQuery.data]);

  // 12. Top Missing Skills (Direct from server-side analytics response)
  const topMissingSkills = useMemo(() => {
    return (analyticsQuery.data?.top_missing_skills || []) as { name: string; count: number }[];
  }, [analyticsQuery.data]);

  // General counts for header indicators
  const averageScore = useMemo(() => {
    if (candidates.length === 0) return 0;
    const sum = candidates.reduce((acc, c) => acc + c.score, 0);
    return Math.round(sum / candidates.length);
  }, [candidates]);

  const openToWorkPct = useMemo(() => {
    if (candidates.length === 0) return 0;
    const openCount = candidates.filter((c) => c.open_to_work === true).length;
    return Math.round((openCount / candidates.length) * 100);
  }, [candidates]);

  const riskProfilesCount = useMemo(() => {
    return candidates.filter((c) => c.is_honeypot === true).length;
  }, [candidates]);

  const verifiedProfilesCount = useMemo(() => {
    return candidates.filter((c) => !c.is_honeypot).length;
  }, [candidates]);

  // Max counts for styling bar chart layouts
  const maxScoreCount = Math.max(...scoreDistribution.map((d) => d.count), 1);
  const maxExpCount = Math.max(...experienceDistribution.map((d) => d.count), 1);
  const maxNoticeCount = Math.max(...noticePeriodDistribution.map((d) => d.count), 1);
  const maxSkillCount = Math.max(...topSkills.map((d) => d.count), 1);
  const maxCompanyCount = Math.max(...topCompanies.map((d) => d.count), 1);
  const maxUnivCount = Math.max(...topUniversities.map((d) => d.count), 1);
  const maxRiskCount = Math.max(...riskDistribution.map((d) => d.count), 1);
  const maxModeCount = Math.max(...workModeDistribution.map((d) => d.count), 1);
  const maxEduCount = Math.max(...educationDistribution.map((d) => d.count), 1);
  const maxLocationCount = Math.max(...locationDistribution.map((d) => d.count), 1);
  const maxMissingCount = Math.max(...topMissingSkills.map((d) => d.count), 1);

  const showInsightsExist = candidates.length > 0;

  return (
    <div className="space-y-10 animate-in fade-in duration-500 py-4">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 select-none">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Insights</h1>
          <p className="text-muted-foreground">
            Analyze match statistics, candidate demographics, and system processing metrics.
          </p>
        </div>
        <Button onClick={handleRefresh} variant="outline" className="gap-2 border-primary/20 hover:border-primary/40" disabled={isRefreshing}>
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} /> Refresh Insights
        </Button>
      </div>

      {(rankingQuery.error || analyticsQuery.error) && (
        <div className="flex items-center gap-3 p-4 border border-destructive/20 rounded-xl bg-destructive/5 text-destructive text-sm animate-in fade-in">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <div>
            <span className="font-bold">Database Sync Warning:</span> {rankingQuery.error || analyticsQuery.error}
          </div>
        </div>
      )}



      {/* SECTION 1: Recruiter Insights */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-foreground select-none">Recruiter Insights</h2>

        {/* Recruiter KPI Strip */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 select-none">
          <Card className="border-border bg-card p-4 hover:shadow-md hover:border-primary/15 transition-all duration-300">
            <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block">Average Fit Score</span>
            <span className="text-2xl font-extrabold text-foreground mt-1 block">{showInsightsExist ? `${averageScore.toFixed(0)} pts` : "N/A"}</span>
          </Card>
          <Card className="border-border bg-card p-4 hover:shadow-md hover:border-primary/15 transition-all duration-300">
            <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block">Open To Work Rate</span>
            <span className="text-2xl font-extrabold text-foreground mt-1 block">{showInsightsExist ? `${openToWorkPct}%` : "N/A"}</span>
          </Card>
          <Card className="border-border bg-card p-4 hover:shadow-md hover:border-primary/15 transition-all duration-300">
            <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block">Verified Clear Profiles</span>
            <span className="text-2xl font-extrabold text-emerald-500 mt-1 block">{showInsightsExist ? verifiedProfilesCount : "N/A"}</span>
          </Card>
          <Card className="border-border bg-card p-4 hover:shadow-md hover:border-primary/15 transition-all duration-300">
            <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block">Flagged Risk Profiles</span>
            <span className={`text-2xl font-extrabold mt-1 block ${riskProfilesCount > 0 ? "text-destructive" : "text-foreground"}`}>{showInsightsExist ? riskProfilesCount : "N/A"}</span>
          </Card>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
          {/* Chart 1: Score Distribution */}
          {scoreDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Score Distribution</CardTitle>
                <CardDescription className="text-[10px]">Fit points frequency inside ranked candidates</CardDescription>
              </CardHeader>
              <CardContent className="h-[200px] flex items-end justify-between gap-3 pt-6 flex-1">
                {scoreDistribution.map((d, idx) => {
                  const pct = (d.count / maxScoreCount) * 100;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end select-none">
                      <div className="text-[9px] font-bold text-foreground">
                        {d.count}
                      </div>
                      <div
                        style={{ height: `${pct * 0.7}%` }}
                        className="w-full bg-primary/75 hover:bg-primary rounded-t-sm transition-all duration-200 cursor-pointer"
                      />
                      <span className="text-[9px] text-muted-foreground font-semibold whitespace-nowrap">{d.range}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 2: Experience Distribution */}
          {experienceDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Experience distribution</CardTitle>
                <CardDescription className="text-[10px]">Years of experience distribution inside ranked candidates</CardDescription>
              </CardHeader>
              <CardContent className="h-[200px] flex items-end justify-between gap-3 pt-6 flex-1">
                {experienceDistribution.map((d, idx) => {
                  const pct = (d.count / maxExpCount) * 100;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end select-none">
                      <div className="text-[9px] font-bold text-foreground">
                        {d.count}
                      </div>
                      <div
                        style={{ height: `${pct * 0.7}%` }}
                        className="w-full bg-emerald-500/70 hover:bg-emerald-500 rounded-t-sm transition-all duration-200 cursor-pointer"
                      />
                      <span className="text-[9px] text-muted-foreground font-semibold whitespace-nowrap">{d.range}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 3: Notice Period Distribution */}
          {noticePeriodDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Notice Period distribution</CardTitle>
                <CardDescription className="text-[10px]">Notice period requirements of selected candidates</CardDescription>
              </CardHeader>
              <CardContent className="h-[200px] flex items-end justify-between gap-3 pt-6 flex-1">
                {noticePeriodDistribution.map((d, idx) => {
                  const pct = (d.count / maxNoticeCount) * 100;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end select-none">
                      <div className="text-[9px] font-bold text-foreground">
                        {d.count}
                      </div>
                      <div
                        style={{ height: `${pct * 0.7}%` }}
                        className="w-full bg-indigo-500/70 hover:bg-indigo-500 rounded-t-sm transition-all duration-200 cursor-pointer"
                      />
                      <span className="text-[9px] text-muted-foreground font-semibold whitespace-nowrap">{d.range}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 4: Top Skills */}
          {topSkills.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Top Skills</CardTitle>
                <CardDescription className="text-[10px]">Most recurring skills inside ranked candidates</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center gap-3.5 pt-4 flex-1">
                {topSkills.map((d, idx) => {
                  const pct = (d.count / maxSkillCount) * 100;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between items-center text-xs font-semibold select-none">
                        <span className="font-mono text-[10px] text-foreground">{d.name}</span>
                        <span className="text-[9px] text-muted-foreground font-bold">{d.count} candidates</span>
                      </div>
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${pct}%` }}
                          className="bg-primary h-full rounded-full transition-all duration-300"
                        />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 5: Top Companies */}
          {topCompanies.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Top Companies</CardTitle>
                <CardDescription className="text-[10px]">Primary candidate feeder organisations</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center gap-3.5 pt-4 flex-1">
                {topCompanies.map((d, idx) => {
                  const pct = (d.count / maxCompanyCount) * 100;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between items-center text-xs font-semibold select-none">
                        <span className="font-mono text-[10px] text-foreground truncate max-w-[150px]">{d.name}</span>
                        <span className="text-[9px] text-muted-foreground font-bold">{d.count} candidates</span>
                      </div>
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${pct}%` }}
                          className="bg-sky-500 h-full rounded-full transition-all duration-300"
                        />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 6: Top Universities */}
          {topUniversities.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Top Universities</CardTitle>
                <CardDescription className="text-[10px]">Academic feeder institutes</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center gap-3.5 pt-4 flex-1">
                {topUniversities.map((d, idx) => {
                  const pct = (d.count / maxUnivCount) * 100;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between items-center text-xs font-semibold select-none">
                        <span className="font-mono text-[10px] text-foreground truncate max-w-[150px]">{d.name}</span>
                        <span className="text-[9px] text-muted-foreground font-bold">{d.count} candidates</span>
                      </div>
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${pct}%` }}
                          className="bg-amber-500 h-full rounded-full transition-all duration-300"
                        />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 7: Risk Distribution */}
          {riskDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Risk Distribution</CardTitle>
                <CardDescription className="text-[10px]">Profile timeline integrity results</CardDescription>
              </CardHeader>
              <CardContent className="h-[200px] flex items-end justify-around gap-3 pt-6 flex-1">
                {riskDistribution.map((d, idx) => {
                  const pct = (d.count / maxRiskCount) * 100;
                  return (
                    <div key={idx} className="w-[60px] flex flex-col items-center gap-1.5 group h-full justify-end select-none">
                      <div className="text-[9px] font-bold text-foreground">
                        {d.count}
                      </div>
                      <div
                        style={{ height: `${pct * 0.7}%` }}
                        className={`w-full rounded-t-sm transition-all duration-200 cursor-pointer ${d.range.includes("Risk") ? "bg-destructive/75 hover:bg-destructive" : "bg-emerald-500/70 hover:bg-emerald-500"}`}
                      />
                      <span className="text-[9px] text-muted-foreground font-semibold whitespace-nowrap">{d.range}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 8: Work Mode Distribution */}
          {workModeDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Work Mode distribution</CardTitle>
                <CardDescription className="text-[10px]">Preferred candidate workplace style</CardDescription>
              </CardHeader>
              <CardContent className="h-[200px] flex items-end justify-between gap-3 pt-6 flex-1">
                {workModeDistribution.map((d, idx) => {
                  const pct = (d.count / maxModeCount) * 100;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end select-none">
                      <div className="text-[9px] font-bold text-foreground">
                        {d.count}
                      </div>
                      <div
                        style={{ height: `${pct * 0.7}%` }}
                        className="w-full bg-purple-500/70 hover:bg-purple-500 rounded-t-sm transition-all duration-200 cursor-pointer"
                      />
                      <span className="text-[9px] text-muted-foreground font-semibold whitespace-nowrap">{d.range}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 9: Education Distribution */}
          {educationDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Education distribution</CardTitle>
                <CardDescription className="text-[10px]">Academic institution tier levels</CardDescription>
              </CardHeader>
              <CardContent className="h-[200px] flex items-end justify-between gap-3 pt-6 flex-1">
                {educationDistribution.map((d, idx) => {
                  const pct = (d.count / maxEduCount) * 100;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end select-none">
                      <div className="text-[9px] font-bold text-foreground">
                        {d.count}
                      </div>
                      <div
                        style={{ height: `${pct * 0.7}%` }}
                        className="w-full bg-teal-500/70 hover:bg-teal-500 rounded-t-sm transition-all duration-200 cursor-pointer"
                      />
                      <span className="text-[9px] text-muted-foreground font-semibold whitespace-nowrap">{d.range}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 10: Location Distribution (FIX 14) */}
          {locationDistribution.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Location Distribution</CardTitle>
                <CardDescription className="text-[10px]">Geographic distribution of evaluated candidates</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center gap-3.5 pt-4 flex-1">
                {locationDistribution.map((d, idx) => {
                  const pct = (d.count / maxLocationCount) * 100;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between items-center text-xs font-semibold select-none">
                        <span className="font-mono text-[10px] text-foreground truncate max-w-[150px]">{d.name}</span>
                        <span className="text-[9px] text-muted-foreground font-bold">{d.count} candidates</span>
                      </div>
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${pct}%` }}
                          className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                        />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 11: Top Missing Skills (FIX 14) */}
          {topMissingSkills.length > 0 && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Top Missing Skills</CardTitle>
                <CardDescription className="text-[10px]">Most frequently missing required skills from active JD</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center gap-3.5 pt-4 flex-1">
                {topMissingSkills.map((d, idx) => {
                  const pct = (d.count / maxMissingCount) * 100;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between items-center text-xs font-semibold select-none">
                        <span className="font-mono text-[10px] text-foreground truncate max-w-[150px]">{d.name}</span>
                        <span className="text-[9px] text-destructive font-bold">{d.count} missing</span>
                      </div>
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${pct}%` }}
                          className="bg-destructive/70 h-full rounded-full transition-all duration-300"
                        />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Chart 12: Average Match Subscores (FIX 14) */}
          {showInsightsExist && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Average Sentinel Fit Scores</CardTitle>
                <CardDescription className="text-[10px]">Average point scores across all canonical dimensions</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center gap-3 pt-3 flex-1">
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium">Skills Match (out of 40):</span>
                    <span className="font-bold">{averageSubscores.skill.toFixed(1)}/40</span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${(averageSubscores.skill / 40) * 100}%` }} className="bg-primary h-full rounded-full" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium">Experience Match (out of 25):</span>
                    <span className="font-bold">{averageSubscores.experience.toFixed(1)}/25</span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${(averageSubscores.experience / 25) * 100}%` }} className="bg-indigo-500 h-full rounded-full" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium">Education Relevance (out of 10):</span>
                    <span className="font-bold">{averageSubscores.education.toFixed(1)}/10</span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${(averageSubscores.education / 10) * 100}%` }} className="bg-amber-500 h-full rounded-full" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium">Projects & Evidence (out of 10):</span>
                    <span className="font-bold">{averageSubscores.project.toFixed(1)}/10</span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${(averageSubscores.project / 10) * 100}%` }} className="bg-violet-500 h-full rounded-full" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium">Behaviour Match (out of 10):</span>
                    <span className="font-bold">{averageSubscores.behavior.toFixed(1)}/10</span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${(averageSubscores.behavior / 10) * 100}%` }} className="bg-emerald-500 h-full rounded-full" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium">Availability (out of 5):</span>
                    <span className="font-bold">{averageSubscores.availability.toFixed(1)}/5</span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${(averageSubscores.availability / 5) * 100}%` }} className="bg-teal-500 h-full rounded-full" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chart 13: Recruiter Strategic Insights (FIX 14) */}
          {showInsightsExist && (
            <Card className="border border-border bg-card shadow-sm flex flex-col h-full col-span-1 md:col-span-2 lg:col-span-3 animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider">Recruiter Strategic Insights</CardTitle>
                <CardDescription className="text-[10px]">AI-assisted high-level hiring candidate recommendations</CardDescription>
              </CardHeader>
              <CardContent className="pt-2 text-xs text-muted-foreground leading-relaxed leading-6">
                <ul className="list-disc pl-4 space-y-2">
                  <li>
                    <strong className="text-foreground">Notice period readiness:</strong> Notice period alignment is highly favorable. Approximately <span className="text-primary font-bold">{openToWorkPct}%</span> of candidates are marked as Open to Work or immediately available.
                  </li>
                  {topMissingSkills.length > 0 && (
                    <li>
                      <strong className="text-foreground">Primary technical gaps detected:</strong> The most significant technical missing requirements across unranked candidates include <span className="text-destructive font-bold">{topMissingSkills.slice(0,2).map(s=>s.name).join(" and ")}</span>. Target direct sourcing outreach toward these skill sets to expand talent pool.
                    </li>
                  )}
                  <li>
                    <strong className="text-foreground">Chronological integrity checks:</strong> Out of the candidates analyzed, <span className="text-emerald-500 font-bold">{verifiedProfilesCount}</span> profile timelines passed verification tests, while <span className="text-destructive font-bold">{riskProfilesCount}</span> profile showed severe date anomalies, warning of logical honeypot contradictions.
                  </li>
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        {!showInsightsExist && !isRefreshing && (
          <div className="py-12">
            <ChartPlaceholder title="Demographic Candidate Metrics" type="list" />
          </div>
        )}
      </div>

      {/* SECTION 2: System Performance */}
      <div className="space-y-4 pt-4 border-t border-border/60 select-none">
        <h2 className="text-lg font-bold text-foreground">System Performance</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {analyticsQuery.loading ? (
            Array.from({ length: 3 }).map((_, idx) => (
              <div key={idx} className="h-24 rounded-xl border bg-card animate-pulse" />
            ))
          ) : (
            <>
              {/* AI Search Time */}
              <Card className="border border-border bg-card shadow-sm">
                <CardHeader className="flex flex-row items-center gap-2 pb-2">
                  <Clock className="h-4.5 w-4.5 text-primary" />
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">AI Search Time</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-extrabold text-foreground">{aiSearchTime}</div>
                  <p className="text-[10px] text-muted-foreground mt-1">Hybrid AI Retrieval execution latency</p>
                </CardContent>
              </Card>

              {/* Screening Runtime */}
              <Card className="border border-border bg-card shadow-sm">
                <CardHeader className="flex flex-row items-center gap-2 pb-2">
                  <Cpu className="h-4.5 w-4.5 text-emerald-500" />
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Screening Runtime</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-extrabold text-foreground">{screeningRuntime}</div>
                  <p className="text-[10px] text-muted-foreground mt-1">Timeline parsing & risk checks runtime</p>
                </CardContent>
              </Card>

              {/* Honeypot Flag Rate */}
              <Card className="border border-border bg-card shadow-sm">
                <CardHeader className="flex flex-row items-center gap-2 pb-2">
                  <ShieldAlert className="h-4.5 w-4.5 text-destructive" />
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Honeypot Flag Rate</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-extrabold text-foreground">{honeypotRateVal}</div>
                  <p className="text-[10px] text-muted-foreground mt-1">Honeypots caught in 300 evaluated cohort</p>
                </CardContent>
              </Card>
            </>
          )}
        </div>

        {/* Challenge details */}
        <Card className="border border-border bg-card shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1">
              Engine Vector Status
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground">Vector Dimension:</span>{" "}
              <span className="font-bold text-foreground">384 Dimensions</span>
            </div>
            <div>
              <span className="text-muted-foreground">Search Index:</span>{" "}
              <span className="font-bold text-foreground">FAISS + TF-IDF Hybrid</span>
            </div>
            <div>
              <span className="text-muted-foreground">Indexed Dataset Size:</span>{" "}
              <span className="font-bold text-foreground">{totalDatasetCount.toLocaleString()} Candidates</span>
            </div>
            <div>
              <span className="text-muted-foreground">Model Status:</span>{" "}
              <span className="font-bold text-emerald-500">Sentence Transformer Active</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
