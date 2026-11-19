import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const siteOrigin = process.env.SITE_ORIGIN ?? 'http://localhost:3000';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin),
  title: 'EngiDraw Verified',
  description: 'Deterministic, standards-aware engineering drawing generation.',
  openGraph: {
    title: 'EngiDraw Verified',
    description: 'Computational engineering, with evidence.',
    type: 'website',
    images: [{ url: new URL('/og.png', siteOrigin).toString(), width: 1200, height: 630, alt: 'EngiDraw Verified computational engineering workspace' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EngiDraw Verified',
    description: 'Computational engineering, with evidence.',
    images: [new URL('/og.png', siteOrigin).toString()],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
