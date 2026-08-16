import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/nav";
import PortalProviders from "@/components/portal/providers";

export const metadata: Metadata = {
  title: "Sourcerer",
  description: "AI-powered RAG platform for educational content",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PortalProviders>
          <div className="ambient" />
          <Nav />
          <main className="relative z-10 ml-60 min-h-screen">{children}</main>
        </PortalProviders>
      </body>
    </html>
  );
}
