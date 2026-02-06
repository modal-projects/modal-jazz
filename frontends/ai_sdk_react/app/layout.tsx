import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata = {
  title: "Modal Jazz Chat",
  openGraph: {
    title: "Modal Jazz Chat",
    description: "we have ai at home. built with vercel and modal",
    type: "website",
    siteName: "Modal Jazz",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen flex flex-col font-sans">
        {/* Header */}
        <header className="border-b border-border px-4 sm:px-6 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-3">
            <span className="text-green-bright font-semibold text-lg">
              Modal Jazz
            </span>
            <span className="text-text-primary/50 text-sm">Chat</span>
          </a>
          <a
            href="https://github.com/modal-projects/modal-jazz"
            target="_blank"
            rel="noopener noreferrer"
            className="text-text-primary/50 hover:text-green-bright transition-colors text-sm"
          >
            GitHub
          </a>
        </header>

        {/* Main */}
        <main className="flex-1 flex flex-col">{children}</main>

        {/* Footer */}
        <footer className="border-t border-border px-4 sm:px-6 py-3 text-center text-xs text-text-primary/40">
          Built with{" "}
          <a
            href="https://modal.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-green-bright/70 hover:text-green-bright transition-colors"
          >
            Modal
          </a>
        </footer>
      </body>
    </html>
  );
}
