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
      symbol: '📚',
      title: 'Grounded, never guessed',
      body: 'Every claim in a generated artifact carries a citation to a source that was actually retrieved.',
    },
    {
      symbol: '🔍',
      title: 'Transparent reasoning',
      body: 'A reasoning trace shows which agent ran, what it produced, and what it cost — never a black box.',
    },
    {
      symbol: '🌐',
      title: 'Your corpus, plus the web',
      body: 'Retrieve evidence from your own uploaded documents and the open academic literature together.',
    },
  ];

  return (
    <main className="flex min-h-dvh flex-col">
      {/* Header with heavy outline */}
      <header className="brutal-panel px-gap py-4">
        <div className="container flex items-center justify-between">
          <span className="text-h2 font-emphasis uppercase">{config.appName}</span>
          <div className="flex items-center gap-3">
            <Button asChild variant="ghost" size="sm">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/register">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero: Yellow poster with large uppercase statement */}
      <section className="relative overflow-hidden px-gap py-16 lg:py-24">
        <div className="container">
          <div className="brutal-poster relative z-10 px-8 py-12 lg:px-12 lg:py-16">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-12">
              <div className="space-y-6 lg:col-span-8">
                <p className="brutal-label text-primary-foreground/70">Research operating system</p>
                <h1 className="brutal-display-lg max-w-[20ch]">
                  An AI research assistant that shows its work.
                </h1>
              </div>
            </div>
          </div>

          {/* Violet band beneath with explanation and actions */}
          <div className="brutal-field relative -mt-6 px-8 py-8 lg:px-12">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-12">
              <div className="lg:col-span-8 lg:col-start-1">
                <p className="text-reading max-w-[60ch]">
                  {config.appName} ingests your documents, retrieves evidence from them and the open
                  academic web, and produces cited research artifacts — with every claim traceable to
                  a source.
                </p>
              </div>
              <div className="flex flex-col gap-3 lg:col-span-4">
                <Button asChild size="lg" variant="contrast">
                  <Link href="/register">Create account</Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href="/login">Sign in</Link>
                </Button>
              </div>
            </div>
            <div className="mt-6">
              <BackendStatus health={health} />
            </div>
          </div>
        </div>
      </section>

      {/* Features: Ruled ledger with symbols */}
      <section className="bg-card px-gap py-16 lg:py-20">
        <div className="container">
          <div className="space-y-8">
            <div className="flex items-center gap-4">
              <div className="brutal-label">01</div>
              <h2 className="text-h1 font-emphasis uppercase">Core capabilities</h2>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
              {features.map((feature, idx) => (
                <div key={feature.title} className="brutal-panel p-6">
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <span className="text-4xl">{feature.symbol}</span>
                      <span className="brutal-label text-accent">
                        {String(idx + 1).padStart(2, '0')}
                      </span>
                    </div>
                    <h3 className="text-h3 font-emphasis">{feature.title}</h3>
                    <p className="text-reading">{feature.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Numbered steps: Paper strips */}
      <section className="px-gap py-16 lg:py-20">
        <div className="container">
          <div className="space-y-8">
            <div className="flex items-center gap-4">
              <div className="brutal-label">02</div>
              <h2 className="text-h1 font-emphasis uppercase">How it works</h2>
            </div>

            <div className="space-y-6">
              {[
                {
                  step: '01',
                  title: 'Upload your sources',
                  body: 'Add documents from your research library or reference open academic papers.',
                },
                {
                  step: '02',
                  title: 'Ask your question',
                  body: 'Describe what you want to learn. The system retrieves relevant evidence.',
                },
                {
                  step: '03',
                  title: 'Review the artifact',
                  body: 'Get a cited answer with every claim linked to its source and full reasoning trace.',
                },
              ].map((step) => (
                <div key={step.step} className="brutal-panel p-6">
                  <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
                    <div className="flex items-center md:col-span-2">
                      <div className="brutal-signal inline-flex h-16 w-16 items-center justify-center">
                        <span className="text-h1 font-display">{step.step}</span>
                      </div>
                    </div>
                    <div className="space-y-2 md:col-span-10">
                      <h3 className="text-h2 font-emphasis">{step.title}</h3>
                      <p className="text-reading text-muted-foreground">{step.body}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Closing poster on red field */}
      <section className="brutal-signal px-gap py-16 lg:py-20">
        <div className="container">
          <div className="brutal-poster px-8 py-12 lg:px-12 lg:py-16">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
              <div className="space-y-6 lg:col-span-9">
                <h2 className="brutal-display max-w-[24ch]">
                  Research grounded in evidence, not guesswork.
                </h2>
                <p className="max-w-[60ch] text-reading">
                  Start building research artifacts with full citation and reasoning transparency.
                </p>
              </div>
              <div className="flex flex-col justify-center lg:col-span-3">
                <Button asChild size="lg" variant="contrast">
                  <Link href="/register">Get started</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer: grouped with panels */}
      <footer className="brutal-panel px-gap py-12">
        <div className="container">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-12">
            <div className="col-span-2 space-y-3 md:col-span-4">
              <span className="text-h3 font-emphasis uppercase">{config.appName}</span>
              <p className="text-small">
                AI research assistant with full citation transparency.
              </p>
            </div>
            <div className="space-y-3 md:col-span-2">
              <p className="brutal-label">Product</p>
              <ul className="space-y-2 text-small font-reading">
                <li>
                  <Link href="/register" className="hover:text-accent">
                    Sign up
                  </Link>
                </li>
                <li>
                  <Link href="/login" className="hover:text-accent">
                    Sign in
                  </Link>
                </li>
              </ul>
            </div>
            <div className="space-y-3 md:col-span-2">
              <p className="brutal-label">Learn</p>
              <ul className="space-y-2 text-small font-reading">
                <li>
                  <span className="text-muted-foreground">Documentation</span>
                </li>
                <li>
                  <span className="text-muted-foreground">Examples</span>
                </li>
              </ul>
            </div>
            <div className="col-span-2 space-y-3 md:col-span-4">
              <p className="brutal-label">System</p>
              <p className="text-small text-muted-foreground">
                Backend status displayed in header when available.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
