"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Workspace" },
  { href: "/sessions", label: "Sessions" },
  { href: "/experiments", label: "Experiments" },
] as const;

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader() {
  const pathname = usePathname() ?? "/";

  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="AI Code Evaluation Suite home">
        <span className="brand-mark" aria-hidden="true">
          AE
        </span>
        <span>AI Code Evaluation Suite</span>
      </Link>

      <nav className="site-nav" aria-label="Primary">
        {NAV_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            aria-current={isActive(pathname, link.href) ? "page" : undefined}
          >
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="header-note">
        <span className="live-dot" aria-hidden="true" />
        Local evaluator
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer>
      <span>Open source · Local first · No fabricated intelligence</span>
      <span>Evaluator MVP / 0.1</span>
    </footer>
  );
}
