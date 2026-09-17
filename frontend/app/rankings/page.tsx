"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import { apiService } from "@/services/api";
import { QueryLoader } from "@/components/query-loader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Eye,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Clock,
  Briefcase,
  Users,
  Award,
  Zap,
  ShieldCheck,
  TrendingUp,
  FileText,
  Info
} from "lucide-react";
import { CandidateDetailResponse, RankResponseItem } from "@/types";
import { motion, AnimatePresence } from "framer-motion";

type SortField = "rank" | "score" | "candidate_id";
type SortOrder = "asc" | "desc";

export default function CandidateRankings() {
  const rankingQuery = useApi(apiService.getTop100, true);
  const analyticsQuery = useApi(apiService.getAnalytics, true);

  const [searchTerm, setSearchTerm] = useState<string>("");

  // Recruiter Workspace Filters
  const [fraudFilter, setFraudFilter] = useState<"all" | "high" | "low">("all");
  const [openToWorkFilter, setOpenToWorkFilter] = useState<"all" | "yes">("all");
  const [noticeFilter, setNoticeFilter] = useState<"all" | "immediate" | "short">("all");
  const [experienceFilter, setExperienceFilter] = useState<"all" | "0-2" | "3-5" | "6-9" | "10+">("all");
  const [locationFilter, setLocationFilter] = useState<string>("");

  const [sortField, setSortField] = useState<SortField>("rank");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [itemsPerPage, setItemsPerPage] = useState<number>(10);

  // Track expanded row status for candidate details
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  // Track clickable popover for score breakdown (FIX 13)
  const [popoverCandidateId, setPopoverCandidateId] = useState<string | null>(null);

  // Caching details dynamically for visible page to get detailed sub-scores
  const [cachedDetails, setCachedDetails] = useState<Record<string, CandidateDetailResponse>>({});
  const [loadingDetails, setLoadingDetails] = useState<Record<string, boolean>>({});

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 text-muted-foreground/60 ml-1 inline-block" />;
    }
    if (sortOrder === "asc") {
      return <ChevronUp className="h-3 w-3 text-primary ml-1 inline-block" />;
    }
    return <ChevronDown className="h-3 w-3 text-primary ml-1 inline-block" />;
  };

  const toggleRow = async (candidateId: string) => {
    setExpandedRows((prev) => ({
      ...prev,
      [candidateId]: !prev[candidateId],
    }));

    if (!cachedDetails[candidateId] && !loadingDetails[candidateId]) {
      setLoadingDetails((prev) => ({ ...prev, [candidateId]: true }));
      try {
        const detail = await apiService.getCandidateDetail(candidateId);
        setCachedDetails((prev) => ({ ...prev, [candidateId]: detail }));
      } catch (err) {
        console.error("Failed to fetch candidate details:", err);
      } finally {
        setLoadingDetails((prev) => {
          const next = { ...prev };
          delete next[candidateId];
          return next;
        });
      }
    }
  };

  // Search match text highlight helper
  const highlightText = (text: string, search: string) => {
    if (!search.trim()) return <span>{text}</span>;
    const cleanSearch = search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${cleanSearch})`, "gi");
    const parts = text.split(regex);
    return (
      <span>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-yellow-500/25 text-foreground px-0.5 rounded font-medium">
              {part}
            </mark>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </span>
    );
  };



  // Filter and sort candidates list including deep detail queries
  const processedCandidates = useMemo(() => {
    const rawList = rankingQuery.data?.candidates || [];

    // Apply Search matching ID, reasoning and details keywords
    let list = rawList.filter((c) => {
      const term = searchTerm.toLowerCase().trim();
      if (!term) return true;

      const idMatch = c.candidate_id.toLowerCase().includes(term);
      const reasoningMatch = c.reasoning.toLowerCase().includes(term);

      const d = cachedDetails[c.candidate_id];
      if (d) {
        const skillsMatch = d.skills?.some(s => s.name.toLowerCase().includes(term));
        const currentRoleMatch = d.current_title.toLowerCase().includes(term);
        const currentCompanyMatch = d.current_company.toLowerCase().includes(term);
        const previousCompaniesMatch = d.career_history?.some(j => j.company.toLowerCase().includes(term));
        const previousRolesMatch = d.career_history?.some(j => j.title.toLowerCase().includes(term));
        const locationMatch = d.location.toLowerCase().includes(term);
        const degreeMatch = d.education?.some(e => e.degree.toLowerCase().includes(term));
        const universityMatch = d.education?.some(e => e.institution.toLowerCase().includes(term));
        const collegeMatch = d.education?.some(e => e.institution.toLowerCase().includes(term));
        const certificationsMatch = d.certifications?.some(c => c.name.toLowerCase().includes(term) || c.issuer.toLowerCase().includes(term));
        const keywordsMatch = d.summary.toLowerCase().includes(term);
        const experienceMatch = d.years_of_experience.toString().includes(term);
        const noticePeriodMatch = d.behavioral_signals?.notice_period_days?.toString().includes(term);

        return idMatch || reasoningMatch || skillsMatch || currentRoleMatch || currentCompanyMatch || 
               previousCompaniesMatch || previousRolesMatch || locationMatch || degreeMatch || 
               universityMatch || collegeMatch || certificationsMatch || keywordsMatch || 
               experienceMatch || noticePeriodMatch;
      }

      return idMatch || reasoningMatch;
    });

    // Apply Sort
    list = [...list].sort((a, b) => {
      let comparison = 0;
      if (sortField === "rank") comparison = a.rank - b.rank;
      else if (sortField === "score") comparison = a.score - b.score;
      else comparison = a.candidate_id.localeCompare(b.candidate_id);

      return sortOrder === "asc" ? comparison : -comparison;
    });

    return list;
  }, [rankingQuery.data, cachedDetails, searchTerm, sortField, sortOrder]);

  // Compute pagination slices
  const totalPages = Math.ceil(processedCandidates.length / itemsPerPage) || 1;
  const paginatedCandidates = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return processedCandidates.slice(start, start + itemsPerPage);
  }, [processedCandidates, currentPage, itemsPerPage]);



  // Filter candidates based on Recruiter Filters panel
  const filteredCandidates = useMemo(() => {
    let list = processedCandidates;

    // 1. Risk Level
    if (fraudFilter !== "all") {
      list = list.filter((c) => {
        const isHoneypot = c.is_honeypot ?? cachedDetails[c.candidate_id]?.is_honeypot ?? false;
        return fraudFilter === "high" ? isHoneypot : !isHoneypot;
      });
    }

    // 2. Open to Work
    if (openToWorkFilter !== "all") {
      list = list.filter((c) => {
        const open = c.open_to_work ?? cachedDetails[c.candidate_id]?.behavioral_signals?.open_to_work_flag ?? false;
        return open === true;
      });
    }

    // 3. Notice Period
    if (noticeFilter !== "all") {
      list = list.filter((c) => {
        const days = c.notice_period_days ?? cachedDetails[c.candidate_id]?.behavioral_signals?.notice_period_days ?? 0;
        if (noticeFilter === "immediate") return days === 0;
        if (noticeFilter === "short") return days <= 30;
        return true;
      });
    }

    // 4. Experience Range
    if (experienceFilter !== "all") {
      list = list.filter((c) => {
        const y = c.years_of_experience ?? cachedDetails[c.candidate_id]?.years_of_experience ?? 0;
        if (experienceFilter === "0-2") return y <= 2;
        if (experienceFilter === "3-5") return y > 2 && y <= 5;
        if (experienceFilter === "6-9") return y > 5 && y <= 9;
        if (experienceFilter === "10+") return y > 9;
        return true;
      });
    }

    // 5. Location Filter
    if (locationFilter.trim()) {
      const term = locationFilter.toLowerCase().trim();
      list = list.filter((c) => {
        const loc = c.location ?? cachedDetails[c.candidate_id]?.location ?? "";
        return loc.toLowerCase().includes(term);
      });
    }

    return list;
  }, [processedCandidates, cachedDetails, fraudFilter, openToWorkFilter, noticeFilter, experienceFilter, locationFilter]);

  // Recalculate paginated view from filtered results
  const totalFilteredPages = Math.ceil(filteredCandidates.length / itemsPerPage) || 1;
  const paginatedFilteredCandidates = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredCandidates.slice(start, start + itemsPerPage);
  }, [filteredCandidates, currentPage, itemsPerPage]);

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalFilteredPages) {
      setCurrentPage(page);
    }
  };

  // Badges compiler matching Ashby design (Max 4 badges, overflow becomes +X more)
  const getRecommendationBadges = (c: RankResponseItem, details?: CandidateDetailResponse) => {
    const list: string[] = [];
    const skillScore = c.score_breakdown?.skill_score ?? details?.score_breakdown?.skill_score ?? 0;
    const expScore = c.score_breakdown?.experience_score ?? details?.score_breakdown?.experience_score ?? 0;
    const openToWork = c.open_to_work ?? details?.behavioral_signals?.open_to_work_flag ?? false;
    const isHoneypot = c.is_honeypot ?? details?.is_honeypot ?? false;
    const yearsExp = c.years_of_experience ?? details?.years_of_experience ?? 0;
    const responseRate = details?.behavioral_signals?.recruiter_response_rate || 0;

    if (skillScore >= 20 || c.score >= 60) {
      list.push("Strong Skill Match");
    }
    if (expScore >= 10 || yearsExp >= 3) {
      list.push("Relevant Experience");
    }
    if (openToWork) {
      list.push("Open to Work");
    }
    if (!isHoneypot) {
      list.push("Verified Timeline");
    }
    if (yearsExp >= 8) {
      list.push("Domain Experience");
    }
    if (responseRate >= 0.8) {
      list.push("High Recruiter Response");
    }

    return list.length ? list : ["Strong Profile"];
  };

  // Real calculations for the Summary strip
  const totalRanked = rankingQuery.data?.candidates?.length || 0;

  const highestScoreVal = useMemo(() => {
    const list = rankingQuery.data?.candidates || [];
    return list[0] ? `${list[0].score.toFixed(0)}` : "N/A";
  }, [rankingQuery.data]);

  const averageMatchScore = useMemo(() => {
    const list = rankingQuery.data?.candidates || [];
    if (list.length === 0) return "N/A";
    const sum = list.reduce((acc, c) => acc + c.score, 0);
    return `${(sum / list.length).toFixed(0)}`;
  }, [rankingQuery.data]);

  const riskProfilesFound = useMemo(() => {
    const list = rankingQuery.data?.candidates || [];
    let count = 0;
    list.forEach((c) => {
      if (c.is_honeypot === true) {
        count++;
      }
    });
    return count;
  }, [rankingQuery.data]);

  const verifiedProfilesCount = useMemo(() => {
    const total = rankingQuery.data?.candidates?.length || 0;
    return total - riskProfilesFound;
  }, [rankingQuery.data, riskProfilesFound]);

  // Featured Candidate Info (Rank #1)
  const featuredCandidate = rankingQuery.data?.candidates?.[0] || null;
  const featuredDetails = featuredCandidate ? cachedDetails[featuredCandidate.candidate_id] : null;

  const formatConciseSummary = (c: RankResponseItem, details?: CandidateDetailResponse) => {
    const role = c.current_title || details?.current_title || "Candidate";
    const comp = c.current_company || details?.current_company;
    const roleStr = comp ? `${role} at ${comp}` : role;
    const yoe = c.years_of_experience !== undefined ? c.years_of_experience : details?.years_of_experience;
    const expStr = yoe !== undefined ? ` with ${yoe.toFixed(1)} years of experience` : "";

    const matched = c.matched_skills || details?.matched_skills || c.critical_skills_matched || details?.critical_skills_matched || [];
    const cleanMatched = matched.map(s => s.split(" (via")[0].trim());
    const matchedStr = cleanMatched.length > 0 ? ` Strong evidence for ${cleanMatched.join(", ")}.` : "";

    const gaps = c.missing_skills || details?.missing_skills || c.missing_critical_skills || details?.missing_critical_skills || [];
    const cleanGaps = gaps.map(g => g.split(" (via")[0].trim());
    const gapsStr = cleanGaps.length > 0 ? ` Documented gaps include ${cleanGaps.join(", ")}.` : " No major critical skill gaps identified.";

    const isOpen = c.open_to_work ?? details?.behavioral_signals?.open_to_work_flag;
    const noticeDays = c.notice_period_days ?? details?.behavioral_signals?.notice_period_days;
    let signalStr = "";
    if (isOpen) {
      signalStr = noticeDays !== undefined ? ` Open to Work with a ${noticeDays}-day notice period.` : " Open to Work.";
    }

    return `${roleStr}${expStr}.${matchedStr}${gapsStr}${signalStr}`;
  };

  const featuredFeedback = useMemo(() => {
    if (!featuredCandidate) return { strengths: ["Screening..."], gaps: ["None"] };
    const list = getRecommendationBadges(featuredCandidate, featuredDetails || undefined);
    const rawGaps = featuredCandidate.missing_skills
      || featuredDetails?.missing_skills
      || featuredCandidate.missing_critical_skills
      || featuredDetails?.missing_critical_skills
      || [];
    const gaps = rawGaps.length ? rawGaps.map(g => g.split(" (via")[0].trim()) : ["None"];
    return { strengths: list, gaps };
  }, [featuredCandidate, featuredDetails]);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4 select-none">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Candidates</h1>
          <p className="text-muted-foreground">
            Sort, filter, and review profiles screened by the AI engine.
          </p>
        </div>
      </div>

      <QueryLoader loading={rankingQuery.loading} error={rankingQuery.error} retry={rankingQuery.execute}>
        {rankingQuery.data?.candidates && rankingQuery.data.candidates.length > 0 ? (
          <>
            {/* KPI Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Card className="bg-card border border-border shadow-sm premium-card-hover">
                <CardContent className="p-4 flex flex-col gap-1">
                  <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider select-none">Screened</span>
                  <div className="flex items-baseline mt-1.5">
                    <span className="text-2xl font-extrabold text-foreground">{totalRanked}</span>
                    <Users className="h-4 w-4 text-slate-400 ml-auto" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border border-border shadow-sm premium-card-hover">
                <CardContent className="p-4 flex flex-col gap-1">
                  <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider select-none">Top Fit Score</span>
                  <div className="flex items-baseline mt-1.5">
                    <span className="text-2xl font-extrabold text-emerald-500">{highestScoreVal} <span className="text-[10px] font-semibold text-muted-foreground">pts</span></span>
                    <Award className="h-4 w-4 text-emerald-500 ml-auto" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border border-border shadow-sm premium-card-hover">
                <CardContent className="p-4 flex flex-col gap-1">
                  <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider select-none">Average Match</span>
                  <div className="flex items-baseline mt-1.5">
                    <span className="text-2xl font-extrabold text-foreground">{averageMatchScore} <span className="text-[10px] font-semibold text-muted-foreground">pts</span></span>
                    <TrendingUp className="h-4 w-4 text-slate-400 ml-auto" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border border-border shadow-sm premium-card-hover">
                <CardContent className="p-4 flex flex-col gap-1">
                  <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider select-none">Verified Clear</span>
                  <div className="flex items-baseline mt-1.5">
                    <span className="text-2xl font-extrabold text-emerald-500">{verifiedProfilesCount}</span>
                    <ShieldCheck className="h-4 w-4 text-emerald-500 ml-auto" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border border-border shadow-sm premium-card-hover">
                <CardContent className="p-4 flex flex-col gap-1">
                  <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider select-none">Flagged Risk</span>
                  <div className="flex items-baseline mt-1.5">
                    <span className={`text-2xl font-extrabold ${riskProfilesFound > 0 ? "text-destructive" : "text-foreground"}`}>
                      {riskProfilesFound}
                    </span>
                    <ShieldAlert className="h-4 w-4 text-destructive ml-auto" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Featured Candidate Card (Primary Recruiter Focal Point) */}
            {featuredCandidate && (
              <Card className="border-border bg-card shadow-sm overflow-hidden relative animate-in fade-in duration-300">
                <div className="absolute top-0 right-0 bg-primary/10 text-primary px-3 py-1 text-xs font-bold rounded-bl-lg flex items-center gap-1 select-none">
                  <Zap className="h-3 w-3 animate-pulse" /> Best Candidate Match
                </div>

                <CardHeader className="pb-3 border-b border-border/40 bg-muted/5">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="bg-primary/20 text-primary border-primary/30">Rank #1 of {totalRanked}</Badge>
                    <CardTitle className="text-base font-mono text-primary">{featuredCandidate.candidate_id}</CardTitle>
                  </div>
                </CardHeader>

                <CardContent className="space-y-6 pt-5">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Score Panel */}
                    <div className="space-y-3">
                      <div>
                        <span className="text-xs text-muted-foreground font-semibold flex items-center gap-1 select-none relative group">
                          Sentinel Fit Score
                          <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 text-[10px] bg-slate-950 border border-border text-slate-100 rounded-lg shadow-md tooltip-custom-fade z-50">
                            Weighted fit score evaluated out of 100 points.
                          </span>
                        </span>
                        <div className="flex items-baseline gap-1.5 mt-1">
                          <span className="text-3xl font-extrabold text-foreground">{featuredCandidate.score.toFixed(1)} <span className="text-xs font-semibold text-muted-foreground">/ 100</span></span>
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                          <div style={{ width: `${Math.min(100, Math.max(0, featuredCandidate.score))}%` }} className="bg-emerald-500 h-full rounded-full" />
                        </div>
                      </div>

                      {/* Six Component Breakdown directly under score bar */}
                      {(() => {
                        const sb = featuredCandidate.score_breakdown || featuredDetails?.score_breakdown;
                        if (!sb) return null;
                        const baseSum = sb.skill_score + sb.experience_score + sb.education_score + sb.project_score + sb.behavior_score + sb.availability_score;
                        return (
                          <div className="pt-2 space-y-1.5 text-[11px] border-t border-border/40 select-none">
                            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-muted-foreground text-[10px]">
                              <div className="flex justify-between">
                                <span>Skills Match:</span>
                                <span className="font-semibold text-foreground">{sb.skill_score.toFixed(1)} / 40</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Experience Match:</span>
                                <span className="font-semibold text-foreground">{sb.experience_score.toFixed(1)} / 25</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Education Relevance:</span>
                                <span className="font-semibold text-foreground">{sb.education_score.toFixed(1)} / 10</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Projects & Evidence:</span>
                                <span className="font-semibold text-foreground">{sb.project_score.toFixed(1)} / 10</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Behaviour Signals:</span>
                                <span className="font-semibold text-foreground">{sb.behavior_score.toFixed(1)} / 10</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Availability:</span>
                                <span className="font-semibold text-foreground">{sb.availability_score.toFixed(1)} / 5</span>
                              </div>
                            </div>

                            <div className="pt-1.5 border-t border-border/30 space-y-0.5 text-[9px]">
                              <div className="flex justify-between text-muted-foreground">
                                <span>Base Component Score:</span>
                                <span className="font-semibold text-foreground">{baseSum.toFixed(1)} / 100.0</span>
                              </div>
                              {sb.engagement_bonus !== undefined && (
                                <div className="flex justify-between text-muted-foreground">
                                  <span>Engagement/Profile Adjustment:</span>
                                  <span className={sb.engagement_bonus > 0 ? "font-semibold text-emerald-500" : sb.engagement_bonus < 0 ? "font-semibold text-rose-500" : "font-semibold text-foreground"}>
                                    {sb.engagement_bonus > 0 ? "+" : ""}{sb.engagement_bonus.toFixed(1)}
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between font-bold text-primary pt-0.5">
                                <span>Final Sentinel Fit Score:</span>
                                <span>{featuredCandidate.score.toFixed(1)} / 100.0</span>
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    {/* Meta Details Panel */}
                    <div className="space-y-3.5">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-xs text-muted-foreground font-semibold block select-none">Experience</span>
                          <span className="text-xs font-bold text-foreground mt-0.5 block">
                            {featuredCandidate.years_of_experience !== undefined ? `${featuredCandidate.years_of_experience.toFixed(1)} Years` : featuredDetails ? `${featuredDetails.years_of_experience.toFixed(1)} Years` : "N/A"}
                          </span>
                        </div>
                        <div>
                          <span className="text-xs text-muted-foreground font-semibold flex items-center gap-1 select-none relative group">
                            Risk Status
                            <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 text-[10px] bg-slate-950 border border-border text-slate-100 rounded-lg shadow-md tooltip-custom-fade z-50">
                              Evaluates profile data completeness and screens for chronological discrepancies or salary anomalies to flag potential fraud.
                            </span>
                          </span>
                          <div className="mt-1">
                            {(featuredCandidate.is_honeypot ?? featuredDetails?.is_honeypot) ? (
                              <Badge variant="destructive" className="gap-1 text-[10px] py-0.5 font-bold whitespace-nowrap">
                                <ShieldAlert className="h-3 w-3" /> Flagged Risk
                              </Badge>
                            ) : (
                              <Badge variant="success" className="gap-1 text-[10px] py-0.5 font-bold whitespace-nowrap">
                                <ShieldCheck className="h-3 w-3" /> Verified Clear
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>

                      <div>
                        <span className="text-xs text-muted-foreground font-semibold block select-none">Top Standing Skills</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {(() => {
                            const skillsList = featuredCandidate.skills && featuredCandidate.skills.length > 0
                              ? featuredCandidate.skills
                              : featuredDetails?.skills && featuredDetails.skills.length > 0
                              ? featuredDetails.skills.map(s => s.name)
                              : [];

                            return skillsList.length > 0 ? (
                              skillsList.slice(0, 3).map((name) => (
                                <Badge key={name} variant="outline" className="text-[10px] py-0.5 bg-background text-foreground border-border font-medium whitespace-nowrap">
                                  {name}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">None listed</span>
                            );
                          })()}
                        </div>
                      </div>

                      <div>
                        <span className="text-xs text-muted-foreground font-semibold block select-none">Availability & Signals</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {(() => {
                            const isOpen = featuredCandidate.open_to_work ?? featuredDetails?.behavioral_signals?.open_to_work_flag;
                            const noticeDays = featuredCandidate.notice_period_days ?? featuredDetails?.behavioral_signals?.notice_period_days;

                            return (
                              <>
                                {isOpen && (
                                  <Badge variant="success" className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[10px] py-0 px-1 font-bold whitespace-nowrap">
                                    Open to Work
                                  </Badge>
                                )}
                                {noticeDays !== undefined && (
                                  <Badge variant="secondary" className="text-[10px] py-0 px-1 bg-secondary text-secondary-foreground font-semibold whitespace-nowrap">
                                    {noticeDays === 0 ? "Immediate Availability" : noticeDays <= 30 ? "Short Notice (≤30 days)" : `Notice: ${noticeDays}d`}
                                  </Badge>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      </div>
                    </div>

                    {/* AI Justification Strengths and Gaps */}
                    <div className="space-y-3">
                      <div>
                        <span className="text-xs text-muted-foreground font-semibold block select-none font-sans">Why Recommended</span>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {featuredFeedback.strengths.slice(0, 3).map((badge, idx) => (
                            <Badge key={idx} variant="outline" className="text-[10px] py-0 bg-background text-emerald-500 border-emerald-500/20 whitespace-nowrap">
                              {badge}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div className="pt-2 border-t border-border/40 select-none">
                        <span className="text-[10px] text-amber-500 font-bold block uppercase tracking-wider">Identified Gaps</span>
                        <ul className="text-[10px] text-muted-foreground list-disc pl-3 mt-1 space-y-0.5">
                          {featuredFeedback.gaps.map((gap, idx) => (
                            <li key={idx} className="leading-tight">{gap}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Recruiter search controls */}
            <div className="flex flex-col gap-4 border border-border bg-card rounded-xl p-4 shadow-sm animate-in fade-in duration-300">
              <span className="text-xs font-bold text-foreground uppercase tracking-wider text-[10px] select-none">Search & Filtration Filters</span>

              <div className="flex flex-wrap gap-4 items-center justify-between">
                {/* Search */}
                <div className="relative w-full max-w-sm flex-1">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground/60" />
                  <Input
                    placeholder="Search candidate ID, skills, company, role, location..."
                    className="pl-9 text-xs focus-visible:ring-primary focus-visible:ring-offset-0 border-border"
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value);
                      setCurrentPage(1);
                    }}
                  />
                </div>

                {/* Recruiter Drill Selectors */}
                <div className="flex flex-wrap gap-2 items-center select-none">
                  <select
                    value={fraudFilter}
                    onChange={(e) => { setFraudFilter(e.target.value as any); setCurrentPage(1); }}
                    className="bg-background border rounded-lg px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground outline-none transition-all cursor-pointer hover:border-primary/40 focus:border-primary border-border"
                  >
                    <option value="all">Risk Level: All</option>
                    <option value="low">Risk Level: Verified Clear</option>
                    <option value="high">Risk Level: Flagged Risk</option>
                  </select>

                  <select
                    value={openToWorkFilter}
                    onChange={(e) => { setOpenToWorkFilter(e.target.value as any); setCurrentPage(1); }}
                    className="bg-background border rounded-lg px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground outline-none transition-all cursor-pointer hover:border-primary/40 focus:border-primary border-border"
                  >
                    <option value="all">Open to Work: All</option>
                    <option value="yes">Only Open to Work</option>
                  </select>

                  <select
                    value={noticeFilter}
                    onChange={(e) => { setNoticeFilter(e.target.value as any); setCurrentPage(1); }}
                    className="bg-background border rounded-lg px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground outline-none transition-all cursor-pointer hover:border-primary/40 focus:border-primary border-border"
                  >
                    <option value="all">Notice Period: All</option>
                    <option value="immediate">Immediate Availability</option>
                    <option value="short">Short Notice (≤ 30 days)</option>
                  </select>

                  <select
                    value={experienceFilter}
                    onChange={(e) => { setExperienceFilter(e.target.value as any); setCurrentPage(1); }}
                    className="bg-background border rounded-lg px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground outline-none transition-all cursor-pointer hover:border-primary/40 focus:border-primary border-border"
                  >
                    <option value="all">Experience: All</option>
                    <option value="0-2">Entry Level (0-2y)</option>
                    <option value="3-5">Mid Level (3-5y)</option>
                    <option value="6-9">Senior Level (6-9y)</option>
                    <option value="10+">Lead / Principal (10y+)</option>
                  </select>



                  <Input
                    placeholder="Filter Location..."
                    className="w-32 h-8 text-xs font-semibold focus-visible:ring-primary focus-visible:ring-offset-0 border border-border rounded-lg bg-background"
                    value={locationFilter}
                    onChange={(e) => {
                      setLocationFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Core Ranks Workspace Table */}
            <Card className="border border-border bg-card shadow-sm">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/10 hover:bg-muted/10 border-b select-none">
                      <TableHead className="w-[80px] text-center font-bold cursor-pointer select-none" onClick={() => handleSort("rank")}>
                        <div className="flex items-center justify-center gap-1">
                          Rank {getSortIcon("rank")}
                        </div>
                      </TableHead>
                      <TableHead className="w-[180px] cursor-pointer select-none" onClick={() => handleSort("candidate_id")}>
                        <div className="flex items-center gap-1">
                          Candidate {getSortIcon("candidate_id")}
                        </div>
                      </TableHead>
                      <TableHead className="w-[120px] cursor-pointer select-none" onClick={() => handleSort("score")}>
                        <div className="flex items-center gap-1 relative group">
                          AI Fit Score
                          <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 text-[10px] bg-slate-950 border border-border text-slate-100 rounded-lg shadow-md tooltip-custom-fade z-50 font-normal">
                            Weighted score combining core skills match (60%), experience alignment (15%), and behavioral responsiveness signals (25%).
                          </span>
                          {getSortIcon("score")}
                        </div>
                      </TableHead>
                      <TableHead className="w-[200px]">Top Skills</TableHead>
                      <TableHead className="w-[240px]">Strengths & Missing Skills</TableHead>
                      <TableHead className="w-[125px]">Notice Period</TableHead>
                      <TableHead className="w-[70px] text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedFilteredCandidates.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="h-32 text-center">
                          <div className="flex flex-col items-center justify-center gap-1.5 p-6 animate-in fade-in duration-300">
                            <AlertTriangle className="h-5 w-5 text-amber-500 mb-1" />
                            <p className="font-bold text-foreground text-sm">
                              No candidates match the current filters.
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Try adjusting search query, filters, or clearing location text searches.
                            </p>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      paginatedFilteredCandidates.map((c) => {
                        const details = cachedDetails[c.candidate_id];
                        const isExpanded = !!expandedRows[c.candidate_id];
                        const isHoneypot = details?.is_honeypot ?? false;

                        // Structured strengths and missing skills from backend evaluation
                        const rawStrengths: string[] = c.matched_skills || details?.matched_skills || c.critical_skills_matched || details?.critical_skills_matched || c.skills || [];
                        const rawGaps: string[] = c.missing_skills || details?.missing_skills || c.missing_critical_skills || details?.missing_critical_skills || [];

                        const strengths: string[] = rawStrengths.map((s: string) => s.split(" (via")[0].trim());
                        const gaps: string[] = rawGaps.map((g: string) => g.split(" (via")[0].trim());


                        return (
                          <React.Fragment key={c.candidate_id}>
                            <TableRow
                              className={`transition-colors duration-150 cursor-pointer even:bg-muted/5 hover:bg-muted/10 ${
                                isHoneypot ? "bg-destructive/5 hover:bg-destructive/10" : ""
                              }`}
                              onClick={() => toggleRow(c.candidate_id)}
                            >
                              {/* Rank */}
                              <TableCell className="font-extrabold text-center text-foreground">{c.rank}</TableCell>
                              
                              {/* Candidate ID, Role, Company, Location */}
                              <TableCell className="font-mono text-primary font-bold">
                                {highlightText(c.candidate_id, searchTerm)}
                                <div className="text-[10px] text-muted-foreground mt-0.5 font-medium max-w-[170px] space-y-0.5">
                                  {c.current_title && c.current_company && (
                                    <div className="truncate font-semibold text-foreground">
                                      {highlightText(c.current_title, searchTerm)} at {highlightText(c.current_company, searchTerm)}
                                    </div>
                                  )}
                                  {c.location && (
                                    <div className="text-[9px] text-muted-foreground/80 truncate">
                                      {highlightText(c.location, searchTerm)}
                                    </div>
                                  )}
                                </div>
                              </TableCell>

                              {/* Sentinel Fit Score (Clickable popover breakdown) */}
                              <TableCell className="relative space-y-1 cursor-pointer select-none" onClick={() => setPopoverCandidateId(popoverCandidateId === c.candidate_id ? null : c.candidate_id)}>
                                <div className="flex justify-between items-baseline whitespace-nowrap">
                                  <span className="font-bold text-foreground text-xs">{c.score.toFixed(1)} / 100</span>
                                  <span className="text-[9px] text-muted-foreground font-semibold">({Math.round(c.score)} pts)</span>
                                </div>
                                <div className="w-full bg-secondary h-1 rounded-full overflow-hidden">
                                  <div
                                    style={{ width: `${Math.min(100, c.score)}%` }}
                                    className={`h-full rounded-full ${c.score >= 80 ? "bg-emerald-500" : c.score >= 60 ? "bg-indigo-500" : "bg-amber-500"}`}
                                  />
                                </div>
                                
                                {popoverCandidateId === c.candidate_id && c.score_breakdown && (
                                  <div className="absolute z-50 mt-1 p-3 bg-popover text-popover-foreground border border-border rounded-xl shadow-xl w-52 text-[11px] space-y-1 animate-in fade-in zoom-in duration-100 left-0" onClick={(e) => e.stopPropagation()}>
                                    <div className="font-bold border-b pb-1 mb-1 text-xs text-foreground">Sentinel Score Breakdown</div>
                                    <div className="flex justify-between"><span>Skills Match:</span> <span className="font-bold text-foreground">{c.score_breakdown.skill_score.toFixed(1)} / 40.0</span></div>
                                    <div className="flex justify-between"><span>Experience Match:</span> <span className="font-bold text-foreground">{c.score_breakdown.experience_score.toFixed(1)} / 25.0</span></div>
                                    <div className="flex justify-between"><span>Education Match:</span> <span className="font-bold text-foreground">{c.score_breakdown.education_score.toFixed(1)} / 10.0</span></div>
                                    <div className="flex justify-between"><span>Project Evidence:</span> <span className="font-bold text-foreground">{c.score_breakdown.project_score.toFixed(1)} / 10.0</span></div>
                                    <div className="flex justify-between"><span>Behaviour Signals:</span> <span className="font-bold text-foreground">{c.score_breakdown.behavior_score.toFixed(1)} / 10.0</span></div>
                                    <div className="flex justify-between"><span>Availability:</span> <span className="font-bold text-foreground">{c.score_breakdown.availability_score.toFixed(1)} / 5.0</span></div>
                                    <div className="flex justify-between border-t pt-1 mt-1"><span>Base Component Score:</span> <span className="font-bold text-foreground">{(c.score_breakdown.skill_score + c.score_breakdown.experience_score + c.score_breakdown.education_score + c.score_breakdown.project_score + c.score_breakdown.behavior_score + c.score_breakdown.availability_score).toFixed(1)}</span></div>
                                    {c.score_breakdown.engagement_bonus !== undefined && (
                                      <div className="flex justify-between"><span>Engagement/Profile Adjustment:</span> <span className={`font-bold ${c.score_breakdown.engagement_bonus > 0 ? 'text-emerald-500' : c.score_breakdown.engagement_bonus < 0 ? 'text-rose-500' : 'text-foreground'}`}>{c.score_breakdown.engagement_bonus > 0 ? '+' : ''}{c.score_breakdown.engagement_bonus.toFixed(1)}</span></div>
                                    )}
                                    <div className="flex justify-between border-t pt-1 mt-1 font-bold text-primary"><span>Final Sentinel Fit Score:</span> <span>{c.score.toFixed(1)} / 100.0</span></div>
                                    <div className="text-[9px] text-muted-foreground pt-1 text-center font-normal">Click score to close</div>
                                  </div>
                                )}
                              </TableCell>

                              {/* Top Skills */}
                              <TableCell>
                                <div className="flex flex-wrap gap-1 max-w-[190px]">
                                  {c.skills && c.skills.length > 0 ? (
                                    c.skills.slice(0, 3).map((s: string, i: number) => (
                                      <Badge key={i} variant="secondary" className="text-[9px] py-0 px-1.5 bg-muted/65 hover:bg-muted text-muted-foreground font-semibold select-none whitespace-nowrap">
                                        {highlightText(s, searchTerm)}
                                      </Badge>
                                    ))
                                  ) : (
                                    <span className="text-[10px] text-muted-foreground">Not specified</span>
                                  )}
                                  {c.skills && c.skills.length > 3 && (
                                    <Badge variant="outline" className="text-[9px] py-0 px-1 bg-muted border-border whitespace-nowrap text-muted-foreground select-none">
                                      +{c.skills.length - 3} more
                                    </Badge>
                                  )}
                                </div>
                              </TableCell>

                              {/* Strengths & Missing Skills */}
                              <TableCell>
                                <div className="flex flex-col gap-1.5 max-w-[230px]">
                                  {/* Strengths */}
                                  {strengths.length > 0 && (
                                    <div className="flex flex-wrap items-center gap-1">
                                      <span className="text-[9px] font-bold text-emerald-600 uppercase select-none mr-0.5">Matched:</span>
                                      {strengths.slice(0, 3).map((s: string, i: number) => (
                                        <Badge key={i} variant="outline" className="text-[9px] py-0 px-1.5 bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 whitespace-nowrap font-medium select-none">
                                          {highlightText(s, searchTerm)}
                                        </Badge>
                                      ))}
                                      {strengths.length > 3 && (
                                        <Badge variant="outline" className="text-[9px] py-0 px-1 bg-muted border-border whitespace-nowrap text-muted-foreground select-none">
                                          +{strengths.length - 3} more
                                        </Badge>
                                      )}
                                    </div>
                                  )}
                                  {/* Missing Skills */}
                                  {gaps.length > 0 && (
                                    <div className="flex flex-wrap items-center gap-1">
                                      <span className="text-[9px] font-bold text-destructive uppercase select-none mr-0.5">Missing:</span>
                                      {gaps.slice(0, 2).map((g: string, i: number) => (
                                        <Badge key={i} variant="outline" className="text-[9px] py-0 px-1.5 bg-destructive/10 text-destructive border border-destructive/20 whitespace-nowrap font-medium select-none">
                                          {highlightText(g, searchTerm)}
                                        </Badge>
                                      ))}
                                      {gaps.length > 2 && (
                                        <Badge variant="outline" className="text-[9px] py-0 px-1 bg-muted border-border whitespace-nowrap text-muted-foreground select-none">
                                          +{gaps.length - 2} more
                                        </Badge>
                                      )}
                                    </div>
                                  )}
                                  {strengths.length === 0 && gaps.length === 0 && (
                                    <span className="text-xs text-muted-foreground select-none italic">General profile screening</span>
                                  )}
                                </div>
                              </TableCell>

                              {/* Notice Period */}
                              <TableCell>
                                {(() => {
                                  const noticeDays = c.notice_period_days ?? details?.behavioral_signals?.notice_period_days;
                                  const isOpen = c.open_to_work ?? details?.behavioral_signals?.open_to_work_flag;

                                  if (noticeDays !== undefined) {
                                    return (
                                      <div className="flex flex-col gap-1">
                                        <span className="font-semibold text-xs text-foreground">
                                          {noticeDays === 0 ? "Immediate" : `${noticeDays} days`}
                                        </span>
                                        {isOpen && (
                                          <span className="text-[9px] text-emerald-500 font-bold select-none whitespace-nowrap">
                                            ● Open to Work
                                          </span>
                                        )}
                                      </div>
                                    );
                                  }

                                  return (
                                    <span className="text-xs text-muted-foreground font-medium select-none">Standard</span>
                                  );
                                })()}
                              </TableCell>

                              {/* Actions */}
                              <TableCell onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center justify-end gap-1 select-none">
                                  <div className="relative group">
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-8 w-8 hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                                      onClick={() => toggleRow(c.candidate_id)}
                                      aria-label={isExpanded ? "Collapse details" : "Expand details"}
                                    >
                                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                    </Button>
                                    <span className="absolute bottom-full right-0 mb-1.5 w-24 p-1.5 text-[9px] bg-slate-900 border border-border text-slate-100 rounded shadow-md text-center tooltip-custom-fade z-50">
                                      Toggle Details
                                    </span>
                                  </div>
                                  
                                  <Link href={`/candidate/${c.candidate_id}`} onClick={() => {
                                    if (typeof window !== "undefined") {
                                      sessionStorage.setItem(`candidate_list_item_${c.candidate_id}`, JSON.stringify(c));
                                      if (cachedDetails[c.candidate_id]) {
                                        sessionStorage.setItem(`candidate_detail_${c.candidate_id}`, JSON.stringify(cachedDetails[c.candidate_id]));
                                      }
                                    }
                                  }}>
                                    <div className="relative group">
                                      <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-muted text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary" aria-label="View Candidate Profile">
                                        <Eye className="h-4 w-4" />
                                      </Button>
                                      <span className="absolute bottom-full right-0 mb-1.5 w-32 p-1.5 text-[9px] bg-slate-900 border border-border text-slate-100 rounded shadow-md text-center tooltip-custom-fade z-50">
                                        View Full Profile
                                      </span>
                                    </div>
                                  </Link>
                                </div>
                              </TableCell>
                            </TableRow>

                            {/* Animated Expandable Row Details Panel */}
                            <AnimatePresence initial={false}>
                              {isExpanded && (
                                <TableRow className="bg-muted/10 border-b hover:bg-muted/10 select-none">
                                  <TableCell colSpan={7} className="p-0">
                                    <motion.div
                                      initial={{ height: 0, opacity: 0 }}
                                      animate={{ height: "auto", opacity: 1 }}
                                      exit={{ height: 0, opacity: 0 }}
                                      transition={{ duration: 0.2 }}
                                      className="overflow-hidden"
                                    >
                                      <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                                        {/* Sub scores breakdown */}
                                        <div className="space-y-4">
                                          <h4 className="font-bold text-foreground flex items-center gap-1.5 border-b pb-1">
                                            <Zap className="h-4 w-4 text-primary" /> Match Breakdown
                                          </h4>

                                          {details ? (
                                            <div className="space-y-2.5">
                                              <div className="space-y-1">
                                                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                                                  <span>Skills Match (40%)</span>
                                                  <span className="text-foreground">{details.score_breakdown.skill_score.toFixed(1)}/40 ({Math.round((details.score_breakdown.skill_score / 40) * 100)}%)</span>
                                                </div>
                                                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                                                  <div style={{ width: `${Math.min(100, (details.score_breakdown.skill_score / 40) * 100)}%` }} className="bg-primary h-full rounded-full" />
                                                </div>
                                              </div>

                                              <div className="space-y-1">
                                                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                                                  <span>Experience Match (25%)</span>
                                                  <span className="text-foreground">{details.score_breakdown.experience_score.toFixed(1)}/25 ({Math.round((details.score_breakdown.experience_score / 25) * 100)}%)</span>
                                                </div>
                                                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                                                  <div style={{ width: `${(details.score_breakdown.experience_score / 25) * 100}%` }} className="bg-indigo-500 h-full rounded-full" />
                                                </div>
                                              </div>

                                              <div className="space-y-1">
                                                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                                                  <span>Education Relevance (10%)</span>
                                                  <span className="text-foreground">{details.score_breakdown.education_score.toFixed(1)}/10 ({Math.round((details.score_breakdown.education_score / 10) * 100)}%)</span>
                                                </div>
                                                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                                                  <div style={{ width: `${(details.score_breakdown.education_score / 10) * 100}%` }} className="bg-amber-500 h-full rounded-full" />
                                                </div>
                                              </div>

                                              <div className="space-y-1">
                                                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                                                  <span>Projects & Evidence (10%)</span>
                                                  <span className="text-foreground">{details.score_breakdown.project_score.toFixed(1)}/10 ({Math.round((details.score_breakdown.project_score / 10) * 100)}%)</span>
                                                </div>
                                                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                                                  <div style={{ width: `${(details.score_breakdown.project_score / 10) * 100}%` }} className="bg-violet-500 h-full rounded-full" />
                                                </div>
                                              </div>

                                              <div className="space-y-1">
                                                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                                                  <span>Behaviour Signals (10%)</span>
                                                  <span className="text-foreground">{details.score_breakdown.behavior_score.toFixed(1)}/10 ({Math.round((details.score_breakdown.behavior_score / 10) * 100)}%)</span>
                                                </div>
                                                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                                                  <div style={{ width: `${(details.score_breakdown.behavior_score / 10) * 100}%` }} className="bg-emerald-500 h-full rounded-full" />
                                                </div>
                                              </div>

                                              <div className="space-y-1 pb-2 border-b">
                                                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                                                  <span>Availability (5%)</span>
                                                  <span className="text-foreground">{details.score_breakdown.availability_score.toFixed(1)}/5 ({Math.round((details.score_breakdown.availability_score / 5) * 100)}%)</span>
                                                </div>
                                                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                                                  <div style={{ width: `${(details.score_breakdown.availability_score / 5) * 100}%` }} className="bg-sky-500 h-full rounded-full" />
                                                </div>
                                              </div>

                                              <div className="space-y-1.5 pt-1">
                                                <div className="flex justify-between text-xs font-medium text-muted-foreground">
                                                  <span>Base Component Score</span>
                                                  <span className="text-foreground font-semibold">
                                                    {(details.score_breakdown.skill_score + details.score_breakdown.experience_score + details.score_breakdown.education_score + details.score_breakdown.project_score + details.score_breakdown.behavior_score + details.score_breakdown.availability_score).toFixed(1)} / 100.0
                                                  </span>
                                                </div>
                                                {details.score_breakdown.engagement_bonus !== undefined && (
                                                  <div className="flex justify-between text-xs font-medium text-muted-foreground">
                                                    <span>Engagement/Profile Adjustment</span>
                                                    <span className={details.score_breakdown.engagement_bonus > 0 ? "text-emerald-500 font-semibold" : details.score_breakdown.engagement_bonus < 0 ? "text-rose-500 font-semibold" : "text-foreground font-semibold"}>
                                                      {details.score_breakdown.engagement_bonus > 0 ? "+" : ""}{details.score_breakdown.engagement_bonus.toFixed(1)}
                                                    </span>
                                                  </div>
                                                )}
                                                <div className="flex justify-between text-sm font-bold text-foreground pt-1 border-t">
                                                  <span>Final Sentinel Fit Score</span>
                                                  <span className="text-primary">{details.score_breakdown.final_score.toFixed(1)} / 100.0</span>
                                                </div>
                                              </div>
                                            </div>
                                          ) : (
                                            <div className="space-y-2">
                                              <div className="h-4 bg-muted/60 rounded animate-pulse" />
                                              <div className="h-4 bg-muted/60 rounded animate-pulse" />
                                            </div>
                                          )}
                                        </div>

                                        {/* Behavioral Signal Details & Recruiter Indicators */}
                                        <div className="space-y-4">
                                          <h4 className="font-bold text-foreground flex items-center gap-1.5 border-b pb-1">
                                            <Clock className="h-4 w-4 text-primary" /> Candidate Signals
                                          </h4>

                                          {details && details.behavioral_signals ? (
                                            <div className="space-y-4">
                                              <div className="grid grid-cols-2 gap-3 text-xs">
                                                <div className="p-2 border rounded-lg bg-card shadow-sm flex flex-col gap-0.5">
                                                  <span className="text-muted-foreground font-medium uppercase tracking-wider text-[10px]">Work Mode</span>
                                                  <span className="font-bold text-foreground capitalize">{details.behavioral_signals.preferred_work_mode}</span>
                                                </div>

                                                <div className="p-2 border rounded-lg bg-card shadow-sm flex flex-col gap-0.5">
                                                  <span className="text-muted-foreground font-medium uppercase tracking-wider text-[10px]">Notice Period</span>
                                                  <span className="font-bold text-foreground">{details.behavioral_signals.notice_period_days} days</span>
                                                </div>

                                                <div className="p-2 border rounded-lg bg-card shadow-sm flex flex-col gap-0.5">
                                                  <span className="text-muted-foreground font-medium uppercase tracking-wider text-[10px]">Response Rate</span>
                                                  <span className="font-bold text-foreground">{Math.round(details.behavioral_signals.recruiter_response_rate * 100)}%</span>
                                                </div>

                                                <div className="p-2 border rounded-lg bg-card shadow-sm flex flex-col gap-0.5">
                                                  <span className="text-muted-foreground font-medium uppercase tracking-wider text-[10px]">Interview Rate</span>
                                                  <span className="font-bold text-foreground">{Math.round(details.behavioral_signals.interview_completion_rate * 100)}%</span>
                                                </div>
                                              </div>

                                              <div className="p-3 border rounded-lg bg-card/60 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                                                <div>Experience: <span className="font-bold text-foreground">{details.years_of_experience} Years</span></div>
                                                <div>Completeness: <span className="font-bold text-foreground">{Math.round(details.behavioral_signals.profile_completeness_score)}%</span></div>
                                                <div className="col-span-2">Location: <span className="font-bold text-foreground truncate block" title={details.location}>{details.location}</span></div>
                                              </div>
                                            </div>
                                          ) : (
                                            <div className="grid grid-cols-2 gap-2">
                                              <div className="h-10 bg-muted/60 rounded animate-pulse" />
                                              <div className="h-10 bg-muted/60 rounded animate-pulse" />
                                            </div>
                                          )}
                                        </div>

                                        {/* Full Factual Explainability Reasoning (Bulleted, scannable layout) */}
                                        <div className="space-y-4 col-span-1 md:col-span-2">
                                          <h4 className="font-bold text-foreground flex items-center gap-1.5 border-b pb-1">
                                            <FileText className="h-4 w-4 text-primary" /> Factual Recommendation Reasoning
                                          </h4>

                                          {(() => {
                                            const matchedSkillsList = c.critical_skills_matched || details?.critical_skills_matched || [];
                                            const missingSkillsList = c.missing_critical_skills || details?.missing_critical_skills || [];

                                            return (
                                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div className="space-y-3">
                                                  <div className="p-4 border rounded-xl bg-card shadow-sm space-y-1.5 h-full">
                                                    <span className="text-[9px] text-primary font-bold uppercase tracking-wider select-none">Screening Summary & Justification</span>
                                                    <p className="text-xs text-foreground font-medium leading-relaxed pt-1">
                                                      {highlightText(formatConciseSummary(c, details), searchTerm)}
                                                    </p>
                                                  </div>
                                                </div>

                                                <div className="space-y-3">
                                                  <div className="p-4 border rounded-xl bg-card shadow-sm space-y-2 h-full">
                                                    <span className="text-[9px] text-primary font-bold uppercase tracking-wider select-none">Key Indicators</span>
                                                    <div className="space-y-2 text-xs text-muted-foreground pt-1">
                                                       {matchedSkillsList.length > 0 && (
                                                         <div>
                                                           <span className="font-bold text-emerald-600 text-[10px] uppercase block mb-1">✓ Matched Critical Skills:</span>
                                                           <div className="flex flex-wrap gap-1">
                                                             {matchedSkillsList.map((skill, idx) => (
                                                               <Badge key={idx} variant="outline" className="text-[9px] py-0.5 px-1.5 bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 font-medium">
                                                                 {skill}
                                                               </Badge>
                                                             ))}
                                                           </div>
                                                         </div>
                                                       )}
                                                       {missingSkillsList.length > 0 && (
                                                         <div>
                                                           <span className="font-bold text-destructive text-[10px] uppercase block mb-1">✗ Missing Requirements:</span>
                                                           <div className="flex flex-wrap gap-1">
                                                             {missingSkillsList.map((skill, idx) => (
                                                               <Badge key={idx} variant="outline" className="text-[9px] py-0.5 px-1.5 bg-destructive/10 text-destructive border border-destructive/20 font-medium">
                                                                 {skill}
                                                               </Badge>
                                                             ))}
                                                           </div>
                                                         </div>
                                                       )}
                                                       {isHoneypot && (
                                                         <div>
                                                           <span className="font-bold text-destructive text-[10px] uppercase block mb-0.5">⚠ Verification Risk:</span>
                                                           <p className="text-[11px] text-destructive font-medium">Profile flagged for chronological duration anomalies.</p>
                                                         </div>
                                                       )}
                                                     </div>
                                                  </div>
                                                </div>
                                              </div>
                                            );
                                          })()}
                                        </div>
                                      </div>
                                    </motion.div>
                                  </TableCell>
                                </TableRow>
                              )}
                            </AnimatePresence>
                          </React.Fragment>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Pagination Controls */}
            <div className="flex flex-wrap items-center justify-between gap-4 mt-4 select-none">
              <span className="text-xs text-muted-foreground font-semibold">
                Showing Page {currentPage} of {totalFilteredPages} ({filteredCandidates.length} filtered candidates)
              </span>

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground font-semibold">Rows per page:</span>
                  <select
                    value={itemsPerPage}
                    onChange={(e) => {
                      setItemsPerPage(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="bg-background border border-border rounded-lg px-2 py-1 text-xs font-semibold outline-none cursor-pointer hover:border-primary/40 focus:border-primary transition-colors"
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="gap-1 text-xs"
                  >
                    <ChevronLeft className="h-4 w-4" /> Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalFilteredPages}
                    className="gap-1 text-xs"
                  >
                    Next <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Recruiter-friendly Empty State */
          <Card className="border-dashed py-16 text-center shadow-sm">
            <CardContent className="flex flex-col items-center justify-center gap-4 max-w-md mx-auto">
              <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                <Users className="h-8 w-8" />
              </div>

              <div>
                <h3 className="text-xl font-bold text-foreground">Candidates List is Unranked</h3>
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
                  Upload a Job Description or paste your requirements to execute candidate matching, evaluate fraud profiles, and view scoring rankings.
                </p>
              </div>

              <Link href="/rank">
                <Button className="mt-2 font-semibold gap-2">
                  <Zap className="h-4 w-4" /> Run Candidate Screening
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </QueryLoader>
    </div>
  );
}
