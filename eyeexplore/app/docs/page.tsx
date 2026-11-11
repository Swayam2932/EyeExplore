import type { Metadata } from "next";
import { DocsSidebar } from "@/components/docs-sidebar";

export const metadata: Metadata = {
  title: "User Guidelines",
  description: "Data schema, I-VT parameters, and CSV troubleshooting for EyeExplore.",
};

export default function DocsPage() {
  return (
    <div className="bg-ice">
      <div className="border-b border-mist bg-navy-950 px-4 py-10 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gaze">Documentation</p>
          <h1 className="mt-2 font-serif text-3xl sm:text-4xl">User guidelines</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/60">
            Technical reference for ingesting scanpaths, setting analysis parameters,
            and resolving common CSV parse errors.
          </p>
        </div>
      </div>
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 lg:grid-cols-[240px_1fr] sm:px-6 lg:px-8">
        <DocsSidebar />
        <article className="space-y-14 rounded-2xl border border-mist bg-white p-6 shadow-sm sm:p-10">
          <section id="overview">
            <h2 className="font-serif text-2xl text-navy-900">Overview</h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              EyeExplore expects a stimulus (image or video) plus one or more
              participant scanpath files. Each scanpath is a time-ordered table of
              gaze samples. After ingest, the pipeline applies an I-VT (velocity
              threshold) filter, computes fixations and saccades, then drives
              heatmaps, overlays, scarf plots, 3D scanpaths, AOI matrices, and
              K-Coefficient classification.
            </p>
          </section>

          <section id="data-schema">
            <h2 className="font-serif text-2xl text-navy-900">Data schema requirements</h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              Custom CSV uploads must include at least three columns. Headers are
              matched case-insensitively. Extra columns (participant ID, trial,
              pupil size) are preserved but not required.
            </p>
            <div className="mt-5 overflow-x-auto rounded-xl border border-mist">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="bg-navy-950 text-white">
                  <tr>
                    <th className="px-4 py-3 font-medium">Column</th>
                    <th className="px-4 py-3 font-medium">Aliases</th>
                    <th className="px-4 py-3 font-medium">Unit</th>
                    <th className="px-4 py-3 font-medium">Notes</th>
                  </tr>
                </thead>
                <tbody className="bg-white text-ink">
                  <tr className="border-t border-mist">
                    <td className="px-4 py-3 font-mono font-medium">X</td>
                    <td className="px-4 py-3 text-muted">x, gaze_x, pos_x</td>
                    <td className="px-4 py-3">px or norm [0,1]</td>
                    <td className="px-4 py-3 text-muted">Horizontal gaze. Screen or stimulus space.</td>
                  </tr>
                  <tr className="border-t border-mist bg-ice/60">
                    <td className="px-4 py-3 font-mono font-medium">Y</td>
                    <td className="px-4 py-3 text-muted">y, gaze_y, pos_y</td>
                    <td className="px-4 py-3">px or norm [0,1]</td>
                    <td className="px-4 py-3 text-muted">Vertical gaze. Origin is top-left unless specified.</td>
                  </tr>
                  <tr className="border-t border-mist">
                    <td className="px-4 py-3 font-mono font-medium">Time</td>
                    <td className="px-4 py-3 text-muted">t, timestamp, time_ms</td>
                    <td className="px-4 py-3">ms (preferred) or s</td>
                    <td className="px-4 py-3 text-muted">Monotonic. Relative to trial start is ideal.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <pre className="mt-5 overflow-x-auto rounded-xl bg-navy-950 p-4 font-mono text-xs leading-6 text-white/80">
{`x,y,time_ms,participant
412.3,188.1,0,P01
418.0,190.4,8,P01
425.7,193.0,16,P01`}
            </pre>
          </section>

          <section id="parameters">
            <h2 className="font-serif text-2xl text-navy-900">Parameter definitions</h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              Defaults are conservative for 60–120 Hz remote trackers. Raise
              thresholds for noisy mobile data; lower them for high-Hz tower
              systems.
            </p>
            <dl className="mt-6 space-y-5">
              {[
                {
                  name: "I-VT velocity threshold",
                  def: "Samples whose instantaneous velocity exceeds this value are labeled saccades; the remainder form fixation candidates. Default: 30°/s (or 0.35 px/ms if visual angle is unknown).",
                },
                {
                  name: "Minimum fixation duration",
                  def: "Fixation candidates shorter than this are discarded or merged. Default: 80 ms.",
                },
                {
                  name: "Maximum gap interpolate",
                  def: "Blink or dropout gaps shorter than this are linearly interpolated. Default: 75 ms.",
                },
                {
                  name: "Heatmap Gaussian σ",
                  def: "Spatial kernel for attention maps, in stimulus pixels. Default: 1.5° equivalent (~50 px at typical viewing distance).",
                },
                {
                  name: "K-Coefficient window",
                  def: "Sliding window used to estimate local fixation/saccade density for Focal vs. Ambient classification. Default: 2 s.",
                },
                {
                  name: "AOI dwell merge",
                  def: "Consecutive samples in the same AOI shorter than this gap are merged into one dwell. Default: 40 ms.",
                },
              ].map((p) => (
                <div key={p.name} className="rounded-xl border border-mist bg-ice p-4">
                  <dt className="font-semibold text-navy-900">{p.name}</dt>
                  <dd className="mt-1 text-sm leading-6 text-muted">{p.def}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section id="troubleshooting">
            <h2 className="font-serif text-2xl text-navy-900">Troubleshooting CSV uploads</h2>
            <div className="mt-5 space-y-4">
              {[
                {
                  err: "Missing required column: Time",
                  fix: "Rename your timestamp header to time, t, timestamp, or time_ms. Epoch timestamps are accepted if they are monotonic within a trial.",
                },
                {
                  err: "Non-numeric values in X/Y",
                  fix: "Strip units (px, mm) from cells. Use a period as the decimal separator. Empty cells should be blank, not NA in mixed types — prefer a single missing token.",
                },
                {
                  err: "Time is not monotonic",
                  fix: "Sort by time within each participant/trial. Duplicate timestamps from binocular merge should be averaged, not stacked.",
                },
                {
                  err: "Coordinates out of stimulus bounds",
                  fix: "Confirm whether values are in screen pixels vs. stimulus pixels vs. normalized 0–1. Set origin and scale in the upload dialog, or pre-crop to the stimulus ROI.",
                },
                {
                  err: "Encoding / delimiter errors",
                  fix: "UTF-8 without BOM is preferred. Comma, semicolon, and tab delimiters are auto-detected. If detection fails, export as comma-separated from your tracker software.",
                },
              ].map((t) => (
                <div key={t.err} className="rounded-xl border border-mist p-4">
                  <p className="font-mono text-sm text-heat-red">{t.err}</p>
                  <p className="mt-2 text-sm leading-6 text-muted">{t.fix}</p>
                </div>
              ))}
            </div>
          </section>
        </article>
      </div>
    </div>
  );
}
