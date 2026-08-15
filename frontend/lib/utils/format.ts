/** Small presentation-only formatting helpers. */

const UNITS = ['B', 'KB', 'MB', 'GB'] as const;

/** Human-readable byte size, e.g. ``1.4 MB``. */
export function formatBytes(bytes: number): string {
  if (bytes <= 0) {
    return '0 B';
  }
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), UNITS.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${UNITS[exponent]}`;
}

/** Localised short date, e.g. ``5 Jan 2026``. */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
