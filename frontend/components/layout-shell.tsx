"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { Navbar } from "./navbar";
import { Sidebar } from "./sidebar";

interface LayoutShellProps {
  children: React.ReactNode;
}

export function LayoutShell({ children }: LayoutShellProps) {
  const pathname = usePathname();
  
  // Experience 1: Landing / Welcome is active when pathname is '/'
  const isLandingMode = pathname === "/";

  // Sidebar permanent expansion state
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);

  const toggleSidebar = () => {
    setIsExpanded((prev) => !prev);
  };

  const toggleMobileOpen = () => {
    setIsMobileOpen((prev) => !prev);
  };

  const closeMobile = () => {
    setIsMobileOpen(false);
  };

  return (
    <div className="relative flex min-h-screen flex-col bg-background text-foreground transition-colors duration-300 premium-radial-bg grain-texture">
      {/* Top Navigation Bar */}
      <Navbar onMenuClick={toggleMobileOpen} isSimplified={isLandingMode} />

      <div className="flex flex-1 relative">
        {/* Render sidebar only in Workspace Experience (when not on landing route) */}
        {!isLandingMode && (
          <Sidebar
            isExpanded={isExpanded}
            onToggle={toggleSidebar}
            isMobileOpen={isMobileOpen}
            onCloseMobile={closeMobile}
          />
        )}

        {/* Backdrop for mobile overlays */}
        {!isLandingMode && isMobileOpen && (
          <div
            onClick={closeMobile}
            className="fixed inset-0 z-20 bg-slate-950/40 backdrop-blur-sm md:hidden transition-all duration-300"
          />
        )}

        {/* Main Content Workspace */}
        <main
          className={`flex-1 transition-all duration-300 ease-in-out min-h-[calc(100vh-4rem)] ${
            isLandingMode
              ? "pl-0 w-full"
              : isExpanded
              ? "md:pl-64"
              : "md:pl-16"
          }`}
        >
          <div className={`h-full w-full max-w-7xl mx-auto p-6 md:p-8 animate-in fade-in duration-300`}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
