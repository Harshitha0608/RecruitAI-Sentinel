"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import { apiService } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { 
  ArrowRight, 
  ShieldCheck, 
  Sparkles, 
  Users, 
  FileText, 
  TrendingUp 
} from "lucide-react";

export default function WelcomePage() {
  const rankingQuery = useApi(apiService.getTop100, true);

  const candidates = rankingQuery.data?.candidates || [];
  const showResultsLink = candidates.length > 0 && rankingQuery.data?.success;

  return (
    <div className="space-y-16 max-w-5xl mx-auto py-12 animate-in fade-in duration-500">
      {/* Hero Welcome Section */}
      <section className="text-center space-y-6 py-12 max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3.5 py-1 text-xs font-semibold text-primary select-none">
          <Sparkles className="h-3.5 w-3.5" /> Explainable Candidate Screening & Ranking Platform
        </div>
        
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-foreground leading-tight">
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-indigo-400">
            RecruitAI-Sentinel
          </span>
        </h1>
        <p className="text-xl font-bold text-foreground/90 tracking-tight">
          AI Candidate Screening with Absolute Fidelity
        </p>
        
        <p className="text-base sm:text-lg text-muted-foreground leading-relaxed">
          RecruitAI-Sentinel evaluates candidate profiles against exact job requirements using hybrid retrieval and multi-dimensional scoring — providing explainable ranking evidence, skill-gap analysis, and timeline verification.
        </p>

        <div className="flex flex-wrap justify-center gap-4 pt-6 select-none">
          <Link href="/rank?new=true">
            <Button size="lg" className="gap-2 font-semibold shadow-md hover:shadow-lg premium-btn-hover h-11 px-6">
              Start AI Screening <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          {showResultsLink && (
            <Link href="/rankings">
              <Button size="lg" variant="outline" className="font-semibold border-border/80 hover:border-primary/40 premium-btn-hover h-11 px-6">
                View Previous Results
              </Button>
            </Link>
          )}
        </div>
      </section>

      {/* Recruiter Workflow Guide (FIX 1) */}
      <section className="space-y-8 animate-in fade-in slide-in-from-bottom duration-700 delay-100">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-foreground">Recruiter Screening Path</h2>
          <p className="text-xs text-muted-foreground">Follow this interactive roadmap to parse requirements, execute AI matching, and vet candidate pools.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 relative select-none">
          {[
            { step: "1", title: "Upload Requirements", desc: "Upload job description Word or text files to establish screening criteria." },
            { step: "2", title: "Verify Extracted Specs", desc: "Audit parsed Title, Experience, and core skills to ensure high-fidelity matching." },
            { step: "3", title: "Run Screen Engine", desc: "Execute automated candidate retrieval incorporating hybrid keyword and semantic models." },
            { step: "4", title: "Analyze Ranked Results", desc: "Vet candidates using unified scores, timeline fraud flags, and explanation reports." },
            { step: "5", title: "Export CSV & Stats", desc: "Download verified screening files and inspect aggregate insight distributions." }
          ].map((item, index) => (
            <div key={item.step} className="flex flex-col items-center text-center p-5 rounded-xl border border-border/80 bg-card/30 relative premium-card-hover group">
              <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary text-xs font-black mb-3.5 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                0{item.step}
              </div>
              <h4 className="font-bold text-xs text-foreground mb-1.5 uppercase tracking-wider">{item.title}</h4>
              <p className="text-[11px] text-muted-foreground/80 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Recruiter Feature Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-4">
        {/* Card 1: AI Candidate Screening */}
        <Card className="premium-card-hover border-border bg-card shadow-sm p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <Users className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-base text-foreground">AI Candidate Screening</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Extract capabilities dynamically from job requirements, rank the candidates using dual matching vectors, and build instant recruiter workflows.
          </p>
        </Card>

        {/* Card 2: Explainable Ranking */}
        <Card className="premium-card-hover border-border bg-card shadow-sm p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-base text-foreground">Explainable Screening</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Checks employment timelines and signal consistencies automatically to flag fraud risks and chronologically suspect candidate statements.
          </p>
        </Card>

        {/* Card 3: Recruiter Insights */}
        <Card className="premium-card-hover border-border bg-card shadow-sm p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-500">
            <FileText className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-base text-foreground">Recruiter Insights</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Clear, visual demographic summaries detailing match grade distribution, notice periods, and experience segments alongside processing speeds.
          </p>
        </Card>
      </section>
    </div>
  );
}
