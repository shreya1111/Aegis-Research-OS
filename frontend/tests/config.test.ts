import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const ENV_KEYS = ['NEXT_PUBLIC_API_URL', 'API_INTERNAL_URL'] as const;
let originalEnv: Record<string, string | undefined>;

beforeEach(() => {
  originalEnv = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));
  // `lib/config.ts` reads process.env at module-evaluation time, so each test
  // needs a fresh module instance to observe its own env mutations.
  vi.resetModules();
});

afterEach(() => {
  for (const key of ENV_KEYS) {
    if (originalEnv[key] === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = originalEnv[key];
    }
  }
});

describe('config', () => {
  it('defaults both base URLs to localhost:8000 when nothing is set', async () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.API_INTERNAL_URL;

    const { config } = await import('@/lib/config');

    expect(config.apiBaseUrl).toBe('http://localhost:8000');
    expect(config.serverApiBaseUrl).toBe('http://localhost:8000');
  });

  it('serverApiBaseUrl falls back to the browser URL when API_INTERNAL_URL is unset', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:9000';
    delete process.env.API_INTERNAL_URL;

    const { config } = await import('@/lib/config');

    expect(config.apiBaseUrl).toBe('http://localhost:9000');
    expect(config.serverApiBaseUrl).toBe('http://localhost:9000');
  });

  it('serverApiBaseUrl uses API_INTERNAL_URL when set, independent of the browser URL', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    process.env.API_INTERNAL_URL = 'http://backend:8000';

    const { config } = await import('@/lib/config');

    expect(config.apiBaseUrl).toBe('http://localhost:8000');
    expect(config.serverApiBaseUrl).toBe('http://backend:8000');
  });

  it('strips trailing slashes from both URLs', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/';
    process.env.API_INTERNAL_URL = 'http://backend:8000/';

    const { config } = await import('@/lib/config');

    expect(config.apiBaseUrl).toBe('http://localhost:8000');
    expect(config.serverApiBaseUrl).toBe('http://backend:8000');
  });

  it('throws a clear error when NEXT_PUBLIC_API_URL is malformed', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'not a url';

    await expect(import('@/lib/config')).rejects.toThrow('NEXT_PUBLIC_API_URL is not a valid URL');
  });

  it('throws a clear error when API_INTERNAL_URL is malformed', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    process.env.API_INTERNAL_URL = 'not a url';

    await expect(import('@/lib/config')).rejects.toThrow('API_INTERNAL_URL is not a valid URL');
  });
});
