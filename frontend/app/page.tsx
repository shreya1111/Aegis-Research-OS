import Link from 'next/link';

import { BackendStatus } from '@/components/system/BackendStatus';
import { Button } from '@/components/ui/button';
import { fetchHealth } from '@/lib/api/health';
import { config } from '@/lib/config';
import type { HealthStatus } from '@/types/api';

// Liveness must reflect the current process state, never a cached build.
export const dynamic = 'force-dynamic';

async function loadHealth(): Promise<HealthStatus | null> {
  try {
    return await fetchHealth();
  } catch {
    // An unreachable backend is an expected state during development; the page
    // reports it rather than failing to render.
    return null;
  }
}

export default async function HomePage(): Promise<React.JSX.Element> {
  const health = await loadHealth();

  const features = [
    {
      title: 'Grounded, never guessed',
      body: 'Every claim in a generated artifact carries a citation to a source that was actually retrieved.',
    },
    {
      title: 'Transparent reasoning',
      body: 'A reasoning trace shows which agent ran, what it produced, and what it cost — never a black box.',
    },
    {
      title: 'Your corpus, plus the web',
      body: 'Retrieve evidence from your own uploaded documents and the open academic literature together.',
    },
  ];

  return (
    <main className="flex min-h-dvh flex-col">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <span className="text-h3 font-semibold">{config.appName}</span>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/register">Get started</Link>
          </Button>
        </div>
      </header>

      <section className="container flex max-w-prose flex-col gap-6 py-20">
        <div className="space-y-3">
          <p className="text-caption uppercase tracking-widest text-muted-foreground">
            Research operating system
          </p>
          <h1 className="text-display font-semibold">
            An AI research assistant that shows its work.
          </h1>
          <p className="text-body text-muted-foreground">
            {config.appName} ingests your documents, retrieves evidence from them and the open
            academic web, and produces cited research artifacts — with every claim traceable to a
            source.
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild size="lg">
            <Link href="/register">Create an account</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
        <BackendStatus health={health} />
      </section>

      <section className="border-t bg-muted/30">
        <div className="container grid grid-cols-1 gap-6 py-16 md:grid-cols-3">
          {features.map((feature) => (
            <div key={feature.title} className="space-y-2">
              <h2 className="text-h3 font-semibold">{feature.title}</h2>
              <p className="text-body-sm text-muted-foreground">{feature.body}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
