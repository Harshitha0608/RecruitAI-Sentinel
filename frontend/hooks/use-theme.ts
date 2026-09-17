"use client";

import { useState, useEffect, useCallback } from "react";

export type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "sentinel_theme";
const THEME_CHANGE_EVENT = "sentinel_theme_change";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>("dark");

  const applyThemeToDOM = useCallback((newTheme: Theme) => {
    setTheme(newTheme);
    if (typeof window !== "undefined") {
      const root = window.document.documentElement;
      if (newTheme === "light") {
        root.classList.remove("dark");
      } else {
        root.classList.add("dark");
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Read current theme from localStorage
    const saved = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    const initialTheme: Theme = saved === "light" ? "light" : "dark";
    applyThemeToDOM(initialTheme);

    const handleCustomEvent = (e: Event) => {
      const customEvent = e as CustomEvent<Theme>;
      if (customEvent.detail === "light" || customEvent.detail === "dark") {
        applyThemeToDOM(customEvent.detail);
      }
    };

    const handleStorageEvent = (e: StorageEvent) => {
      if (e.key === THEME_STORAGE_KEY && (e.newValue === "light" || e.newValue === "dark")) {
        applyThemeToDOM(e.newValue as Theme);
      }
    };

    window.addEventListener(THEME_CHANGE_EVENT, handleCustomEvent);
    window.addEventListener("storage", handleStorageEvent);

    return () => {
      window.removeEventListener(THEME_CHANGE_EVENT, handleCustomEvent);
      window.removeEventListener("storage", handleStorageEvent);
    };
  }, [applyThemeToDOM]);

  const toggleTheme = useCallback(() => {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";
    applyThemeToDOM(nextTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
      window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: nextTheme }));
    }
  }, [theme, applyThemeToDOM]);

  const setThemeExplicit = useCallback((newTheme: Theme) => {
    applyThemeToDOM(newTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
      window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: newTheme }));
    }
  }, [applyThemeToDOM]);

  return { theme, toggleTheme, setTheme: setThemeExplicit };
}
