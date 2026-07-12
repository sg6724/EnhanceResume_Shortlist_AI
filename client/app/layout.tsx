import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GetHired AI",
  description: "Agentic job-hunting platform — tailor your resume to every JD automatically.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-bg text-text font-sans">
        <Sidebar />
        <main className="ml-56 min-h-screen p-8 max-w-[calc(100vw-14rem)]">
          {children}
        </main>
      </body>
    </html>
  );
}
