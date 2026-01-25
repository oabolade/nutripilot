import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "NutriPilot AI | Your Autonomous Nutrition Co-Pilot",
  description: "Snap a photo of your meal and get instant AI-powered nutritional analysis with personalized health recommendations.",
  keywords: ["nutrition", "AI", "food analysis", "health", "meal tracking", "calorie counter"],
  authors: [{ name: "NutriPilot Team" }],
  openGraph: {
    title: "NutriPilot AI | Your Autonomous Nutrition Co-Pilot",
    description: "Snap a photo of your meal and get instant AI-powered nutritional analysis.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} antialiased`}>
        <div className="gradient-bg" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
