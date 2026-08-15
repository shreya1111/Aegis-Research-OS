import type { Metadata, Viewport } from 'next';

import { Toaster } from '@/components/feedback/Toaster';
import { config } from '@/lib/config';
import { AuthProvider } from '@/lib/auth/auth-context';
import { ThemeProvider } from '@/lib/theme/theme-context';
import { ToastProvider } from '@/lib/toast/toast-context';

import './globals.css';

export const metadata: Metadata = {
  title: {
    default: config.appName,
    template: `%s · ${config.appName}`,
  },
  description:
    'Autonomous multi-agent AI research assistant: ingest documents, retrieve evidence, and produce cited research artifacts.',
  applicationName: config.appName,
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  colorScheme: 'light dark',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>): React.JSX.Element {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh font-sans">
        <ThemeProvider>
          <ToastProvider>
            <AuthProvider>{children}</AuthProvider>
            <Toaster />
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
