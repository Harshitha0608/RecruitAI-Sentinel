"use client";

import React, { useState, useEffect } from "react";
import { useApi } from "@/hooks/use-api";
import { useTheme } from "@/hooks/use-theme";
import { apiService, getBaseUrl, setBaseUrl } from "@/services/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Settings as SettingsIcon,
  Globe,
  Database,
  Cpu,
  RefreshCw,
  CheckCircle,
  XCircle,
  Palette,
  AlertTriangle
} from "lucide-react";

import { motion, AnimatePresence } from "framer-motion";

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState<string>("");
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [precomputeStatus, setPrecomputeStatus] = useState<{
    status: string;
    progress: number;
    message: string;
  } | null>(null);

  // Confirmation modal state
  const [showConfirm, setShowConfirm] = useState<boolean>(false);

  const healthQuery = useApi(apiService.getHealth, true);
  const precomputeQuery = useApi(apiService.precompute);

  useEffect(() => {
    setApiUrl(getBaseUrl());

    const fetchStatus = async () => {
      try {
        const res = await apiService.getPrecomputeStatus();
        setPrecomputeStatus(res);
      } catch (err) {
        console.error("Failed to fetch precompute status:", err);
      }
    };
    fetchStatus();
  }, []);

  // Poll precompute status when processing
  useEffect(() => {
    if (precomputeStatus?.status !== "processing") return;

    const interval = setInterval(async () => {
      try {
        const res = await apiService.getPrecomputeStatus();
        setPrecomputeStatus(res);
        if (res.status !== "processing") {
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Failed to poll precompute status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [precomputeStatus?.status]);

  const handleSaveApi = () => {
    setBaseUrl(apiUrl);
    setSaveSuccess(true);
    healthQuery.execute().catch(() => {});
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handlePrecomputeTrigger = async () => {
    setShowConfirm(false);
    try {
      setPrecomputeStatus({
        status: "processing",
        progress: 0,
        message: "Triggered background precomputation task...",
      });
      await precomputeQuery.execute();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-10 max-w-3xl mx-auto py-4 animate-in fade-in duration-500 relative">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-muted-foreground">
          Configure recruiter portal configurations, appearance options, and system diagnostics.
        </p>
      </div>

      {/* SECTION 1: Recruiter Preferences */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-foreground select-none">Recruiter Preferences</h2>
        
        {/* Appearance Mode */}
        <Card className="border border-border bg-card shadow-sm hover:shadow-md hover:border-primary/15 transition-all duration-300">
          <CardHeader>
            <CardTitle className="text-sm font-bold flex items-center gap-2">
              <Palette className="h-4.5 w-4.5 text-primary" /> Appearance Configuration
            </CardTitle>
            <CardDescription className="text-xs">
              Toggle theme configurations matching your environment view.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground select-none">Appearance Color Theme</span>
            <Button
              onClick={toggleTheme}
              variant="outline"
              className="text-xs border-primary/20 hover:border-primary/40 font-semibold px-4 py-1.5 h-auto transition-colors"
            >
              Switch to {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </Button>
          </CardContent>
        </Card>



        {/* Developer Tools */}
        <Card className="border border-border bg-card shadow-sm hover:shadow-md hover:border-primary/15 transition-all duration-300">
          <CardHeader>
            <CardTitle className="text-sm font-bold flex items-center gap-2 select-none">
              <SettingsIcon className="h-4.5 w-4.5 text-primary" /> Developer Tools
            </CardTitle>
            <CardDescription className="text-xs">
              Configure connections, monitor diagnostic health, and rebuild vector search indexes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-2">
            {/* 1. API Routing Configuration */}
            <div className="space-y-3 pb-5 border-b border-border/40">
              <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                <Globe className="h-4 w-4 text-muted-foreground" /> API Routing Configuration
              </h3>
              <p className="text-xs text-muted-foreground select-none">
                Modify the connection endpoint matching the RecruitAI-Sentinel backend server.
              </p>
              <div className="flex gap-4 pt-1">
                <Input
                  placeholder="http://127.0.0.1:8000"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="font-mono text-xs focus-visible:ring-primary focus-visible:ring-offset-0 border-border"
                />
                <Button onClick={handleSaveApi} className="font-semibold text-xs px-4 h-9">
                  Save Routing
                </Button>
              </div>
              {saveSuccess && (
                <p className="text-xs text-emerald-500 font-semibold mt-1">
                  API URL saved successfully! Re-polling connection...
                </p>
              )}
            </div>

            {/* 2. System Diagnostics */}
            <div className="space-y-3 pb-5 border-b border-border/40 text-xs">
              <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5 select-none">
                <Cpu className="h-4 w-4 text-muted-foreground" /> System Diagnostics
              </h3>
              <div className="flex justify-between items-center bg-muted/10 p-2.5 border rounded-lg border-border">
                <span className="text-muted-foreground select-none">Server Connection status</span>
                {healthQuery.loading ? (
                  <Badge variant="default" className="text-[10px] py-0.5 px-2">Checking...</Badge>
                ) : healthQuery.data?.status === "healthy" ? (
                  <Badge variant="success" className="gap-1 text-[10px] py-0.5 px-2 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-bold">
                    <CheckCircle className="h-3 w-3" /> Connection Healthy
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1 text-[10px] py-0.5 px-2 bg-destructive/10 text-destructive border border-destructive/20 font-bold animate-pulse">
                    <XCircle className="h-3 w-3" /> Offline
                  </Badge>
                )}
              </div>
            </div>

            {/* 3. Index Management */}
            <div className="space-y-3 pt-1">
              <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5 select-none">
                <Database className="h-4 w-4 text-muted-foreground" /> Index Management
              </h3>
              <p className="text-xs text-muted-foreground select-none">
                Re-calculate candidate embeddings and FAISS / TF-IDF indices.
              </p>
              <div className="flex flex-wrap items-center justify-between gap-4 p-4 border border-border rounded-xl bg-muted/5">
                <div>
                  <h4 className="text-xs font-bold text-foreground">Trigger System Index Rebuild</h4>
                  <p className="text-[10px] text-muted-foreground mt-0.5 max-w-sm">
                    Runs background processes to recalculate transformer vectors.
                  </p>
                </div>
                <Button
                  onClick={() => setShowConfirm(true)}
                  disabled={precomputeQuery.loading || precomputeStatus?.status === "processing"}
                  className="gap-2 font-semibold text-xs h-9 px-4 border-border"
                >
                  {precomputeQuery.loading || precomputeStatus?.status === "processing" ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Indexing...
                    </>
                  ) : (
                    <>
                      <Database className="h-3.5 w-3.5" /> Rebuild Search Index
                    </>
                  )}
                </Button>
              </div>

              {precomputeStatus && precomputeStatus.status !== "idle" && (
                <div className={`p-4 border rounded-xl space-y-3 animate-in fade-in duration-200 ${
                  precomputeStatus.status === "success" 
                    ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500" 
                    : precomputeStatus.status === "failed" 
                      ? "border-destructive/20 bg-destructive/5 text-destructive" 
                      : "border-primary/20 bg-primary/5 text-primary"
                }`}>
                  <div className="flex justify-between items-center text-xs font-bold">
                    <span>{precomputeStatus.message}</span>
                    <span>{precomputeStatus.progress}%</span>
                  </div>
                  {precomputeStatus.status === "processing" && (
                    <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                      <div 
                        style={{ width: `${precomputeStatus.progress}%` }} 
                        className="bg-primary h-full rounded-full transition-all duration-500" 
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Confirmation Modal */}
      <AnimatePresence>
        {showConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-sm select-none animate-in fade-in duration-200">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border w-full max-w-sm rounded-xl p-6 shadow-lg space-y-4 m-4"
            >
              <div className="flex items-center gap-3 text-amber-500">
                <AlertTriangle className="h-6 w-6 flex-shrink-0" />
                <h3 className="font-bold text-sm text-foreground">Confirm Rebuild Operation</h3>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Are you sure you want to rebuild the vector search indices? This is an expensive background operation that will rebuild FAISS and TF-IDF tables.
              </p>
              <div className="flex justify-end gap-2.5 pt-2">
                <Button variant="ghost" onClick={() => setShowConfirm(false)} className="text-xs font-semibold h-9 px-4">
                  Cancel
                </Button>
                <Button onClick={handlePrecomputeTrigger} className="text-xs font-semibold h-9 px-4">
                  Rebuild Index
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
