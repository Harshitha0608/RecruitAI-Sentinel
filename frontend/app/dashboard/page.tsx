"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import { apiService } from "@/services/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Database, 
  FileText, 
  CheckCircle, 
  XCircle, 
  Search, 
  RefreshCw, 
  Cpu, 
  Users, 
  Award, 
  TrendingUp, 
  ShieldCheck, 
  ShieldAlert, 
  Clock,
  AlertCircle
} from "lucide-react";

export default function Dashboard() {
  const analyticsQuery = useApi(apiService.getAnalytics, true);
  const rankingQuery = useApi(apiService.getTop100, true);

  const [lastRankingTime, setLastRankingTime] = useState<string>("Never");

  const handleRefresh = () => {
    analyticsQuery.execute().catch(() => {});
    rankingQuery.execute().catch(() => { });
  };

  const isRefreshing = analyticsQuery.loading || rankingQuery.loading;

  const candidateCount = analyticsQuery.data?.candidate_count || 0;
  const indexedCandidates = analyticsQuery.data?.indexed_candidates || 0;
  const dimension = analyticsQuery.data?.embedding_dimension || 0;
  const faissLoaded = analyticsQuery.data?.faiss_loaded ?? false;
  const tfidfLoaded = analyticsQuery.data?.tfidf_loaded ?? false;
  const modelLoaded = analyticsQuery.data?.model_loaded ?? false;
  const sqliteConnected = analyticsQuery.data?.sqlite_connected ?? false;

  const top100Count = rankingQuery.data?.candidates?.length || 0;
  const topCandidate = rankingQuery.data?.candidates?.[0] || null;

  // Retrieve last ranking run time from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedTime = window.localStorage.getItem("sentinel_last_ranking_time");
      if (storedTime) {
        try {
          const date = new Date(storedTime);
          setLastRankingTime(date.toLocaleString());
        } catch {
          setLastRankingTime("Never");
        }
      }
    }
  }, [rankingQuery.data]);

  // Derive recruiter analytics metrics
  const averageScore = top100Count > 0
    ? (rankingQuery.data!.candidates.reduce((sum, c) => sum + c.score, 0) / top100Count).toFixed(2)
    : "N/A";

  const highestScore = top100Count > 0
    ? Math.max(...rankingQuery.data!.candidates.map(c => c.score)).toFixed(2)
    : "N/A";

  const flaggedCount = analyticsQuery.data?.latest_honeypot_rate !== undefined && analyticsQuery.data?.latest_honeypot_rate !== null
    ? Math.round(analyticsQuery.data.latest_honeypot_rate * 1000)
    : 0;

  const verifiedCount = top100Count > 0 ? (indexedCandidates - flaggedCount) : 0;

  const pipelineRuntime = analyticsQuery.data?.latest_pipeline_runtime_ms !== undefined && analyticsQuery.data?.latest_pipeline_runtime_ms !== null
    ? `${(analyticsQuery.data.latest_pipeline_runtime_ms / 1000).toFixed(2)}s`
    : "N/A";

  const showRankingsExist = top100Count > 0 && rankingQuery.data?.success;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground animate-in slide-in-from-left duration-300">Dashboard</h1>
          <p className="text-muted-foreground">
            System overview, indexing statuses, and latest ranking metrics.
          </p>
        </div>
        <Button onClick={handleRefresh} variant="outline" className="gap-2 border-primary/20 hover:border-primary/40" disabled={isRefreshing}>
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} /> Refresh Core Data
        </Button>
      </div>

      {analyticsQuery.error && (
        <div className="flex items-center gap-3 p-4 border border-destructive/20 rounded-xl bg-destructive/5 text-destructive text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <div>
            <span className="font-bold">System Status Warning:</span> {analyticsQuery.error}
          </div>
          <Button size="sm" variant="ghost" className="ml-auto text-destructive hover:bg-destructive/10" onClick={handleRefresh}>
            Retry Connection
          </Button>
        </div>
      )}

      {/* SECTION 1: System Indexing & Status (Instantly loaded or showing skeletons) */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-foreground">Core Indexing Status</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {analyticsQuery.loading ? (
            Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="h-28 rounded-xl border bg-card animate-pulse" />
            ))
          ) : (
            <>
              <Card className="hover:shadow-sm transition-all border-border bg-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Indexed Candidates
                  </CardTitle>
                  <Database className="h-4.5 w-4.5 text-primary" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-extrabold text-foreground">{indexedCandidates}</div>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Parsed from {candidateCount} total profiles
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-sm transition-all border-border bg-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Embedding Dimension
                  </CardTitle>
                  <Cpu className="h-4.5 w-4.5 text-primary" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-extrabold text-foreground">{dimension}</div>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Dense features dimensions (FAISS)
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-sm transition-all border-border bg-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    TF-IDF Lexical Status
                  </CardTitle>
                  {tfidfLoaded ? (
                    <CheckCircle className="h-4.5 w-4.5 text-emerald-500" />
                  ) : (
                    <XCircle className="h-4.5 w-4.5 text-destructive" />
                  )}
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-bold">
                    {tfidfLoaded ? (
                      <Badge variant="success" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 font-bold">Loaded</Badge>
                    ) : (
                      <Badge variant="destructive" className="bg-destructive/10 text-destructive border-destructive/20 font-bold">Unloaded</Badge>
                    )}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-2">
                    Lexical index (tfidf.pkl)
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-sm transition-all border-border bg-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Sentence Transformer
                  </CardTitle>
                  {modelLoaded ? (
                    <CheckCircle className="h-4.5 w-4.5 text-emerald-500" />
                  ) : (
                    <XCircle className="h-4.5 w-4.5 text-destructive" />
                  )}
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-bold">
                    {modelLoaded ? (
                      <Badge variant="success" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 font-bold">Active</Badge>
                    ) : (
                      <Badge variant="destructive" className="bg-destructive/10 text-destructive border-destructive/20 font-bold">Inactive</Badge>
                    )}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-2">
                    All MiniLM L6 v2 model
                  </p>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* SECTION 2: Recruiter Active Ranked Candidates Analytics (Only populates if rankings exist) */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-foreground">Active Ranked Candidates Metrics</h2>
        
        {rankingQuery.loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="h-28 rounded-xl border bg-card animate-pulse" />
            ))}
          </div>
        ) : showRankingsExist ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 animate-in fade-in duration-300">
            <Card className="hover:shadow-sm transition-all border-border bg-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Candidates Ranked
                </CardTitle>
                <Users className="h-4.5 w-4.5 text-indigo-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-extrabold text-foreground">{top100Count}</div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Active screened candidates
                </p>
              </CardContent>
            </Card>

            <Card className="hover:shadow-sm transition-all border-border bg-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Average AI Score
                </CardTitle>
                <TrendingUp className="h-4.5 w-4.5 text-indigo-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-extrabold text-indigo-500">{averageScore} <span className="text-xs font-semibold text-muted-foreground">pts</span></div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Mean candidate match compliance
                </p>
              </CardContent>
            </Card>

            <Card className="hover:shadow-sm transition-all border-border bg-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Highest AI Score
                </CardTitle>
                <Award className="h-4.5 w-4.5 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-extrabold text-emerald-500">{highestScore} <span className="text-xs font-semibold text-muted-foreground">pts</span></div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Rank #1 matched score
                </p>
              </CardContent>
            </Card>

            <Card className="hover:shadow-sm transition-all border-border bg-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Profile Screening Status
                </CardTitle>
                <ShieldCheck className="h-4.5 w-4.5 text-emerald-500" />
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="flex justify-between items-baseline">
                  <span className="text-sm font-bold text-emerald-500">{verifiedCount} Verified</span>
                  <span className="text-xs font-medium text-destructive">{flaggedCount} Flagged</span>
                </div>
                <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                  <div 
                    style={{ width: `${(verifiedCount / indexedCandidates) * 100}%` }} 
                    className="bg-emerald-500 h-full rounded-full" 
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="hover:shadow-sm transition-all border-border bg-card sm:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Last Screening Execution Time
                </CardTitle>
                <Clock className="h-4.5 w-4.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-bold text-foreground truncate">{lastRankingTime}</div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Successful screening process completion timestamp
                </p>
              </CardContent>
            </Card>

            <Card className="hover:shadow-sm transition-all border-border bg-card sm:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Screening Process Execution Runtime
                </CardTitle>
                <Cpu className="h-4.5 w-4.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-bold text-foreground">{pipelineRuntime}</div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Dual-retrieval and screening run time
                </p>
              </CardContent>
            </Card>
          </div>
        ) : (
          /* Recruiter-friendly Empty State for ranking metrics */
          <Card className="border-dashed py-12 text-center shadow-sm">
            <CardContent className="flex flex-col items-center justify-center gap-3.5 max-w-md mx-auto">
              <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">No Candidate Rankings Executed</h3>
                <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                  The AI candidate matching process has not been executed yet. Run a Job Description ranking to populate recruiter workspace analytics.
                </p>
              </div>
              <Link href="/rank">
                <Button size="sm" className="font-semibold gap-2">
                  Rank Job Description
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Index Status & Latest Ranking Block */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Index Details */}
        <Card className="lg:col-span-1 border-border">
          <CardHeader>
            <CardTitle className="text-sm">Core System Status</CardTitle>
            <CardDescription className="text-xs">Vector and database search states</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-xs font-medium text-muted-foreground">FAISS Vectors</span>
              <Badge variant={faissLoaded ? "success" : "destructive"} className="text-[10px] font-bold">
                {faissLoaded ? "Ready" : "Offline"}
              </Badge>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-xs font-medium text-muted-foreground">TF-IDF Vectorizer</span>
              <Badge variant={tfidfLoaded ? "success" : "destructive"} className="text-[10px] font-bold">
                {tfidfLoaded ? "Ready" : "Offline"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Model Hash</span>
              <span className="text-xs font-mono text-muted-foreground">minilm-l6-v2</span>
            </div>
          </CardContent>
        </Card>

        {/* Latest Run Preview */}
        <Card className="lg:col-span-2 border-border">
          <CardHeader>
            <CardTitle className="text-sm">Latest Ranked Candidates</CardTitle>
            <CardDescription className="text-xs">Metrics from the last executed job description search</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col justify-between min-h-[160px]">
            {rankingQuery.loading ? (
              <div className="flex items-center justify-center h-full">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : showRankingsExist ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-muted-foreground block">Candidates Ranked</span>
                    <span className="text-lg font-extrabold">{top100Count} candidates</span>
                  </div>
                  {topCandidate && (
                    <div>
                      <span className="text-xs text-muted-foreground block">Top Matched Candidate</span>
                      <Link
                        href={`/candidate/${topCandidate.candidate_id}`}
                        className="text-primary hover:underline font-bold text-sm font-mono"
                      >
                        {topCandidate.candidate_id} ({topCandidate.score.toFixed(2)} pts)
                      </Link>
                    </div>
                  )}
                </div>
                <div className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                  <span className="font-semibold text-foreground">Top Candidate Reason:</span>{" "}
                  {topCandidate?.reasoning}
                </div>
                <div>
                  <Link href="/rankings">
                    <Button size="sm" variant="outline" className="gap-2 text-xs border-primary/20 hover:border-primary/40">
                      <Search className="h-3.5 w-3.5" /> View All {top100Count} Rankings
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center h-full border border-dashed rounded-lg p-6">
                <FileText className="h-7 w-7 text-muted-foreground mb-2" />
                <p className="text-xs text-muted-foreground mb-3">No ranking runs found in system.</p>
                <Link href="/rank">
                  <Button size="sm" className="gap-2 text-xs">
                    Rank Job Description
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
