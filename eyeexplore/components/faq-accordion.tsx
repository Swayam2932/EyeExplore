"use client";

import { useState } from "react";

const faqs = [
  {
    q: "What file formats can I upload?",
    a: "Stimuli: PNG, JPG, MP4, and WebM. Scanpaths: CSV or TSV with X, Y, and Time columns. See Docs for aliases and units.",
  },
  {
    q: "Do I need a specific eyetracker?",
    a: "No. EyeExplore is tracker-agnostic as long as you can export sample-level gaze. Tobii, EyeLink, GazePoint, and web-cam pipelines have all been used in the wild.",
  },
  {
    q: "How is the K-Coefficient computed?",
    a: "In a sliding window we compare local fixation duration vs. saccade amplitude. High K indicates Focal processing; low K indicates Ambient exploration. Window length is configurable.",
  },
  {
    q: "Can I self-host the Dash dashboard?",
    a: "Yes. Point the dashboard iframe at your Python/Dash process (typically port 8050) or reverse-proxy it behind the same origin.",
  },
  {
    q: "Where should I report bugs?",
    a: "Use the form on this page or open a GitHub Issue. Include a redacted CSV header row and the exact parse error when possible.",
  },
];

export function FaqAccordion() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <div className="divide-y divide-mist rounded-2xl border border-mist bg-white">
      {faqs.map((item, i) => {
        const isOpen = open === i;
        return (
          <div key={item.q}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : i)}
            >
              <span className="font-medium text-navy-900">{item.q}</span>
              <span className="text-xl text-muted">{isOpen ? "−" : "+"}</span>
            </button>
            {isOpen && <p className="px-5 pb-4 text-sm leading-6 text-muted">{item.a}</p>}
          </div>
        );
      })}
    </div>
  );
}
