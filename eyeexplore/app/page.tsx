import Link from "next/link";
import { HeroViz } from "@/components/hero-viz";

const features = [
  {
    title: "Custom Data Upload",
    body: "Bring your own images, videos, and raw scanpath CSVs. EyeExplore maps X, Y, and Time columns automatically and flags schema issues before analysis.",
    tag: "Ingest",
  },
  {
    title: "Dynamic AOI Mapping",
    body: "Draw, import, or auto-propose areas of interest. Transition matrices and dwell-time summaries update as AOIs change.",
    tag: "AOI",
  },
  {
    title: "K-Coefficient Analysis",
    body: "Classify Focal vs. Ambient attention on a synced video timeline. Isolate exploration phases without leaving the stimulus.",
    tag: "Attention",
  },
  {
    title: "3D Scanpaths",
    body: "Lift 2D gaze into a depth-encoded 3D overlay. Compare participants in space, not just on a static heatmap.",
    tag: "Viz",
  },
];

const vizTypes = [
  { name: "Attention Maps", detail: "Gaussian heatmaps with perceptually ordered red–orange–yellow ramps." },
  { name: "Scanpath Overlays", detail: "Fixation bubbles and saccade vectors aligned to any stimulus." },
  { name: "Scarf Plots", detail: "AOI occupancy over time for multi-participant comparison." },
  { name: "Synced Video Player", detail: "Gaze, K-Coefficient, and stimulus playback on one clock." },
];

const stats = [
  { value: "X · Y · T", label: "Core schema" },
  { value: "I-VT", label: "Fixation filters" },
  { value: "3D", label: "Scanpath view" },
  { value: "K", label: "Focal / ambient" },
];

export default function HomePage() {
  return (
    <div className="bg-navy-950">
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-24 top-0 h-80 w-80 rounded-full bg-gaze/20 blur-3xl" />
          <div className="absolute right-0 top-24 h-96 w-96 rounded-full bg-heat-orange/15 blur-3xl" />
        </div>
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 pb-20 pt-14 sm:px-6 lg:grid-cols-2 lg:px-8 lg:pb-28 lg:pt-20">
          <div>
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium uppercase tracking-[0.14em] text-gaze">
              Visual eyetracking dashboard
            </p>
            <h1 className="font-serif text-4xl leading-[1.12] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
              Visualize Human Attention with EyeExplore
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-white/65 sm:text-lg">
              Upload stimuli and raw scanpaths. Generate attention maps, scanpath
              overlays, scarf plots, AOI transition matrices, and a synced video
              player that tracks Focal vs. Ambient phases — built for labs, UX
              teams, and cognitive science.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/dashboard-app/"
                target="_blank"
                rel="noopener noreferrer"
                className="heat-gradient inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-600/30 transition hover:brightness-110"
              >
                Launch Dashboard
              </Link>
              <Link
                href="/tutorials"
                className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                View Tutorials
              </Link>
            </div>
            <dl className="mt-12 grid grid-cols-2 gap-6 sm:grid-cols-4">
              {stats.map((s) => (
                <div key={s.label}>
                  <dt className="font-mono text-lg font-medium text-heat-yellow">{s.value}</dt>
                  <dd className="mt-1 text-xs uppercase tracking-wider text-white/40">{s.label}</dd>
                </div>
              ))}
            </dl>
          </div>
          <HeroViz />
        </div>
      </section>

      <section className="relative bg-ice pb-20 pt-16 text-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-heat-orange">Capabilities</p>
            <h2 className="mt-2 font-serif text-3xl text-navy-900 sm:text-4xl">
              From raw gaze to publication-ready figures
            </h2>
            <p className="mt-3 text-muted">
              The same pipeline researchers use for controlled experiments, and UX
              teams use for live product evaluation.
            </p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((f) => (
              <article
                key={f.title}
                className="group rounded-2xl border border-mist bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-heat-orange/40 hover:shadow-lg"
              >
                <span className="font-mono text-[11px] font-medium uppercase tracking-wider text-gaze">
                  {f.tag}
                </span>
                <h3 className="mt-3 text-lg font-semibold text-navy-900">{f.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{f.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white py-20">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-heat-orange">Visualizations</p>
            <h2 className="mt-2 font-serif text-3xl text-navy-900 sm:text-4xl">
              Every view your protocol needs
            </h2>
            <p className="mt-3 text-muted">
              Heatmaps for density, scanpaths for sequence, scarf plots for time,
              matrices for transitions, and 3D for spatial comparison.
            </p>
            <ul className="mt-8 space-y-4">
              {vizTypes.map((v) => (
                <li key={v.name} className="flex gap-3">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-heat-orange" />
                  <div>
                    <p className="font-semibold text-navy-900">{v.name}</p>
                    <p className="text-sm text-muted">{v.detail}</p>
                  </div>
                </li>
              ))}
            </ul>
            <Link
              href="/gallery"
              className="mt-8 inline-flex text-sm font-semibold text-navy-900 underline decoration-heat-orange decoration-2 underline-offset-4"
            >
              See use cases in the gallery →
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <VizCard title="Heatmap" type="heat" />
            <VizCard title="Scanpath" type="scan" className="mt-8" />
            <VizCard title="Scarf" type="scarf" />
            <VizCard title="AOI matrix" type="matrix" className="mt-8" />
          </div>
        </div>
      </section>

      <section className="bg-navy-900 py-16">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-4 sm:px-6 lg:flex-row lg:items-center lg:px-8">
          <div>
            <h2 className="font-serif text-3xl text-white">Ready to inspect a dataset?</h2>
            <p className="mt-2 max-w-xl text-white/60">
              Open the dashboard workspace, or start with sample reading and visual
              search tasks from the tutorials.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href="/dashboard-app/"
              target="_blank"
              rel="noopener noreferrer"
              className="heat-gradient rounded-full px-6 py-3 text-center text-sm font-semibold text-white"
            >
              Launch Dashboard
            </Link>
            <Link
              href="/docs"
              className="rounded-full border border-white/20 px-6 py-3 text-center text-sm font-semibold text-white"
            >
              Read the schema
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function VizCard({
  title,
  type,
  className = "",
}: {
  title: string;
  type: "heat" | "scan" | "scarf" | "matrix";
  className?: string;
}) {
  return (
    <div className={`overflow-hidden rounded-2xl border border-mist bg-navy-950 p-3 ${className}`}>
      <p className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wider text-white/40">{title}</p>
      {type === "heat" && (
        <div className="relative h-36 overflow-hidden rounded-xl bg-navy-800">
          <div className="absolute left-[30%] top-[28%] h-24 w-24 rounded-full bg-heat-red/80 blur-2xl" />
          <div className="absolute left-[48%] top-[40%] h-20 w-20 rounded-full bg-heat-orange/70 blur-xl" />
          <div className="absolute left-[22%] top-[50%] h-16 w-16 rounded-full bg-heat-yellow/50 blur-xl" />
        </div>
      )}
      {type === "scan" && (
        <svg viewBox="0 0 160 144" className="h-36 w-full rounded-xl bg-navy-800">
          <path d="M18 110 C 40 70, 55 40, 80 48 S 120 90, 142 32" fill="none" stroke="#94a3b8" strokeWidth="1.4" />
          {[ [18, 110], [55, 52], [80, 48], [110, 78], [142, 32] ].map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r="5" fill="#38bdf8" />
          ))}
        </svg>
      )}
      {type === "scarf" && (
        <div className="flex h-36 flex-col justify-center gap-2 rounded-xl bg-navy-800 p-3">
          {[
            [55, 25],
            [40, 35],
            [62, 18],
            [30, 40],
          ].map(([a, b], i) => (
            <div key={i} className="flex h-4 overflow-hidden rounded-full bg-white/10">
              <div className="h-full bg-heat-orange" style={{ width: `${a}%` }} />
              <div className="h-full bg-gaze" style={{ width: `${b}%` }} />
            </div>
          ))}
        </div>
      )}
      {type === "matrix" && (
        <div className="grid h-36 grid-cols-4 gap-1 rounded-xl bg-navy-800 p-3">
          {Array.from({ length: 16 }, (_, i) => (
            <div
              key={i}
              className="rounded-sm"
              style={{ background: `rgba(239,68,68,${0.15 + ((i * 17) % 70) / 100})` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
