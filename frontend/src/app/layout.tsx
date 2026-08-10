import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Knowledge Management Intelligence",
  description: "Advanced RAG System",
  icons: {
    icon: "/favicon.ico", // Ensure this exists or falls back
    shortcut: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={cn(inter.className, "antialiased min-h-screen bg-background")} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
