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
