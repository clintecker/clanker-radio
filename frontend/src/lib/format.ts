/** Pure formatting helpers. Keep free of DOM access so they stay unit-testable. */

export function formatClock(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '0:00';
  const total = Math.floor(seconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function formatTimeAgo(then: Date, now: Date = new Date()): string {
  const seconds = Math.max(0, Math.floor((now.getTime() - then.getTime()) / 1000));
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function formatUptime(start: string | undefined, now: Date = new Date()): string {
  if (!start) return '—';
  const startMs = Date.parse(start);
  if (Number.isNaN(startMs)) return '—';
  const diffMin = Math.max(0, Math.floor((now.getTime() - startMs) / 60_000));
  const days = Math.floor(diffMin / 1440);
  const hours = Math.floor((diffMin % 1440) / 60);
  const minutes = diffMin % 60;
  return days > 0 ? `${days}d ${hours}h` : `${hours}h ${minutes}m`;
}

/** Icecast reports "2026-09-19T04:57:53+0000" (no colon in offset), which Safari rejects. */
export function normalizeIso(value: string): string {
  return value.replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
}
