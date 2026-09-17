import type { Metadata } from "next";
import "./globals.css";
import { LayoutShell } from "@/components/layout-shell";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "RecruitAI Sentinel - Recruiter SaaS Portal",
  description: "Production-ready recruiter screening and risk scoring AI engine.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background font-sans antialiased text-foreground selection:bg-primary selection:text-primary-foreground">
        <Providers>
          <LayoutShell>{children}</LayoutShell>
        </Providers>
      </body>
    </html>
  );
}
