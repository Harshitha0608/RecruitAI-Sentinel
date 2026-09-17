"use client";

import React, { useEffect } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initial theme set
    const savedTheme = localStorage.getItem("sentinel_theme");
    const root = window.document.documentElement;
    if (savedTheme === "light") {
      root.classList.remove("dark");
    } else {
      root.classList.add("dark");
      localStorage.setItem("sentinel_theme", "dark");
    }
  }, []);

  return <>{children}</>;
}

