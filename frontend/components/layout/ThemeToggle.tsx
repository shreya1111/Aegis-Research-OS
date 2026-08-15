'use client';

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
      <span aria-hidden="true">{isDark ? '☀︎' : '☾'}</span>
      <span className="sr-only">{isDark ? 'Light mode' : 'Dark mode'}</span>
    </Button>
  );
}
