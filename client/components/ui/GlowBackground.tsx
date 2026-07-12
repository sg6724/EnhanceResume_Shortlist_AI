export function GlowBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-[28rem] -z-10 blur-2xl"
      style={{
        background:
          "radial-gradient(45% 80% at 15% 10%, rgba(110,168,254,0.55) 0%, transparent 70%), " +
          "radial-gradient(40% 80% at 55% 0%, rgba(167,139,250,0.5) 0%, transparent 70%), " +
          "radial-gradient(35% 70% at 90% 15%, rgba(45,212,191,0.45) 0%, transparent 70%)",
      }}
    />
  );
}
