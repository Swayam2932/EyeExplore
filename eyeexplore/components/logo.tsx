import Link from "next/link";

export function Logo({ invert = false }: { invert?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <span className="relative flex h-8 w-8 items-center justify-center">
        <span className="heat-gradient absolute inset-0 rounded-lg opacity-90" />
        <svg
          viewBox="0 0 32 32"
          className="relative h-8 w-8"
          aria-hidden
        >
          <ellipse cx="16" cy="16" rx="11" ry="7" fill="none" stroke="white" strokeWidth="1.6" />
          <circle cx="16" cy="16" r="3.2" fill="white" />
          <circle cx="17.2" cy="15" r="1" fill="#0b1a33" />
        </svg>
      </span>
      <span
        className={`text-[17px] font-semibold tracking-tight ${invert ? "text-white" : "text-navy-900"}`}
      >
        EyeExplore
      </span>
    </Link>
  );
}
