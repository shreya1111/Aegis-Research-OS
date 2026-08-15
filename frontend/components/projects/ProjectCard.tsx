import Link from 'next/link';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Project } from '@/types/api';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function ProjectCard({ project }: { project: Project }): React.JSX.Element {
  return (
    <Link href={`/projects/${project.id}`} className="block">
      <Card className="h-full transition-colors hover:border-primary/50">
        <CardHeader>
          <CardTitle className="line-clamp-1">{project.title}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <p className="line-clamp-2 text-body-sm text-muted-foreground">
            {project.description ?? 'No description yet.'}
          </p>
          <p className="text-caption text-muted-foreground">
            Created {formatDate(project.created_at)}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
