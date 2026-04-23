import type { Metadata } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const fontSans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const fontSerif = Fraunces({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  axes: ["opsz"],
});

const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "ClaimGuard – Health Claims, die vor Gericht halten",
    template: "%s · ClaimGuard",
  },
  description:
    "ClaimGuard prüft Werbeaussagen für Supplements und Functional Food gegen die EU-Health-Claims-Verordnung – inklusive impliziter Aussagen, mit Rechtsgrundlage und Reformulierung.",
  metadataBase: new URL("https://claimguard.de"),
  openGraph: {
    type: "website",
    locale: "de_DE",
    siteName: "ClaimGuard",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="de"
      className={`${fontSans.variable} ${fontSerif.variable} ${fontMono.variable}`}
    >
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
