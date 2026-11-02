import {
  BarChart3,
  FileText,
  History,
  MessageSquare,
  Network,
  ScrollText,
  Settings,
  type LucideIcon,
} from 'lucide-react';

/** Workspace left-nav definition (design §5.2). Single source for the tab set
 * so the sidebar and mobile drawer render identically. */

export interface ProjectNavItem {
  /** URL segment appended to `/projects/[id]`. Empty string = the Chat index. */
  segment: string;
  label: string;
  icon: LucideIcon;
}

export const PROJECT_NAV_ITEMS: readonly ProjectNavItem[] = [
  { segment: '', label: 'Chat', icon: MessageSquare },
  { segment: 'documents', label: 'Documents', icon: FileText },
  { segment: 'graph', label: 'Knowledge Graph', icon: Network },
  { segment: 'analytics', label: 'Analytics', icon: BarChart3 },
  { segment: 'reports', label: 'Reports', icon: ScrollText },
  { segment: 'activity', label: 'Activity', icon: History },
  { segment: 'settings', label: 'Settings', icon: Settings },
];

/** Build the href for a nav item within a project. */
export function projectNavHref(projectId: string, segment: string): string {
  return segment ? `/projects/${projectId}/${segment}` : `/projects/${projectId}`;
}
