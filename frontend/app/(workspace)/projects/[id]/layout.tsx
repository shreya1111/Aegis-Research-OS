'use client';

import { useParams } from 'next/navigation';

import { ProjectShell } from '@/components/layout/ProjectShell';

/**
 * Project workspace layout (design §5.1, §5.7 ProjectShell). Wraps every
 * project tab (Chat, Documents, Reports, Settings) in the persistent shell so
 * navigating between them swaps only the main content region.
 */
export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  const params = useParams<{ id: string }>();
  return <ProjectShell projectId={params.id}>{children}</ProjectShell>;
}
