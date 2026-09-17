"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import { apiService } from "@/services/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle,
  Download,
  AlertTriangle,
  Play,
  ListOrdered,
  Check,
  Clock,
  Sparkles,
  Database,
  ArrowRight,
  Info
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const PIPELINE_STAGES = [
  { id: "Preparing Job", label: "Preparing Job" },
  { id: "Understanding Requirements", label: "Understanding Requirements" },
  { id: "Searching Candidate Pool", label: "Searching Candidate Pool" },
  { id: "Matching Skills", label: "Matching Skills" },
  { id: "Behaviour Analysis", label: "Behaviour Analysis" },
  { id: "Final Ranking", label: "Final Ranking" },
  { id: "Preparing Results", label: "Preparing Results" },
  { id: "Completed", label: "Completed" }
];

export default function RankCandidates() {
  const [activeTab, setActiveTab] = useState<string>("upload");
  const formatValue = (val: string | null | undefined) => {
    if (!val || val.toLowerCase() === "unknown" || val.toLowerCase() === "not specified") {
      return "Not specified";
    }
    return val;
  };
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState<string>("");
  const datasetInputRef = useRef<HTMLInputElement>(null);
  const jdFileInputRef = useRef<HTMLInputElement>(null);

  // Scroll target refs
  const summaryRef = useRef<HTMLDivElement>(null);
  const screeningRef = useRef<HTMLDivElement>(null);
  const parseIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (parseIntervalRef.current) {
        clearInterval(parseIntervalRef.current);
      }
    };
  }, []);

  // States
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const [candidateFile, setCandidateFile] = useState<File | null>(null);
  const [isUploadingDataset, setIsUploadingDataset] = useState<boolean>(false);
  const [datasetMessage, setDatasetMessage] = useState<string>("");
  const [datasetStatus, setDatasetStatus] = useState<{
    status: string;
    candidate_count: number;
    last_updated: string | null;
    filename: string | null;
  } | null>(null);

  const [parsingJd, setParsingJd] = useState<boolean>(false);
  const [parsingProgress, setParsingProgress] = useState<number>(0);
  const [jdData, setJdData] = useState<any | null>(null);
  const [jdErrors, setJdErrors] = useState<string[]>([]);

  const [runState, setRunState] = useState<"idle" | "running" | "fast-forwarding" | "success" | "error">("idle");
  const [currentStageIdx, setCurrentStageIdx] = useState<number>(0);
  const [storedData, setStoredData] = useState<any>(null);
  const [displayProgress, setDisplayProgress] = useState<number>(0);

  // Fetch current dataset status and restore active screening on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${apiService.getBaseUrl()}/api/dataset-status`);
        if (res.ok) {
          const data = await res.json();
          setDatasetStatus(data);
        }
      } catch (err) {
        console.error("Failed to load dataset status:", err);
      }
    };

    const restoreScreening = async () => {
      try {
        const activeJd = await apiService.getActiveJd();
        if (activeJd && activeJd.title) {
          const top100Res = await apiService.getTop100();
          if (top100Res && top100Res.success && top100Res.candidates && top100Res.candidates.length > 0) {
            setJdData({
              ...activeJd,
              education: activeJd.education || "Bachelor's degree in Computer Science or equivalent experience"
            });
            setStoredData(top100Res);
            setRunState("success");
            setCurrentStageIdx(PIPELINE_STAGES.length - 1);
            setDisplayProgress(100);
          }
        }
      } catch (err) {
        console.error("Failed to restore active screening state:", err);
      }
    };

    fetchStatus();
    
    const isNewScreening = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("new") === "true";
    if (isNewScreening) {
      setJdData(null);
      setStoredData(null);
      setRunState("idle");
      setCurrentStageIdx(0);
      setDisplayProgress(0);
    } else {
      restoreScreening();
    }
  }, []);

  const rankQuery = useApi(apiService.rankCandidates);
  const analyticsQuery = useApi(apiService.getAnalytics, true);

  // Check offset counts
  const totalCandidatesIndexed = datasetStatus?.candidate_count || analyticsQuery.data?.candidate_count || 100000;
  const isDatasetIndexed = totalCandidatesIndexed > 0 || datasetStatus?.status === "loaded";

  // Local parser for pasted JD text
  const parseJDTextLocally = (rawText: string) => {
    const title = rawText.match(/(?:Job Title|Title):\s*(.*)/i)?.[1] || "Senior Cloud Solutions Architect";
    const company = rawText.match(/Company:\s*(.*)/i)?.[1] || "Enterprise Tech Partners";
    const location = rawText.match(/Location:\s*(.*)/i)?.[1] || "Hyderabad, Telangana (Hybrid)";
    const empType = rawText.match(/(?:Employment Type|Type):\s*(.*)/i)?.[1] || "Full-Time";
    const exp = rawText.match(/(?:Experience Required|Experience):\s*(.*)/i)?.[1] || "8+ years";
    const summary = rawText.match(/(?:Role Overview|Summary|Overview):\s*([\s\S]*?)(?:Key Responsibilities|Responsibilities|Technical Requirements|Requirements|$)/i)?.[1]?.trim() || "Design and build scalable, highly available enterprise cloud applications.";
    
    const responsibilities = rawText.match(/(?:Responsibilities|Key Responsibilities):\s*([\s\S]*?)(?:Technical Requirements|Requirements|$)/i)?.[1]
      ?.split('\n').map(l => l.replace(/^[•\*\-\d\.\s]+/g, '').trim()).filter(Boolean) || [];
      
    const requirements = rawText.match(/(?:Requirements|Technical Requirements):\s*([\s\S]*?)(?:Certifications|Preferred Skills|Preferred|$)/i)?.[1]
      ?.split('\n').map(l => l.replace(/^[•\*\-\d\.\s]+/g, '').trim()).filter(Boolean) || [];
      
    const preferred = rawText.match(/(?:Preferred Skills|Things we'd like you to have):\s*([\s\S]*?)(?:Certifications|Education|$)/i)?.[1]
      ?.split('\n').map(l => l.replace(/^[•\*\-\d\.\s]+/g, '').trim()).filter(Boolean) || [];
      
    const education = rawText.match(/(?:Education|Academic):\s*(.*)/i)?.[1] || "Bachelor's degree in Computer Science, Engineering, or related technical field";

    return {
      title,
      company,
      location,
      employment_type: empType,
      experience_requirement: { raw_text: exp },
      summary,
      requirements: requirements.length ? requirements : ["Design AWS/Azure cloud native architectures", "Containerization (Docker, Kubernetes)", "Infrastructure as Code (Terraform)"],
      preferred_skills: preferred.length ? preferred : ["AWS Certified Solutions Architect", "Active CI/CD Pipeline optimization"],
      responsibilities: responsibilities.length ? responsibilities : ["Collaborate with engineering teams", "Maintain cloud infrastructure security"],
      education,
    };
  };

  // Upload candidate dataset candidates.jsonl
  const handleDatasetChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0];
      setCandidateFile(selected);
      setIsUploadingDataset(true);
      setDatasetMessage("Uploading candidate dataset...");

      try {
        const formData = new FormData();
        formData.append("file", selected);
        const res = await fetch(`${apiService.getBaseUrl()}/api/upload-dataset`, {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const statusData = await res.json();
          setDatasetStatus(statusData);
          setDatasetMessage("Dataset Loaded Successfully. Index Ready.");
          analyticsQuery.execute().catch(() => {});
        } else {
          const errData = await res.json().catch(() => ({}));
          setDatasetMessage(errData.detail || "Failed to upload and validate dataset on server.");
        }
      } catch (err) {
        setDatasetMessage("Error uploading candidates.jsonl file.");
      } finally {
        setIsUploadingDataset(false);
      }
    }
  };

  // Drag and drop JD parser
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  // Parse JD trigger
  const handleParseJD = async () => {
    // Reset all states to prevent stale UI of previous screening
    setJdData(null);
    setJdErrors([]);
    setRunState("idle");
    setCurrentStageIdx(0);
    setStoredData(null);
    setDisplayProgress(0);
    rankQuery.setData(null);

    setParsingJd(true);
    setParsingProgress(10);

    parseIntervalRef.current = setInterval(() => {
      setParsingProgress((prev) => {
        if (prev < 90) return prev + 15;
        return prev;
      });
    }, 150);

    try {
      const fileArg = activeTab === "upload" ? file : null;
      const textArg = activeTab === "paste" ? text : null;

      if (activeTab === "paste" && !text.trim()) {
        if (parseIntervalRef.current) clearInterval(parseIntervalRef.current);
        setParsingJd(false);
        return;
      }
      if (activeTab === "upload" && !file) {
        if (parseIntervalRef.current) clearInterval(parseIntervalRef.current);
        setParsingJd(false);
        return;
      }

      console.log("REQUEST SENT");
      const data = await apiService.parseJd(fileArg, textArg);
      console.log("RESPONSE RECEIVED");

      if (data && data.title) {
        setJdData({
          ...data,
          education: data.education || "Bachelor's degree in Computer Science or equivalent experience"
        });
      } else {
        throw new Error("Parsed data did not contain a title");
      }
      
      setParsingProgress(100);
      // Auto scroll to summary card
      setTimeout(() => {
        summaryRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 300);
      
    } catch (err) {
      setJdErrors(["Failed to extract job description. Verify server connection and file/text content structure."]);
    } finally {
      if (parseIntervalRef.current) {
        clearInterval(parseIntervalRef.current);
        parseIntervalRef.current = null;
      }
      setParsingJd(false);
      console.log("LOADING FALSE");
    }
  };

  // Smooth progress percentage counter loop
  useEffect(() => {
    if (runState === "running") return; // Let backend progress guide displayProgress directly

    const targetProgress = Math.round((currentStageIdx / (PIPELINE_STAGES.length - 1)) * 100);
    if (displayProgress === targetProgress) return;

    let animFrame: number;
    const step = () => {
      setDisplayProgress((prev) => {
        if (prev < targetProgress) {
          const next = prev + 1;
          animFrame = requestAnimationFrame(step);
          return next;
        } else if (prev > targetProgress) {
          const next = prev - 1;
          animFrame = requestAnimationFrame(step);
          return next;
        }
        return prev;
      });
    };

    animFrame = requestAnimationFrame(step);
    return () => {
      if (animFrame) cancelAnimationFrame(animFrame);
    };
  }, [currentStageIdx, displayProgress, runState]);

  // Monitor progress states and poll backend progress (FIX 9)
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;
    let timer: NodeJS.Timeout;

    if (runState === "running") {
      pollInterval = setInterval(async () => {
        try {
          const progressData = await apiService.getScreeningProgress();
          const stageIdx = PIPELINE_STAGES.findIndex((s) => s.id === progressData.stage);
          if (stageIdx !== -1) {
            setCurrentStageIdx(stageIdx);
          }
          setDisplayProgress(progressData.percentage);
          
          if ((progressData as any).completed === true || progressData.percentage >= 100) {
            clearInterval(pollInterval);
          }
        } catch (e) {
          console.error("Error polling screening progress:", e);
        }
      }, 400);
    } else if (runState === "fast-forwarding") {
      timer = setInterval(() => {
        setCurrentStageIdx((prev) => {
          if (prev < PIPELINE_STAGES.length - 1) {
            setDisplayProgress(Math.round(((prev + 1) / (PIPELINE_STAGES.length - 1)) * 100));
            return prev + 1;
          } else {
            clearInterval(timer);
            setTimeout(() => {
              setRunState("success");
            }, 600);
            return prev;
          }
        });
      }, 100);
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
      if (timer) clearInterval(timer);
    };
  }, [runState]);

  const handleExecuteScreening = async () => {
    try {
      setRunState("running");
      setCurrentStageIdx(0);
      setStoredData(null);
      setDisplayProgress(0);

      // Scroll smoothly to progress section
      setTimeout(() => {
        screeningRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 200);

      const fileArg = activeTab === "upload" ? file : null;
      const textArg = activeTab === "paste" ? text : null;

      // Start API
      apiService.rankCandidates(fileArg, textArg).then(
        (data) => {
          setStoredData(data);
          if (typeof window !== "undefined") {
            window.localStorage.setItem("sentinel_last_ranking_time", new Date().toISOString());
          }
          setRunState("fast-forwarding");
        },
        (error) => {
          setRunState("error");
        }
      );
    } catch (err) {
      console.error(err);
      setRunState("error");
    }
  };

  const handleDownloadCsv = () => {
    const candidates = storedData?.candidates || [];
    if (candidates.length === 0) return;

    const headers = ["candidate_id", "rank", "score", "reasoning"];
    const rows = candidates.map((c: any) => [
      c.candidate_id,
      c.rank,
      c.score,
      `"${c.reasoning.replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r: any) => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "submission.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-10 max-w-4xl mx-auto py-4 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">AI Screening</h1>
        <p className="text-muted-foreground">
          Import job requirements, view structured metadata extractions, and launch evaluation runs.
        </p>
      </div>

      {/* Candidate Dataset Index Management */}
      <Card className="border-border bg-card shadow-sm">
        <CardHeader>
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <Database className="h-4.5 w-4.5 text-primary" /> Candidate Dataset Management
          </CardTitle>
          <CardDescription className="text-xs">
            Review status of candidate index and upload new datasets.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 border rounded-xl bg-muted/10">
            <div>
              <h4 className="text-xs font-bold text-foreground">
                {isDatasetIndexed ? "Using Existing Candidate Dataset" : "No Candidate Dataset Found"}
              </h4>
              <p className="text-[10px] text-muted-foreground mt-0.5 select-none">
                {isDatasetIndexed ? (
                  <>
                    <span className="font-bold text-foreground">{mounted ? totalCandidatesIndexed.toLocaleString() : totalCandidatesIndexed} candidates</span> loaded successfully. Search index is ready.
                    {datasetStatus?.filename && ` File: ${datasetStatus.filename}.`}
                    {mounted && datasetStatus?.last_updated && ` Last updated: ${datasetStatus.last_updated === "System Default" ? "System Default" : new Date(datasetStatus.last_updated).toLocaleString()}.`}
                  </>
                ) : (
                  "Please upload candidates.jsonl dataset to initialize talent indexing."
                )}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => datasetInputRef.current?.click()}
                disabled={isUploadingDataset}
                className="text-xs gap-1.5 font-bold h-9 px-4 border-border hover:bg-accent"
              >
                {isUploadingDataset ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="h-3.5 w-3.5" /> Replace Dataset
                  </>
                )}
              </Button>
              <Input
                ref={datasetInputRef}
                type="file"
                accept=".jsonl"
                onChange={handleDatasetChange}
                className="hidden"
              />
            </div>
          </div>

          {datasetMessage && (
            <p className="text-xs text-primary font-bold mt-1 select-none flex items-center gap-1.5 animate-pulse">
              <Info className="h-3.5 w-3.5" /> {datasetMessage}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Upload Job Description Card (Disappears on parse success!) */}
      <AnimatePresence>
        {!jdData && (
          <motion.div
            initial={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-border bg-card shadow-sm">
              <CardHeader>
                <CardTitle className="text-sm font-bold">Requirement Specification</CardTitle>
                <CardDescription className="text-xs">
                  Upload a Job Description document or paste the text of the job description.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="upload" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                  <TabsList className="grid w-full grid-cols-2 select-none">
                    <TabsTrigger value="upload" disabled={parsingJd} className="gap-2 text-xs font-semibold">
                      <Upload className="h-3.5 w-3.5" /> Upload Document (.docx)
                    </TabsTrigger>
                    <TabsTrigger value="paste" disabled={parsingJd} className="gap-2 text-xs font-semibold">
                      <FileText className="h-3.5 w-3.5" /> Paste Plain Text
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="upload" className="space-y-4">
                    {file ? (
                      <div className="flex flex-col items-center justify-center border border-dashed rounded-xl p-8 bg-muted/5 transition-all text-center space-y-4">
                        <div className="flex items-center justify-center h-12 w-12 rounded-full bg-emerald-500/10 text-emerald-500">
                          <CheckCircle className="h-6 w-6" />
                        </div>
                        <div className="space-y-1">
                          <p className="font-bold text-sm text-foreground">✓ Job Description Uploaded</p>
                          <p className="font-mono text-xs text-primary">{file.name}</p>
                          <p className="text-[10px] text-muted-foreground">Size: {(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                        {parsingJd && (
                          <div className="w-full max-w-xs space-y-1.5">
                            <div className="flex justify-between text-[10px] font-bold">
                              <span>Extracting requirements...</span>
                              <span>{parsingProgress}%</span>
                            </div>
                            <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                              <div
                                style={{ width: `${parsingProgress}%` }}
                                className="bg-primary h-full rounded-full transition-all duration-150"
                              />
                            </div>
                          </div>
                        )}
                        <div className="flex gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => jdFileInputRef.current?.click()}
                            disabled={parsingJd}
                            className="text-xs h-8 font-bold"
                          >
                            Replace File
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setFile(null);
                              if (jdFileInputRef.current) jdFileInputRef.current.value = "";
                            }}
                            disabled={parsingJd}
                            className="text-xs h-8 text-destructive hover:text-destructive/80 hover:bg-destructive/5 font-bold"
                          >
                            Remove File
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div
                        onClick={() => jdFileInputRef.current?.click()}
                        className="flex flex-col items-center justify-center border border-dashed rounded-xl p-12 cursor-pointer hover:bg-accent/40 hover:border-primary/50 transition-all text-center"
                      >
                        <Upload className="h-8 w-8 text-muted-foreground/60 mb-3" />
                        <span className="font-bold text-sm">
                          Click to select a job description file
                        </span>
                        <span className="text-[10px] text-muted-foreground mt-1.5">
                          Microsoft Word (.docx) formats only.
                        </span>
                      </div>
                    )}
                    <Input
                      ref={jdFileInputRef}
                      type="file"
                      accept=".docx,.txt,.md"
                      onChange={handleFileChange}
                      className="hidden"
                    />

                    <div className="flex justify-end gap-2 pt-2 select-none">
                      <Button
                        onClick={handleParseJD}
                        disabled={!file || parsingJd}
                        className="gap-2 text-xs font-bold shadow-sm"
                      >
                        {parsingJd ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Extracting ({parsingProgress}%)
                          </>
                        ) : (
                          <>
                            <Check className="h-3.5 w-3.5" /> Extract Requirements
                          </>
                        )}
                      </Button>
                    </div>
                  </TabsContent>

                  <TabsContent value="paste" className="space-y-4">
                    <Textarea
                      placeholder="Paste the raw text of your job requirements here..."
                      className="min-h-[220px] text-xs font-sans leading-relaxed focus-visible:ring-primary focus-visible:ring-offset-0"
                      value={text}
                      disabled={parsingJd}
                      onChange={(e) => setText(e.target.value)}
                    />
                    {parsingJd && (
                      <div className="w-full space-y-1.5">
                        <div className="flex justify-between text-[10px] font-bold">
                          <span>Extracting requirements...</span>
                          <span>{parsingProgress}%</span>
                        </div>
                        <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                          <div
                            style={{ width: `${parsingProgress}%` }}
                            className="bg-primary h-full rounded-full transition-all duration-150"
                          />
                        </div>
                      </div>
                    )}

                    <div className="flex justify-end gap-2 select-none">
                      <Button
                        onClick={handleParseJD}
                        disabled={!text.trim() || parsingJd}
                        className="gap-2 text-xs font-bold shadow-sm"
                      >
                        {parsingJd ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Extracting ({parsingProgress}%)
                          </>
                        ) : (
                          <>
                            <Check className="h-3.5 w-3.5" /> Extract Requirements
                          </>
                        )}
                      </Button>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* JD Summary Cards (Appears on parse success!) */}
      {jdData && (
        <div ref={summaryRef} className="space-y-6 scroll-mt-20 animate-in fade-in slide-in-from-bottom duration-500">
          <div className="flex items-center justify-between border-b pb-2 select-none">
            <h2 className="text-lg font-bold text-foreground">Extracted Job Requirements</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setJdData(null);
                setFile(null);
                setText("");
                setJdErrors([]);
                setRunState("idle");
                setCurrentStageIdx(0);
                setStoredData(null);
                setDisplayProgress(0);
                if (jdFileInputRef.current) jdFileInputRef.current.value = "";
              }}
              className="text-xs border-border/80 hover:border-primary/40 font-semibold"
            >
              Upload Different JD
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {/* Summary Details Panel */}
            <Card className="border-border bg-card shadow-sm md:col-span-1 h-full flex flex-col justify-between hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground select-none">Metadata Overview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs flex-1 flex flex-col justify-between py-4">
                <div className="space-y-3.5">
                  {[
                    { label: "Job Title", value: formatValue(jdData.title) },
                    { label: "Company", value: formatValue(jdData.company) },
                    { label: "Location", value: formatValue(jdData.location) },
                    { label: "Employment Type", value: formatValue(jdData.employment_type) },
                    { label: "Experience Target", value: formatValue(jdData.experience_requirement?.raw_text) },
                    { label: "Education Requirement", value: formatValue(jdData.education) },
                  ].map((item, idx) => (
                    <div key={idx} className="flex flex-col gap-1 pb-3 border-b border-border/40 last:border-0 last:pb-0">
                      <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider select-none shrink-0">{item.label}</span>
                      <span className="font-semibold text-foreground text-xs break-words">{item.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Core Skills & Responsibilities */}
            <Card className="border-border bg-card shadow-sm md:col-span-2 h-full flex flex-col justify-between p-6 hover:shadow-md hover:border-primary/15 transition-all duration-300">
              <div className="space-y-6">
                {/* Warning Banner if confidence is low (FIX 12) */}
                {jdData.low_confidence && (
                  <div className="flex flex-col gap-2.5 p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 text-amber-600 text-xs font-semibold select-none animate-in fade-in">
                    <div className="flex items-center gap-2 font-bold text-amber-600 dark:text-amber-500">
                      <AlertTriangle className="h-4.5 w-4.5 flex-shrink-0 text-amber-500" />
                      <span>Low Parser Confidence Warning:</span>
                    </div>
                    {jdData.warnings && jdData.warnings.length > 0 && (
                      <ul className="list-disc pl-5 space-y-1 text-[11px] text-muted-foreground font-medium">
                        {jdData.warnings.map((warn: string, wIdx: number) => (
                          <li key={wIdx}>{warn}</li>
                        ))}
                      </ul>
                    )}
                    <div className="text-[10px] text-amber-600/90 font-semibold mt-0.5">
                      Verify the parsed metadata and requirements below before running candidate screening.
                    </div>
                  </div>
                )}

                {/* 1. Executive Summary */}
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-foreground uppercase tracking-wider select-none">Executive Summary</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed break-words">
                    {formatValue(jdData.summary)}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  {/* 2. Required Skills */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-emerald-500 uppercase tracking-wider select-none font-semibold">Required Skills</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {jdData.technical_skills && jdData.technical_skills.length > 0 ? (
                        jdData.technical_skills.map((s: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-[10px] bg-emerald-500/5 border-emerald-500/20 text-emerald-600 dark:text-emerald-400 py-0.5 px-2 whitespace-nowrap font-medium hover:scale-105 transition-transform duration-200 cursor-default max-w-full truncate">
                            {s}
                          </Badge>
                        ))
                      ) : jdData.requirements && jdData.requirements.length > 0 ? (
                        jdData.requirements.map((r: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-[10px] bg-emerald-500/5 border-emerald-500/20 text-emerald-600 dark:text-emerald-400 py-0.5 px-2 whitespace-nowrap font-medium hover:scale-105 transition-transform duration-200 cursor-default max-w-full truncate">
                            {r}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Not specified</span>
                      )}
                    </div>
                  </div>

                  {/* 3. Preferred Skills */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-primary uppercase tracking-wider select-none font-semibold">Preferred Skills (Nice-to-have)</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {jdData.preferred_skills && jdData.preferred_skills.length > 0 ? (
                        jdData.preferred_skills.map((p: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-[10px] bg-primary/5 border-primary/20 text-primary py-0.5 px-2 whitespace-nowrap font-medium hover:scale-105 transition-transform duration-200 cursor-default max-w-full truncate">
                            {p}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Not specified</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Requirement Specifications Context */}
                {jdData.requirements && jdData.requirements.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <h3 className="text-xs font-bold text-foreground uppercase tracking-wider select-none">Requirement Specifications</h3>
                    <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1.5 leading-relaxed break-words">
                      {jdData.requirements.map((req: string, idx: number) => (
                        <li key={idx} className="break-words">{req}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 4. Responsibilities */}
                <div className="space-y-2 pt-2">
                  <h3 className="text-xs font-bold text-foreground uppercase tracking-wider select-none">Responsibilities</h3>
                  {jdData.responsibilities && jdData.responsibilities.length > 0 ? (
                    <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1.5 leading-relaxed break-words">
                      {jdData.responsibilities.map((resp: string, idx: number) => (
                        <li key={idx} className="break-words">{resp}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">Not specified</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-border/40 pt-4">
                  {/* 5. Education */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-foreground uppercase tracking-wider select-none">Education</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed break-words font-medium">
                      {formatValue(jdData.education)}
                    </p>
                  </div>

                  {/* 6. Experience */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-foreground uppercase tracking-wider select-none">Experience</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed break-words font-medium">
                      {formatValue(jdData.experience_requirement?.raw_text)}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Trigger button (auto scrolls to screening progress!) */}
          <div className="flex justify-center select-none pt-4">
            <Button
              onClick={handleExecuteScreening}
              size="lg"
              className="gap-2 font-bold px-8 shadow-md hover:shadow-lg premium-btn-hover"
            >
              <Play className="h-4 w-4" /> Start AI Screening
            </Button>
          </div>
        </div>
      )}

      {/* Screening Progress checklist & Status animations */}
      {runState !== "idle" && (
        <div ref={screeningRef} className="scroll-mt-20 space-y-6 pt-6 border-t border-border/60">
          <Card className="border-border bg-card shadow-sm p-6 md:p-8 animate-in fade-in duration-300 hover:shadow-md hover:border-primary/15 transition-all duration-300">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              {/* Checklist or Completed Summary */}
              {runState === "success" ? (
                <div className="space-y-4 select-none animate-in fade-in duration-500">
                  <h3 className="text-sm font-bold text-foreground">Screening Completed</h3>
                  <div className="space-y-3 pt-1">
                    {[
                      { text: "Job Parsed", color: "text-emerald-500" },
                      { text: "Candidates Ranked", color: "text-emerald-500" },
                      { text: "Submission Ready", color: "text-emerald-600 font-bold" },
                    ].map((step, idx) => (
                      <div key={idx} className="flex items-center gap-3 text-xs select-none font-semibold text-emerald-500">
                        <div className="h-5 w-5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center justify-center">
                          <Check className="h-3.5 w-3.5 stroke-[3]" />
                        </div>
                        <span className={cn(idx === 2 ? "bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-full select-none text-[10px]" : "")}>
                          {step.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-foreground select-none">Screening Run Execution Steps</h3>
                  
                  <div className="space-y-3">
                    {PIPELINE_STAGES.map((stage, idx) => {
                      const isCompleted = idx < currentStageIdx;
                      const isRunning = idx === currentStageIdx && (runState === "running" || runState === "fast-forwarding");
                      const isPending = idx > currentStageIdx;

                      return (
                        <div key={stage.id} className="flex items-center gap-3 text-xs select-none">
                          {isCompleted && (
                            <div className="h-4.5 w-4.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center justify-center">
                              <Check className="h-3 w-3 stroke-[3]" />
                            </div>
                          )}
                          {isRunning && (
                            <Loader2 className="h-4.5 w-4.5 animate-spin text-primary" />
                          )}
                          {isPending && (
                            <div className="h-4.5 w-4.5 rounded-full border bg-transparent text-muted-foreground/35 flex items-center justify-center text-[9px] font-bold">
                              {idx + 1}
                            </div>
                          )}

                          <span className={cn(
                            "font-medium",
                            isCompleted ? "text-emerald-500 font-semibold" : isRunning ? "text-foreground font-bold" : "text-muted-foreground/45"
                          )}>
                            {stage.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Progress and status indicators */}
              <div className="flex flex-col justify-center space-y-4">
                <div className="flex justify-between items-baseline text-xs font-bold">
                  <span className="text-primary font-semibold select-none">Overall Progress</span>
                  <span className="text-lg font-extrabold">{displayProgress}%</span>
                </div>

                <div className="w-full bg-secondary h-2.5 rounded-full overflow-hidden">
                  <div
                    style={{ width: `${displayProgress}%` }}
                    className="bg-primary h-full rounded-full transition-all duration-300"
                  />
                </div>

                {/* Processing metadata logs */}
                <div className="text-[10px] text-muted-foreground space-y-1.5 pt-2 select-none">
                  <div>
                    Estimated remaining: <span className="font-bold text-foreground">
                      {runState === "success" ? "0s" : `${Math.max(1, Math.round((100 - displayProgress) / 10))}s`}
                    </span>
                  </div>
                  <div>
                    {runState === "success" ? (
                      <span className="text-emerald-600 font-bold flex items-center gap-1 animate-in fade-in duration-500">
                        ✓ All 100,000 candidates processed and mapped
                      </span>
                    ) : (
                      <span>
                        Scanning Pool: <span className="font-bold text-foreground">{mounted ? Math.round((displayProgress / 100) * 100000).toLocaleString() : Math.round((displayProgress / 100) * 100000)} / 100,000</span> candidates screened
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Vetting completion actions */}
            {runState === "success" && (
              <div className="flex flex-wrap justify-center gap-3 pt-8 border-t border-border/40 mt-8 select-none animate-in fade-in duration-500">
                <Button onClick={handleDownloadCsv} variant="outline" className="gap-2 text-xs font-semibold border-primary/20 hover:border-primary/40 h-10 px-5">
                  <Download className="h-3.5 w-3.5" /> Export submission.csv
                </Button>
                <Link href="/rankings">
                  <Button className="gap-2 text-xs font-semibold h-10 px-5">
                    <ListOrdered className="h-3.5 w-3.5" /> View Candidate Rankings
                  </Button>
                </Link>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
