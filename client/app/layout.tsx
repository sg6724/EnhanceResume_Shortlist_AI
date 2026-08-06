import type { Metadata } from "next";
import { Inter, Fraunces } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  style: ["normal", "italic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "GetHired AI",
  description: "Agentic job-hunting platform — tailor your resume to every JD automatically.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable}`}>
      <body className="bg-bg text-text font-sans">
        <Navbar />
        <main className="min-h-screen px-6 md:px-10 py-6 max-w-7xl mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
