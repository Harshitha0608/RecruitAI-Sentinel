"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Play,
  Users,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isExpanded: boolean;
  onToggle: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

const menuItems = [
  { name: "Welcome Portal", path: "/", icon: Home },
  { name: "AI Screening", path: "/rank", icon: Play },
  { name: "Candidates", path: "/rankings", icon: Users },
  { name: "Insights", path: "/analytics", icon: BarChart3 },
  { name: "Settings", path: "/settings", icon: Settings },
];

export function Sidebar({ isExpanded, onToggle, isMobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const [isHovered, setIsHovered] = useState<boolean>(false);

  // Helper to determine if link is active
  const isLinkActive = (path: string) => {
    if (path === "/") {
      return pathname === "/";
    }
    // Fix highlighting overlap bug between /rank and /rankings
    if (path === "/rank") {
      return pathname === "/rank";
    }
    if (path === "/rankings") {
      return pathname === "/rankings" || pathname?.startsWith("/candidate/");
    }
    return pathname?.startsWith(path);
  };

  // Determine if sidebar is currently in expanded layout state (either clicked or hovered)
  const isDisplayExpanded = isExpanded || isHovered;

  const sidebarContent = (
    <div className="flex flex-col h-full bg-card/65 backdrop-blur-md border-r border-border text-card-foreground select-none relative">
      {/* Brand Header */}
      <div className={cn(
        "flex items-center border-b border-border/50 h-16 transition-all duration-300",
        isDisplayExpanded ? "justify-start gap-3.5 px-[18px]" : "justify-center"
      )}>
        <ShieldCheck className="h-5 w-5 text-primary flex-shrink-0" />
        {isDisplayExpanded && (
          <div className="animate-in fade-in duration-300 select-none">
            <h2 className="font-extrabold tracking-tight text-xs text-foreground uppercase">RecruitAI-Sentinel</h2>
            <p className="text-[9px] text-muted-foreground font-bold tracking-wider">Candidate Screening</p>
          </div>
        )}
      </div>

      {/* Main Navigation Menu */}
      <nav className="flex-1 space-y-2 px-3 py-6 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = isLinkActive(item.path);

          return (
            <Link
              key={item.path}
              href={item.path}
              onClick={onCloseMobile}
              className={cn(
                "flex items-center rounded-lg h-10 px-3 transition-all duration-200 outline-none focus-visible:ring-1 focus-visible:ring-primary premium-btn-hover",
                isDisplayExpanded ? "justify-start" : "justify-center",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
              aria-label={item.name}
            >
              <Icon className="h-4.5 w-4.5 flex-shrink-0" />
              <span className={cn(
                "text-xs tracking-tight whitespace-nowrap transition-all duration-300 ease-in-out overflow-hidden",
                isDisplayExpanded ? "opacity-100 w-auto ml-3" : "opacity-0 w-0 ml-0"
              )}>
                {item.name}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Logo */}
      <div className={cn(
        "p-4 border-t border-border/50 flex items-center transition-all duration-300 bg-muted/5",
        isDisplayExpanded ? "justify-start gap-2" : "justify-center"
      )}>
        <ShieldCheck className="h-4 w-4 text-primary/80" />
        <span className={cn(
          "text-[10px] font-bold text-muted-foreground uppercase tracking-widest transition-all duration-300 overflow-hidden whitespace-nowrap",
          isDisplayExpanded ? "opacity-100 w-auto" : "opacity-0 w-0"
        )}>
          Sentinel v1.0
        </span>
      </div>

      {/* Collapse/Expand Toggle Button (Desktop only) */}
      <div className="hidden md:flex p-3 border-t border-border/50 bg-muted/10 justify-center">
        <button
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-all duration-200 outline-none focus-visible:ring-1 focus-visible:ring-primary"
          aria-label={isExpanded ? "Collapse Sidebar Menu" : "Expand Sidebar Menu"}
        >
          {isExpanded ? <ChevronLeft className="h-4.5 w-4.5" /> : <ChevronRight className="h-4.5 w-4.5" />}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Floating overlay expand mechanism) */}
      <aside
        onMouseEnter={() => !isExpanded && setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          "fixed left-0 top-16 z-30 hidden h-[calc(100vh-4rem)] border-r transition-all duration-300 ease-in-out md:block shadow-sm",
          isDisplayExpanded ? "w-64" : "w-16"
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer menu overlay */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-card h-full transition-transform duration-300 ease-in-out md:hidden shadow-lg",
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
