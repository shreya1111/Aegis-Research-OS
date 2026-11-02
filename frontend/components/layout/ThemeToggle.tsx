'use client';

import { Moon, Sun } from 'lucide-react';

import { useTheme } from '@/lib/theme/theme-context';

import { Button } from '@/components/ui/button';

export function ThemeToggle(): React.JSX.Element {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {isDark ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
    </Button>
  );
}
