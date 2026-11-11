import Link from "next/link";
import { communityEmail, githubIssues, navLinks } from "@/lib/site";
import { Logo } from "./logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10 bg-navy-950 text-white">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-4 lg:px-8">
        <div className="md:col-span-2">
          <Logo invert />
          <p className="mt-4 max-w-sm text-sm leading-6 text-white/60">
            Advanced visual eyetracking dashboards for researchers, UX designers,
            and cognitive psychologists. Upload stimuli and scanpaths. See
            attention.
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/40">
            Product
          </p>
          <ul className="mt-4 space-y-2.5">
            {navLinks.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-sm text-white/70 hover:text-white">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/40">
            Community
          </p>
          <ul className="mt-4 space-y-2.5 text-sm text-white/70">
            <li>
              <a href={githubIssues} className="hover:text-white" target="_blank" rel="noreferrer">
                GitHub Issues
              </a>
            </li>
            <li>
              <a href={`mailto:${communityEmail}`} className="hover:text-white">
                {communityEmail}
              </a>
            </li>
            <li>
              <Link href="/docs" className="hover:text-white">
                Data schema
              </Link>
            </li>
            <li>
              <Link href="/tutorials" className="hover:text-white">
                Sample datasets
              </Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-3 px-4 py-5 text-xs text-white/40 sm:flex-row sm:items-center sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} EyeExplore. Built for attention science.</p>
          <p>Heatmaps · Scanpaths · Scarf plots · K-Coefficient</p>
        </div>
      </div>
    </footer>
  );
}
