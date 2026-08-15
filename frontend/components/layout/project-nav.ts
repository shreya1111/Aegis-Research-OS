/** Workspace left-nav definition (design §5.2). Single source for the tab set
 * so the sidebar and mobile drawer render identically. */

export interface ProjectNavItem {
  /** URL segment appended to `/projects/[id]`. Empty string = the Chat index. */
  segment: string;
  label: string;
  /** Monospace glyph used as the icon (kept dependency-free). */
  glyph: string;
  /** Stretch features are shown but disabled with a "coming soon" affordance
   * (design §5.1: placeholder honesty). */
  comingSoon?: boolean;
}

export const PROJECT_NAV_ITEMS: readonly ProjectNavItem[] = [
  { segment: '', label: 'Chat', glyph: '💬' },
  { segment: 'documents', label: 'Documents', glyph: '📄' },
  { segment: 'graph', label: 'Knowledge Graph', glyph: '🕸', comingSoon: true },
  { segment: 'reports', label: 'Reports', glyph: '📊' },
  { segment: 'settings', label: 'Settings', glyph: '⚙' },
] as const;

/** Build the href for a nav item within a project. */
export function projectNavHref(projectId: string, segment: string): string {
  return segment ? `/projects/${projectId}/${segment}` : `/projects/${projectId}`;
}
