'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@/lib/utils/cn';

import { PROJECT_NAV_ITEMS, projectNavHref } from '@/components/layout/project-nav';

export interface SideNavProps {
  projectId: string;
  /** Called after a link is activated, so the mobile drawer can close itself. */
  onNavigate?: () => void;
}

/**
 * Workspace left navigation (design §5.2). Renders the same item set on desktop
 * and inside the mobile drawer. The active tab is derived from the current path
 * so navigation state survives tab switches (design §5.1 persistent layout).
 */
export function SideNav({ projectId, onNavigate }: SideNavProps): React.JSX.Element {
  const pathname = usePathname();
  const basePath = `/projects/${projectId}`;

  function isActive(segment: string): boolean {
    const href = projectNavHref(projectId, segment);
    if (segment === '') {
      return pathname === basePath;
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <nav aria-label="Workspace" className="flex flex-col gap-1 p-3">
      {PROJECT_NAV_ITEMS.map((item) => {
        const active = isActive(item.segment);

        if (item.comingSoon) {
          return (
            <span
              key={item.label}
              aria-disabled="true"
              title="Coming soon"
              className="flex items-center justify-between gap-3 rounded-control px-3 py-2 text-body-sm text-muted-foreground/60"
            >
              <span className="flex items-center gap-3">
                <span aria-hidden="true">{item.glyph}</span>
                {item.label}
              </span>
              <span className="rounded-full bg-muted px-2 py-0.5 text-caption">Soon</span>
            </span>
          );
        }

        return (
          <Link
            key={item.label}
            href={projectNavHref(projectId, item.segment)}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'flex items-center gap-3 rounded-control px-3 py-2 text-body-sm transition-colors',
              active
                ? 'bg-primary/10 font-medium text-primary'
                : 'text-foreground hover:bg-accent hover:text-accent-foreground',
            )}
          >
            <span aria-hidden="true">{item.glyph}</span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
