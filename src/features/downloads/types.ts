export type Platform = 'youtube' | 'instagram' | 'facebook' | 'twitter' | 'other'

export type JobStatus = 'queued'|'downloading'|'paused'|'merging'|'done'|'error'|'canceled'

export interface FormatItem {
    format_id?: string | null;   // merged formats set this to null
    format_string: string;       // ALWAYS present, e.g. "137+140" or "18"
    label: string;
    ext?: string;
  }
  
  export interface InfoResponse {
    title: string;
    thumbnail?: string;
    duration?: number;
    formats: FormatItem[];
  }

export interface DownloadJob {
  id: string
  url: string
  platform: Platform
  formatId: string
  formatLabel: string
  title?: string
  progress: number      // 0..1
  status: 'queued' | 'downloading' | 'paused' | 'done' | 'error'
}

export interface DownloadJobDTO {
    id: string
    url: string
    title?: string
    format_string: string
    ext?: string
    status: JobStatus
    progress: number
    downloaded_bytes: number
    total_bytes?: number | null       // ← allow null
    speed_bps?: number | null         // ← allow null
    eta_seconds?: number | null       // ← allow null
    filename?: string | null          // ← allow null
    error?: string | null             // ← allow null
  
    // optional UI-only fields if you add them
    label?: string
    platform?: string
  }

