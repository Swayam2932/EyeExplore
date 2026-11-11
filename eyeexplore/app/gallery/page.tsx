import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Gallery",
  description: "Real-world EyeExplore use cases: UX, cognitive psychology, and clinical gaze.",
};

const items = [
  {
    title: "E-commerce checkout UX",
    domain: "UX evaluation",
    blurb: "Heatmaps on a multi-step checkout. Attention clusters on the price row; the trust badge is almost never fixated.",
    type: "heat" as const,
    tall: true,
  },
  {
    title: "Visual search (T among L)",
    domain: "Cognitive psychology",
    blurb: "Classic conjunction search. Scanpaths show systematic left-to-right sweeps until target acquisition.",
    type: "scan" as const,
    tall: false,
  },
  {
    title: "Radiology chest X-ray",
    domain: "Clinical gaze",
    blurb: "Expert vs. novice dwell on lung fields. Focal K-Coefficient spikes at nodule candidates.",
    type: "heat" as const,
    tall: false,
  },
  {
    title: "News homepage AOIs",
    domain: "UX evaluation",
    blurb: "Transition matrix: hero image → headline → nav. Scarf plots reveal banner blindness after 4 s.",
    type: "matrix" as const,
    tall: true,
  },
  {
    title: "Reading comprehension",
    domain: "Cognitive psychology",
    blurb: "Regressive saccades on garden-path sentences. Line-level AOIs exported as scarf plots.",
    type: "scan" as const,
    tall: false,
  },
  {
    title: "Mobile onboarding video",
    domain: "Synced player",
    blurb: "Ambient exploration in the first 8 s, then focal lock on the CTA. K-Coefficient overlaid on the timeline.",
    type: "k" as const,
    tall: true,
  },
];

export default function GalleryPage() {
  return (
    <div className="bg-ice">
      <div className="border-b border-mist bg-navy-950 px-4 py-10 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gaze">Use cases</p>
          <h1 className="mt-2 font-serif text-3xl sm:text-4xl">Gallery</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/60">
            Benchmarks and application examples — UX audits, lab tasks, and
            clinical gaze patterns rendered as heatmaps and scanpaths.
          </p>
        </div>
      </div>
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="masonry">
          {items.map((item) => (
            <article key={item.title} className="masonry-item overflow-hidden rounded-2xl border border-mist bg-white shadow-sm">
              <Thumb type={item.type} tall={item.tall} />
              <div className="p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-heat-orange">{item.domain}</p>
                <h2 className="mt-1 text-lg font-semibold text-navy-900">{item.title}</h2>
                <p className="mt-2 text-sm leading-6 text-muted">{item.blurb}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function Thumb({ type, tall }: { type: "heat" | "scan" | "matrix" | "k"; tall: boolean }) {
  const h = tall ? "h-56" : "h-40";
  if (type === "heat") {
    return (
      <div className={`relative ${h} overflow-hidden bg-navy-900`}>
        <div className="absolute left-[22%] top-[18%] h-32 w-32 rounded-full bg-heat-red/80 blur-2xl" />
        <div className="absolute left-[48%] top-[36%] h-28 w-28 rounded-full bg-heat-orange/70 blur-2xl" />
        <div className="absolute left-[30%] top-[58%] h-20 w-24 rounded-full bg-heat-yellow/50 blur-xl" />
        <div className="absolute bottom-2 left-2 rounded bg-black/50 px-2 py-0.5 font-mono text-[10px] text-white/70">
          attention map
        </div>
      </div>
    );
  }
  if (type === "scan") {
    return (
      <svg viewBox="0 0 320 160" className={`${h} w-full bg-navy-900`}>
        <path d="M24 130 C 70 90, 90 40, 140 55 S 210 120, 290 36" fill="none" stroke="#cbd5e1" strokeWidth="1.5" />
        {[ [24, 130], [88, 62], [140, 55], [200, 98], [290, 36] ].map(([x, y], i) => (
          <g key={i}>
            <circle cx={x} cy={y} r={6 + i} fill="#38bdf8" opacity="0.9" />
          </g>
        ))}
      </svg>
    );
  }
  if (type === "matrix") {
    return (
      <div className={`${h} grid grid-cols-5 gap-1 bg-navy-900 p-4`}>
        {Array.from({ length: 25 }, (_, i) => (
          <div
            key={i}
            className="rounded-sm"
            style={{ background: `rgba(249,115,22,${0.12 + ((i * 13) % 80) / 100})` }}
          />
        ))}
      </div>
    );
  }
  return (
    <div className={`relative flex ${h} flex-col justify-end bg-navy-900 p-4`}>
      <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className="h-full w-2/3 heat-gradient" />
      </div>
      <p className="font-mono text-[10px] uppercase tracking-wider text-white/40">K-coefficient</p>
      <p className="text-sm font-semibold text-heat-yellow">Focal lock · 00:08.2</p>
    </div>
  );
}
