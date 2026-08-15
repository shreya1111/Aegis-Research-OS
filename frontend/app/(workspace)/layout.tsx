import { AuthGuard } from '@/components/auth/AuthGuard';
import { TopBar } from '@/components/layout/TopBar';

/**
 * Workspace shell (design §5.1): persistent top bar over all authenticated
 * pages. Per-project navigation (Chat, Documents, Reports, Settings) is added
 * in `projects/[id]/layout.tsx` once those tabs exist (Phase 2+).
 */
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <AuthGuard>
      <div className="flex min-h-dvh flex-col">
        <TopBar />
        <main className="flex-1">{children}</main>
      </div>
    </AuthGuard>
  );
}
