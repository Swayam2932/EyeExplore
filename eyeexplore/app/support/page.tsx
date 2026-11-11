import type { Metadata } from "next";
import { FaqAccordion } from "@/components/faq-accordion";
import { SupportForm } from "@/components/support-form";
import { communityEmail, githubIssues } from "@/lib/site";

export const metadata: Metadata = {
  title: "Support",
  description: "Help, FAQ, and issue reporting for EyeExplore.",
};

export default function SupportPage() {
  return (
    <div className="bg-ice">
      <div className="border-b border-mist bg-navy-950 px-4 py-10 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gaze">Help & feedback</p>
          <h1 className="mt-2 font-serif text-3xl sm:text-4xl">Support</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/60">
            File a bug, browse the FAQ, or reach the research community.
          </p>
        </div>
      </div>
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 lg:grid-cols-2 sm:px-6 lg:px-8">
        <div>
          <h2 className="font-serif text-2xl text-navy-900">Submit an issue</h2>
          <p className="mt-2 text-sm text-muted">
            Prefer a tracker? Open a ticket on{" "}
            <a href={githubIssues} className="font-semibold text-navy-900 underline decoration-heat-orange underline-offset-4" target="_blank" rel="noreferrer">
              GitHub Issues
            </a>
            .
          </p>
          <div className="mt-6">
            <SupportForm />
          </div>
          <p className="mt-6 text-sm text-muted">
            Community contact:{" "}
            <a href={`mailto:${communityEmail}`} className="font-medium text-navy-900">
              {communityEmail}
            </a>
          </p>
        </div>
        <div>
          <h2 className="font-serif text-2xl text-navy-900">FAQ</h2>
          <p className="mt-2 mb-6 text-sm text-muted">Common questions from labs and UX teams.</p>
          <FaqAccordion />
        </div>
      </div>
    </div>
  );
}
