export function HeroViz() {
  return (
    <div className="relative mx-auto aspect-[4/3] w-full max-w-xl">
      <div className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-gaze/20 via-heat-orange/10 to-heat-red/20 blur-2xl" />
      <div className="relative h-full overflow-hidden rounded-[1.6rem] border border-white/15 bg-navy-900/80 shadow-2xl shadow-black/40">
        <div className="hero-grid absolute inset-0 opacity-70" />
        <div className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-white/70">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-heat-orange" />
          Live attention map
        </div>
        <svg viewBox="0 0 480 360" className="absolute inset-0 h-full w-full">
          <defs>
            <radialGradient id="h1" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.9" />
              <stop offset="45%" stopColor="#f97316" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fbbf24" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="h2" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#f97316" stopOpacity="0.75" />
              <stop offset="55%" stopColor="#fbbf24" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
            </radialGradient>
            <filter id="soft">
              <feGaussianBlur stdDeviation="18" />
            </filter>
          </defs>
          <g filter="url(#soft)" className="blob">
            <circle cx="178" cy="132" r="78" fill="url(#h1)" />
          </g>
          <g filter="url(#soft)" className="blob blob-delay">
            <circle cx="292" cy="168" r="64" fill="url(#h2)" />
          </g>
          <g filter="url(#soft)">
            <circle cx="240" cy="248" r="52" fill="url(#h2)" opacity="0.7" />
          </g>
          <path
            className="scan-path"
            d="M72 268 C 110 210, 140 150, 178 132 S 250 118, 292 168 S 320 240, 368 96"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          {[
            [72, 268],
            [140, 176],
            [178, 132],
            [240, 128],
            [292, 168],
            [330, 214],
            [368, 96],
          ].map(([x, y], i) => (
            <g key={i}>
              <circle cx={x} cy={y} r="9" fill="#38bdf8" opacity="0.18" />
              <circle cx={x} cy={y} r="4.2" fill="#f8fafc" stroke="#38bdf8" strokeWidth="1.4" />
            </g>
          ))}
          <circle cx="178" cy="132" r="6" fill="#ef4444">
            <animate attributeName="r" values="5;10;5" dur="2.4s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="1;0.4;1" dur="2.4s" repeatCount="indefinite" />
          </circle>
        </svg>
        <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3">
          <div className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-white/80">
            <p className="font-mono text-[10px] uppercase tracking-wider text-white/40">K-coefficient</p>
            <p className="mt-0.5 text-sm font-semibold text-heat-yellow">Focal 0.72 · Ambient 0.28</p>
          </div>
          <div className="hidden rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-right sm:block">
            <p className="font-mono text-[10px] uppercase tracking-wider text-white/40">Fixations</p>
            <p className="mt-0.5 text-sm font-semibold text-white">247</p>
          </div>
        </div>
      </div>
      <div className="float-card absolute -left-6 bottom-10 hidden w-40 rounded-2xl border border-white/15 bg-navy-800/90 p-3 shadow-xl lg:block">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-gaze">AOI transition</p>
        <div className="mt-2 grid grid-cols-3 gap-1">
          {[".82", ".11", ".07", ".09", ".74", ".17", ".14", ".21", ".65"].map((v, i) => (
            <div
              key={i}
              className="rounded bg-white/10 py-1.5 text-center font-mono text-[10px] text-white/80"
              style={{ background: `rgba(249,115,22,${Number(v) * 0.7})` }}
            >
              {v}
            </div>
          ))}
        </div>
      </div>
      <div className="float-card absolute -right-4 top-16 hidden w-36 rounded-2xl border border-white/15 bg-navy-800/90 p-3 shadow-xl lg:block" style={{ animationDelay: "-2s" }}>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-heat-orange">Scanpath 3D</p>
        <p className="mt-1 text-xs leading-4 text-white/60">Depth-encoded saccades over stimulus plane</p>
      </div>
    </div>
  );
}
