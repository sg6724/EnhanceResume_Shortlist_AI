import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "JobHunt AI",
  description: "Agentic job-hunting platform — tailor your resume to every JD automatically.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg text-text">
        <Sidebar />
        <main className="ml-56 min-h-screen p-8 max-w-[calc(100vw-14rem)]">
          {children}
        </main>
      </body>
    </html>
  );
}
