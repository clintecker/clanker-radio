/** The bulletin archive: /api/breaks/index.json written hourly by generate_breaks_index.py. */

export interface Bulletin {
  filename: string;
  /** Station-local wall clock, no offset (e.g. "2026-09-22T11:07:47"). */
  timestamp: string;
  url: string;
  size_bytes: number;
}

export interface ArchiveIndex {
  generated_at: string;
  count: number;
  breaks: Bulletin[];
}

export function parseArchive(raw: unknown): ArchiveIndex {
  if (typeof raw !== 'object' || raw === null) throw new Error('archive index is not an object');
  const r = raw as Record<string, unknown>;
  const breaks = Array.isArray(r.breaks)
    ? r.breaks.flatMap((b): Bulletin[] => {
        if (typeof b !== 'object' || b === null) return [];
        const o = b as Record<string, unknown>;
        if (typeof o.url !== 'string' || typeof o.timestamp !== 'string') return [];
        // Only accept paths under the archive endpoint; never follow a foreign URL from the index.
        if (!o.url.startsWith('/api/breaks/') || !o.url.endsWith('.mp3')) return [];
        return [
          {
            filename: typeof o.filename === 'string' ? o.filename : (o.url.split('/').pop() ?? ''),
            timestamp: o.timestamp,
            url: o.url,
            size_bytes: typeof o.size_bytes === 'number' ? o.size_bytes : 0,
          },
        ];
      })
    : [];
  return { generated_at: typeof r.generated_at === 'string' ? r.generated_at : '', count: breaks.length, breaks };
}

export async function fetchArchive(signal?: AbortSignal): Promise<ArchiveIndex> {
  const res = await fetch('/api/breaks/index.json', { signal, headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`archive index: HTTP ${res.status}`);
  return parseArchive(await res.json());
}

/** "2026-09-22T11:07:47" → "Sep 22, 11:07" in the station's own wall clock. */
export function formatBulletinTime(ts: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(ts);
  if (!m) return ts;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[Number(m[2]) - 1] ?? m[2]} ${Number(m[3])}, ${m[4]}:${m[5]}`;
}
