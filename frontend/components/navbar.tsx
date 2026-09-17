"use client";

import React, { useEffect, useState } from "react";
import { Moon, Sun, ShieldCheck, Menu, Wifi, WifiOff } from "lucide-react";
import { apiService } from "@/services/api";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/hooks/use-theme";

interface NavbarProps {
  onMenuClick?: () => void;
  isSimplified?: boolean;
}

export function Navbar({ onMenuClick, isSimplified = false }: NavbarProps) {
  const { theme, toggleTheme } = useTheme();
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    if (isSimplified) return;

    // Health check polling
    const checkHealth = async () => {
      try {
        const res = await apiService.getHealth();
        setIsOnline(res.status === "healthy");
      } catch {
        setIsOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [isSimplified]);

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border bg-background/80 backdrop-blur-md px-6 shadow-sm select-none">
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger toggle (Hidden in simplified mode) */}
        {!isSimplified && (
          <button
            onClick={onMenuClick}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden transition-colors outline-none focus-visible:ring-1 focus-visible:ring-primary"
            aria-label="Toggle Navigation Drawer"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <span className="text-sm font-extrabold tracking-tight text-foreground sm:inline-block">
            RecruitAI-Sentinel
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Connection status badge (Hidden in simplified mode) */}
        {!isSimplified && (
          <div className="flex items-center">
            {isOnline === null ? (
              <Badge variant="outline" className="text-[10px] py-0 px-2 font-medium bg-background text-muted-foreground border-border">Connecting...</Badge>
            ) : isOnline ? (
              <Badge variant="success" className="text-[10px] py-0.5 px-2 flex items-center gap-1 font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                <Wifi className="h-2.5 w-2.5" /> Engine Connected
              </Badge>
            ) : (
              <Badge variant="destructive" className="text-[10px] py-0.5 px-2 flex items-center gap-1 font-bold bg-destructive/10 text-destructive border border-destructive/20 animate-pulse">
                <WifiOff className="h-2.5 w-2.5" /> Offline
              </Badge>
            )}
          </div>
        )}

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors duration-200 outline-none focus-visible:ring-1 focus-visible:ring-primary"
          aria-label="Toggle Theme"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-slate-700" />
          )}
        </button>
      </div>
    </header>
  );
}
