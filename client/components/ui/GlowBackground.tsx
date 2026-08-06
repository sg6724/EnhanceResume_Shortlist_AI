export function GlowBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-[28rem] -z-10 blur-2xl"
      style={{
        background:
          "radial-gradient(45% 80% at 15% 10%, rgba(255,111,94,0.35) 0%, transparent 70%), " +
          "radial-gradient(40% 80% at 55% 0%, rgba(185,166,245,0.35) 0%, transparent 70%)",
      }}
    />
  );
}
