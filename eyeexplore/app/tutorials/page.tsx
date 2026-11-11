import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Tutorials",
  description: "Get started with EyeExplore: walkthroughs and sample datasets.",
};

const steps = [
  {
    n: "01",
    title: "Prepare your files",
    body: "Export scanpaths as CSV with X, Y, and Time. Pair each file with the stimulus image or video used during recording.",
  },
  {
    n: "02",
    title: "Upload in the dashboard",
    body: "Launch the workspace, drop stimuli first, then scanpaths. Confirm column mapping if auto-detect is uncertain.",
  },
  {
    n: "03",
    title: "Tune filters",
    body: "Start with default I-VT thresholds. Inspect a few trials, then tighten minimum fixation duration if noise remains.",
  },
  {
    n: "04",
    title: "Map AOIs and export",
    body: "Draw areas of interest, review the transition matrix and scarf plot, then export figures for your paper or UX report.",
  },
];

const videos = [
  { title: "Five-minute orientation", length: "5:12", note: "Interface tour: upload, heatmap, scanpath overlay." },
  { title: "K-Coefficient on video", length: "8:40", note: "Focal vs. Ambient phases on a synced player." },
  { title: "AOIs from a UX audit", length: "11:05", note: "Website evaluation workflow with transition matrices." },
];

const datasets = [
  {
    name: "Reading Task Dataset",
    file: "/samples/reading-task.csv",
    detail: "Paragraph reading, 12 participants, 120 Hz remote tracker. Includes line-level AOI hints in comments.",
  },
  {
    name: "Visual Search Task Dataset",
    file: "/samples/visual-search.csv",
    detail: "Feature-conjunction search, 8 participants. Dense saccades; good for 3D scanpath demos.",
  },
];

export default function TutorialsPage() {
  return (
    <div className="bg-ice">
      <div className="border-b border-mist bg-navy-950 px-4 py-10 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gaze">Get started</p>
          <h1 className="mt-2 font-serif text-3xl sm:text-4xl">Tutorials</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/60">
            Interactive onboarding: a four-step path, video walkthroughs, and
            downloadable sample datasets.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <h2 className="font-serif text-2xl text-navy-900">Step-by-step</h2>
        <div className="mt-6 grid gap-5 sm:grid-cols-2">
          {steps.map((s) => (
            <article key={s.n} className="rounded-2xl border border-mist bg-white p-6 shadow-sm">
              <span className="font-mono text-sm text-heat-orange">{s.n}</span>
              <h3 className="mt-2 text-lg font-semibold text-navy-900">{s.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{s.body}</p>
            </article>
          ))}
        </div>

        <h2 className="mt-14 font-serif text-2xl text-navy-900">Video walkthroughs</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {videos.map((v) => (
            <article key={v.title} className="overflow-hidden rounded-2xl border border-mist bg-white shadow-sm">
              <div className="relative flex aspect-video items-center justify-center bg-navy-950">
                <div className="absolute inset-0 hero-grid opacity-50" />
                <button
                  type="button"
                  className="relative flex h-14 w-14 items-center justify-center rounded-full bg-white/95 text-navy-900 shadow-lg"
                  aria-label={`Play ${v.title} (placeholder)`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </button>
                <span className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 font-mono text-[11px] text-white">
                  {v.length}
                </span>
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-navy-900">{v.title}</h3>
                <p className="mt-1 text-sm text-muted">{v.note}</p>
              </div>
            </article>
          ))}
        </div>

        <h2 className="mt-14 font-serif text-2xl text-navy-900">Sample datasets</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Drop these CSVs into the dashboard with any matching stimulus to explore
          heatmaps and scanpaths without your own tracker export.
        </p>
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          {datasets.map((d) => (
            <article key={d.name} className="flex flex-col rounded-2xl border border-mist bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-navy-900">{d.name}</h3>
              <p className="mt-2 flex-1 text-sm leading-6 text-muted">{d.detail}</p>
              <a
                href={d.file}
                download
                className="heat-gradient mt-5 inline-flex w-fit items-center rounded-full px-4 py-2 text-sm font-semibold text-white"
              >
                Download CSV
              </a>
            </article>
          ))}
        </div>
        <p className="mt-8 text-sm text-muted">
          Next:{" "}
          <Link href="/dashboard-app/" target="_blank" rel="noopener noreferrer" className="font-semibold text-navy-900 underline decoration-heat-orange underline-offset-4">
            Launch Dashboard
          </Link>{" "}
          or review the{" "}
          <Link href="/docs" className="font-semibold text-navy-900 underline decoration-heat-orange underline-offset-4">
            data schema
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
