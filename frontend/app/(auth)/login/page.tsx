import Link from 'next/link';
import { Suspense } from 'react';

import { LoginForm } from '@/components/auth/LoginForm';
import { RedirectIfAuthenticated } from '@/components/auth/RedirectIfAuthenticated';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export const metadata = { title: 'Sign in' };

export default function LoginPage(): React.JSX.Element {
  return (
    <Card>
      <RedirectIfAuthenticated />
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Pick up where you left off.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {/* useSearchParams requires a Suspense boundary in a static shell (Next.js App Router). */}
        <Suspense>
          <LoginForm />
        </Suspense>
        <p className="text-body-sm text-muted-foreground">
          Don&apos;t have an account?{' '}
          <Link href="/register" className="text-primary underline-offset-4 hover:underline">
            Create one
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
