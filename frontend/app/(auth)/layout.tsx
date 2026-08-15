import Link from 'next/link';

import { config } from '@/lib/config';

/**
 * Auth shell (design §5.1): centred single-column card, minimal chrome, no
 * navigation into protected areas.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-8 px-4 py-16">
      <Link href="/" className="text-h2 font-semibold">
        {config.appName}
      </Link>
      <div className="w-full max-w-sm">{children}</div>
    </main>
  );
}
