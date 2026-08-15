import { describe, expect, it } from 'vitest';

import { formatBytes, formatDate } from '@/lib/utils/format';

describe('formatBytes', () => {
  it('formats zero and negatives as 0 B', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(-5)).toBe('0 B');
  });

  it('formats bytes without decimals', () => {
    expect(formatBytes(512)).toBe('512 B');
  });

  it('formats kilobytes and megabytes with one decimal', () => {
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(1_572_864)).toBe('1.5 MB');
  });
});

describe('formatDate', () => {
  it('formats an ISO date into a readable short form', () => {
    const formatted = formatDate('2026-01-05T00:00:00Z');
    expect(formatted).toMatch(/2026/);
    expect(formatted).toMatch(/Jan/);
  });
});
