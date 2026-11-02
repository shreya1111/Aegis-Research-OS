import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';

/**
 * Neo Brutalism Design System
 * Press-sheet aesthetic with cream paper, heavy black outlines, yellow emphasis,
 * red signals, violet fields, and solid offset shadows.
 */
const config: Config = {
  darkMode: ['class'],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: 'var(--dp-spacing-gap)',
      screens: { 
        sm: '640px',
        md: '720px',
        lg: '1050px',
        xl: '1400px',
      },
    },
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--success-foreground))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))',
        },
        info: {
          DEFAULT: 'hsl(var(--info))',
          foreground: 'hsl(var(--info-foreground))',
        },
      },
      borderRadius: {
        control: 'var(--radius-control)',
        surface: 'var(--radius-surface)',
      },
      borderWidth: {
        panel: 'var(--dp-border-panel)',
        divider: 'var(--dp-border-divider)',
        annotation: 'var(--dp-border-annotation)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Neo Brutalism display scales - heavy and uppercase
        'display-xl': ['5rem', { lineHeight: '0.95', letterSpacing: 'var(--dp-typography-display-tracking)', fontWeight: 'var(--dp-typography-display-weight)' }],
        'display-lg': ['3.5rem', { lineHeight: '1', letterSpacing: 'var(--dp-typography-display-tracking)', fontWeight: 'var(--dp-typography-display-weight)' }],
        display: ['2.5rem', { lineHeight: '1.1', letterSpacing: 'var(--dp-typography-display-tracking)', fontWeight: 'var(--dp-typography-display-weight)' }],
        h1: ['2rem', { lineHeight: '1.1', fontWeight: 'var(--dp-typography-emphasis-weight)' }],
        h2: ['1.5rem', { lineHeight: '1.2', fontWeight: 'var(--dp-typography-emphasis-weight)' }],
        h3: ['1.25rem', { lineHeight: '1.3', fontWeight: 'var(--dp-typography-emphasis-weight)' }],
        body: ['var(--dp-typography-body)', { lineHeight: '1.5', fontWeight: 'var(--dp-typography-reading-weight)' }],
        reading: ['var(--dp-typography-reading)', { lineHeight: '1.6', fontWeight: 'var(--dp-typography-reading-weight)' }],
        small: ['var(--dp-typography-small)', { lineHeight: '1.5', fontWeight: 'var(--dp-typography-reading-weight)' }],
        metadata: ['var(--dp-typography-metadata)', { lineHeight: '1.4' }],
        label: ['var(--dp-typography-label)', { lineHeight: '1.4', textTransform: 'uppercase', fontWeight: 'var(--dp-typography-emphasis-weight)' }],
      },
      fontWeight: {
        reading: 'var(--dp-typography-reading-weight)',
        emphasis: 'var(--dp-typography-emphasis-weight)',
        display: 'var(--dp-typography-display-weight)',
      },
      letterSpacing: {
        display: 'var(--dp-typography-display-tracking)',
      },
      spacing: {
        gap: 'var(--dp-spacing-gap)',
        'gap-compact': 'var(--dp-spacing-gap-compact)',
      },
      boxShadow: {
        'brutal': '6px 6px 0 0 hsl(var(--foreground))',
        'brutal-sm': '4px 4px 0 0 hsl(var(--foreground))',
        'brutal-lg': '8px 8px 0 0 hsl(var(--foreground))',
        'brutal-hover': '8px 8px 0 0 hsl(var(--foreground))',
      },
      transitionDuration: {
        interaction: 'var(--dp-motion-interaction)',
      },
    },
  },
  plugins: [animate],
};

export default config;
