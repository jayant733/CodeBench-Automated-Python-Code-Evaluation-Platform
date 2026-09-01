import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SiteFooter, SiteHeader } from "../components/site-chrome";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Code Evaluation Suite",
  description:
    "Run Python submissions in isolation and inspect deterministic, test-level evaluation reports.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SiteHeader />
        <main>{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
