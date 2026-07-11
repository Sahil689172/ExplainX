import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";

import { AppProviders } from "@/components/providers/AppProviders";

import "@/styles/globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const sans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ExplainX",
  description:
    "Offline-first AI Presentation-to-Video Engine for educational explainers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
