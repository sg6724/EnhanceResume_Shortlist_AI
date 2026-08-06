import type { SVGProps } from "react";

export function SquiggleUnderline(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 120 16" fill="none" stroke="currentColor" strokeWidth={3}
      strokeLinecap="round" {...props}>
      <path d="M2 10c8-9 16-9 24 0s16 9 24 0 16-9 24 0 16 9 24 0 16-9 20-4" />
    </svg>
  );
}

export function StarBurst(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth={2.5}
      strokeLinecap="round" {...props}>
      <path d="M20 3v10M20 27v10M3 20h10M27 20h10M8 8l7 7M32 32l-7-7M8 32l7-7M32 8l-7 7" />
    </svg>
  );
}

export function SketchArrow(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 80 40" fill="none" stroke="currentColor" strokeWidth={2.5}
      strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M3 20c18-4 40-4 60-3M63 17c4 3 8 3 14 0M63 30c4-8 8-11 14-13" />
    </svg>
  );
}

export function DocumentStackIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
      <path d="M14 3v4h4" />
      <path d="M9 12h6M9 15.5h6" />
    </svg>
  );
}

export function TargetIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </svg>
  );
}

export function CopyStackIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="8" y="8" width="12" height="13" rx="1.5" />
      <path d="M5 16H4.5A1.5 1.5 0 0 1 3 14.5v-11A1.5 1.5 0 0 1 4.5 2h9A1.5 1.5 0 0 1 15 3.5V5" />
    </svg>
  );
}

export function ClockIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}
