export function GlowBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-72 -z-10 opacity-40 blur-3xl"
      style={{
        background:
          "radial-gradient(60% 100% at 20% 0%, #6ea8fe 0%, transparent 60%), " +
          "radial-gradient(50% 100% at 60% 0%, #a78bfa 0%, transparent 60%), " +
          "radial-gradient(40% 100% at 90% 20%, #2dd4bf 0%, transparent 60%)",
      }}
    />
  );
}
