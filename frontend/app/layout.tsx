import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProposalGuard",
  description: "AI-powered proposal generation with grounding verification, bias detection, and human-in-the-loop review",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
