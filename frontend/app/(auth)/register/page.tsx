import Link from 'next/link';

import { RedirectIfAuthenticated } from '@/components/auth/RedirectIfAuthenticated';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export const metadata = { title: 'Create an account' };

export default function RegisterPage(): React.JSX.Element {
  return (
    <Card>
      <RedirectIfAuthenticated />
      <CardHeader>
        <CardTitle>Create an account</CardTitle>
        <CardDescription>Start a research workspace in a minute.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <RegisterForm />
        <p className="text-body-sm text-muted-foreground">
          Already have an account?{' '}
          <Link href="/login" className="text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
