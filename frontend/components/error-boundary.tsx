"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Button } from "./ui/button";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-8 text-center bg-card rounded-xl border border-destructive/20 shadow-md">
          <div className="rounded-full bg-destructive/10 p-4 text-destructive mb-4">
            <AlertOctagon className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-foreground mb-2">
            Section Failed to Render
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6 leading-relaxed">
            {this.state.error?.message || "An unexpected error occurred while rendering this element."}
          </p>
          <Button onClick={this.handleReset} variant="outline" size="sm" className="gap-2">
            <RotateCcw className="h-4 w-4" /> Try Reloading Component
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
