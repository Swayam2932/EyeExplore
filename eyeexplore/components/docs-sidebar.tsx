"use client";

import { docsSections } from "@/lib/site";
import { useEffect, useState } from "react";

export function DocsSidebar() {
  const [active, setActive] = useState<string>(docsSections[0].id);

  useEffect(() => {
    const els = docsSections.map((s) => document.getElementById(s.id)).filter(Boolean);
    const obs = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (vis?.target.id) setActive(vis.target.id);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: [0, 0.25, 0.5] },
    );
    els.forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <nav className="rounded-2xl border border-mist bg-white p-4 lg:sticky lg:top-24">
      <p className="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Guidelines</p>
      <ul className="mt-3 space-y-1">
        {docsSections.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className={`block rounded-lg px-3 py-2 text-sm ${
                active === s.id ? "bg-navy-900 font-medium text-white" : "text-muted hover:bg-ice hover:text-navy-900"
              }`}
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
