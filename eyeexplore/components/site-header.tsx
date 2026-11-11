"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { navLinks } from "@/lib/site";
import { Logo } from "./logo";

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const onDark = pathname === "/";

  return (
    <header
      className={`sticky top-0 z-50 border-b ${
        onDark
          ? "border-white/10 bg-navy-950/80 text-white backdrop-blur-xl"
          : "border-mist bg-white/85 text-ink backdrop-blur-xl"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Logo invert={onDark} />

        <nav className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                  active
                    ? onDark
                      ? "bg-white/10 text-white"
                      : "bg-navy-900 text-white"
                    : onDark
                      ? "text-white/70 hover:bg-white/5 hover:text-white"
                      : "text-muted hover:bg-ice hover:text-navy-900"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <a
            href="/user-study/"
            target="_blank"
            rel="noopener noreferrer"
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
              onDark
                ? "border-white/20 text-white hover:bg-white/10"
                : "border-navy-900/15 text-navy-900 hover:bg-ice"
            }`}
          >
            Take User Study
          </a>
          <Link
            href="/dashboard-app/"
            target="_blank"
            rel="noopener noreferrer"
            className="heat-gradient rounded-full px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-orange-500/25 transition hover:brightness-110"
          >
            Launch Dashboard
          </Link>
        </div>

        <button
          type="button"
          className={`inline-flex h-10 w-10 items-center justify-center rounded-lg md:hidden ${onDark ? "text-white" : "text-navy-900"}`}
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? (
              <path d="M6 6l12 12M18 6L6 18" />
            ) : (
              <path d="M4 7h16M4 12h16M4 17h16" />
            )}
          </svg>
        </button>
      </div>

      {open && (
        <div
          className={`border-t px-4 py-4 md:hidden ${onDark ? "border-white/10 bg-navy-950" : "border-mist bg-white"}`}
        >
          <div className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={`rounded-lg px-3 py-2.5 text-sm font-medium ${onDark ? "text-white/80 hover:bg-white/5" : "text-ink hover:bg-ice"}`}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/dashboard-app/"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="heat-gradient mt-2 rounded-lg px-3 py-2.5 text-center text-sm font-semibold text-white"
            >
              Launch Dashboard
            </Link>
            <a
              href="/user-study/"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="mt-2 rounded-lg border border-current px-3 py-2.5 text-center text-sm font-semibold text-inherit"
            >
              Take User Study
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
