import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/app-shell";
import PortalProviders from "@/components/portal/providers";

export const metadata: Metadata = {
  title: "Sourcerer",
  description: "Your academic resource library, served with focus.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PortalProviders>
          <AppShell>{children}</AppShell>
        </PortalProviders>
      </body>
    </html>
  );
}
