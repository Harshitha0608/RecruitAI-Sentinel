"use client";

import React from "react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "./ui/button";

interface QueryLoaderProps {
  loading: boolean;
  error: string | null;
  retry?: () => void;
  loadingMessage?: string;
  children: React.ReactNode;
}

export function QueryLoader({
  loading,
  error,
  retry,
  loadingMessage = "Retrieving data from Core Engine...",
  children,
}: QueryLoaderProps) {
  if (loading) {
    return (
      <div className="flex min-h-[300px] w-full flex-col items-center justify-center p-8 text-center animate-in fade-in duration-300">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
        <p className="text-sm text-muted-foreground font-medium">{loadingMessage}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[300px] w-full flex-col items-center justify-center p-8 text-center border border-destructive/20 rounded-xl bg-destructive/5 animate-in fade-in duration-300">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <h3 className="text-lg font-bold text-foreground mb-1">Retrieval Failed</h3>
        <p className="text-sm text-muted-foreground max-w-md mb-6">{error}</p>
        {retry && (
          <Button onClick={retry} size="sm" variant="outline" className="gap-2">
            <RefreshCw className="h-3.5 w-3.5" /> Reconnect & Retry
          </Button>
        )}
      </div>
    );
  }

  return <>{children}</>;
}
