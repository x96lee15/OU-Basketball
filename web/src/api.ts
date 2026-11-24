import type { DatasetPayload } from './types';

export interface SyncResponse {
  synced: boolean;
  message: string;
  data?: DatasetPayload;
}

export async function loadDataset(): Promise<{ data: DatasetPayload; mode: 'api' | 'static' }> {
  // Try live Express API first; fall back seamlessly to static JSON bundle (e.g. Netlify / vite preview).
  try {
    const res = await fetch('/api/data');
    if (res.ok) {
      const ct = res.headers.get('content-type') || '';
      if (ct.includes('application/json')) {
        return { data: (await res.json()) as DatasetPayload, mode: 'api' };
      }
    }
  } catch {
    // Fall through to static file
  }

  const staticRes = await fetch('/data/ou_3pt_data.json');
  if (!staticRes.ok) {
    throw new Error(`Failed to load dataset (HTTP ${staticRes.status}). Run "python main.py report" first.`);
  }
  return { data: (await staticRes.json()) as DatasetPayload, mode: 'static' };
}

export async function syncCurrentSeason(season = '2026-27'): Promise<SyncResponse> {
  const res = await fetch('/api/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ season }),
  });

  if (!res.ok) {
    let msg = `Sync endpoint unavailable (HTTP ${res.status}). Start the local API server with "npm run dev" or run "python main.py run --seasons ${season}".`;
    try {
      const body = (await res.json()) as { message?: string };
      if (body.message) msg = body.message;
    } catch {
      // keep default message
    }
    return { synced: false, message: msg };
  }

  return (await res.json()) as SyncResponse;
}
