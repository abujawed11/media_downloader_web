# Frontend Fix: Job Persistence Across Page Refresh

## Problem
When you refresh the page, the UI loses track of ongoing downloads, but they continue in the background. The job ID doesn't change - the frontend just loses it.

## Solution
Save job IDs to `localStorage` and restore them on page load.

---

## Implementation Example (React/TypeScript)

### 1. Create a Job Storage Helper

```typescript
// src/utils/jobStorage.ts

interface StoredJob {
  id: string;
  url: string;
  title: string;
  format: string;
  startedAt: number;
  status?: string;
}

const STORAGE_KEY_PREFIX = 'media_job_';
const MAX_JOB_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

export const JobStorage = {
  /**
   * Save a job to localStorage
   */
  save(job: StoredJob): void {
    const key = `${STORAGE_KEY_PREFIX}${job.id}`;
    localStorage.setItem(key, JSON.stringify(job));
  },

  /**
   * Get a specific job by ID
   */
  get(jobId: string): StoredJob | null {
    const key = `${STORAGE_KEY_PREFIX}${jobId}`;
    const data = localStorage.getItem(key);
    if (!data) return null;

    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  },

  /**
   * Get all stored jobs (excluding old/completed ones)
   */
  getAll(): StoredJob[] {
    const jobs: StoredJob[] = [];
    const now = Date.now();

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith(STORAGE_KEY_PREFIX)) continue;

      const data = localStorage.getItem(key);
      if (!data) continue;

      try {
        const job: StoredJob = JSON.parse(data);

        // Skip jobs older than 24 hours
        if (now - job.startedAt > MAX_JOB_AGE_MS) {
          localStorage.removeItem(key);
          continue;
        }

        jobs.push(job);
      } catch {
        // Invalid JSON, remove it
        localStorage.removeItem(key);
      }
    }

    return jobs;
  },

  /**
   * Remove a job from storage
   */
  remove(jobId: string): void {
    const key = `${STORAGE_KEY_PREFIX}${jobId}`;
    localStorage.removeItem(key);
  },

  /**
   * Update job status
   */
  updateStatus(jobId: string, status: string): void {
    const job = this.get(jobId);
    if (job) {
      job.status = status;
      this.save(job);
    }
  },

  /**
   * Clear all jobs
   */
  clear(): void {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(STORAGE_KEY_PREFIX)) {
        keys.push(key);
      }
    }
    keys.forEach(key => localStorage.removeItem(key));
  }
};
```

---

### 2. Update Your Download Hook/Component

```typescript
// src/hooks/useDownloadManager.ts

import { useState, useEffect, useCallback } from 'react';
import { JobStorage } from '../utils/jobStorage';

interface Job {
  id: string;
  status: 'queued' | 'downloading' | 'paused' | 'merging' | 'done' | 'error' | 'canceled';
  progress: number;
  url: string;
  title: string;
  format: string;
  downloaded_bytes?: number;
  total_bytes?: number;
  speed_bps?: number;
  eta_seconds?: number;
  error?: string;
}

export const useDownloadManager = () => {
  const [jobs, setJobs] = useState<Map<string, Job>>(new Map());
  const [isRestoring, setIsRestoring] = useState(true);

  /**
   * Start a new download job
   */
  const startJob = async (url: string, format: string, title: string, ext: string) => {
    try {
      const response = await fetch('/jobs/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, format, title, ext })
      });

      if (!response.ok) throw new Error('Failed to start job');

      const job: Job = await response.json();

      // Save to localStorage
      JobStorage.save({
        id: job.id,
        url,
        title,
        format,
        startedAt: Date.now()
      });

      // Add to state
      setJobs(prev => new Map(prev).set(job.id, job));

      // Start polling
      pollJob(job.id);

      return job;
    } catch (error) {
      console.error('Failed to start job:', error);
      throw error;
    }
  };

  /**
   * Poll a job for status updates
   */
  const pollJob = useCallback(async (jobId: string) => {
    let attempts = 0;
    const maxAttempts = 1000; // ~8 minutes with 500ms interval

    const poll = async () => {
      try {
        const response = await fetch(`/jobs/${jobId}`);

        if (!response.ok) {
          // Job not found, probably expired
          JobStorage.remove(jobId);
          setJobs(prev => {
            const next = new Map(prev);
            next.delete(jobId);
            return next;
          });
          return;
        }

        const job: Job = await response.json();

        // Update storage
        JobStorage.updateStatus(jobId, job.status);

        // Update state
        setJobs(prev => new Map(prev).set(jobId, job));

        // Continue polling if not finished
        if (['queued', 'downloading', 'paused', 'merging'].includes(job.status)) {
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(poll, 500);
          }
        } else {
          // Job finished (done/error/canceled)
          // Remove from storage after 5 seconds so user can see final state
          setTimeout(() => {
            JobStorage.remove(jobId);
          }, 5000);
        }
      } catch (error) {
        console.error(`Failed to poll job ${jobId}:`, error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000); // Retry with longer interval on error
        }
      }
    };

    poll();
  }, []);

  /**
   * Restore jobs from localStorage on mount
   */
  useEffect(() => {
    const restoreJobs = async () => {
      const storedJobs = JobStorage.getAll();
      console.log(`Restoring ${storedJobs.length} jobs from localStorage`);

      for (const storedJob of storedJobs) {
        try {
          const response = await fetch(`/jobs/${storedJob.id}`);

          if (response.ok) {
            const job: Job = await response.json();
            setJobs(prev => new Map(prev).set(job.id, job));

            // Start polling if still active
            if (['queued', 'downloading', 'paused', 'merging'].includes(job.status)) {
              pollJob(job.id);
            } else if (['done', 'error', 'canceled'].includes(job.status)) {
              // Remove completed jobs after a delay
              setTimeout(() => JobStorage.remove(job.id), 5000);
            }
          } else {
            // Job not found on server, remove from storage
            JobStorage.remove(storedJob.id);
          }
        } catch (error) {
          console.error(`Failed to restore job ${storedJob.id}:`, error);
          JobStorage.remove(storedJob.id);
        }
      }

      setIsRestoring(false);
    };

    restoreJobs();
  }, []); // Run once on mount

  /**
   * Pause a job
   */
  const pauseJob = async (jobId: string) => {
    try {
      const response = await fetch(`/jobs/${jobId}/pause`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to pause job');

      const job: Job = await response.json();
      setJobs(prev => new Map(prev).set(jobId, job));
      JobStorage.updateStatus(jobId, 'paused');
    } catch (error) {
      console.error('Failed to pause job:', error);
      throw error;
    }
  };

  /**
   * Resume a job
   */
  const resumeJob = async (jobId: string) => {
    try {
      const response = await fetch(`/jobs/${jobId}/resume`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to resume job');

      const job: Job = await response.json();
      setJobs(prev => new Map(prev).set(jobId, job));
      JobStorage.updateStatus(jobId, 'queued');

      // Resume polling
      pollJob(jobId);
    } catch (error) {
      console.error('Failed to resume job:', error);
      throw error;
    }
  };

  /**
   * Cancel a job
   */
  const cancelJob = async (jobId: string) => {
    try {
      const response = await fetch(`/jobs/${jobId}/cancel`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to cancel job');

      const job: Job = await response.json();
      setJobs(prev => new Map(prev).set(jobId, job));

      // Remove from storage after a delay
      setTimeout(() => {
        JobStorage.remove(jobId);
        setJobs(prev => {
          const next = new Map(prev);
          next.delete(jobId);
          return next;
        });
      }, 3000);
    } catch (error) {
      console.error('Failed to cancel job:', error);
      throw error;
    }
  };

  /**
   * Download file
   */
  const downloadFile = (jobId: string, filename?: string) => {
    const url = `/jobs/${jobId}/file`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'download';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return {
    jobs: Array.from(jobs.values()),
    isRestoring,
    startJob,
    pauseJob,
    resumeJob,
    cancelJob,
    downloadFile,
  };
};
```

---

### 3. Use in Your Component

```tsx
// src/components/DownloadManager.tsx

import React from 'react';
import { useDownloadManager } from '../hooks/useDownloadManager';

export const DownloadManager: React.FC = () => {
  const {
    jobs,
    isRestoring,
    startJob,
    pauseJob,
    resumeJob,
    cancelJob,
    downloadFile,
  } = useDownloadManager();

  const handleStartDownload = async () => {
    try {
      await startJob(
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'best',
        'Test Video',
        'mp4'
      );
    } catch (error) {
      alert('Failed to start download');
    }
  };

  if (isRestoring) {
    return <div>Restoring downloads...</div>;
  }

  return (
    <div>
      <button onClick={handleStartDownload}>
        Start Download
      </button>

      <div>
        {jobs.map(job => (
          <div key={job.id} className="job-item">
            <h3>{job.title}</h3>
            <p>Status: {job.status}</p>
            <p>Progress: {(job.progress * 100).toFixed(1)}%</p>

            {job.status === 'downloading' && (
              <>
                <button onClick={() => pauseJob(job.id)}>Pause</button>
                <button onClick={() => cancelJob(job.id)}>Cancel</button>
              </>
            )}

            {job.status === 'paused' && (
              <>
                <button onClick={() => resumeJob(job.id)}>Resume</button>
                <button onClick={() => cancelJob(job.id)}>Cancel</button>
              </>
            )}

            {job.status === 'done' && (
              <button onClick={() => downloadFile(job.id, job.title)}>
                Download File
              </button>
            )}

            {job.status === 'error' && (
              <p className="error">Error: {job.error}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## Key Features

✅ **Automatic Restoration**: Jobs restore on page load
✅ **Auto-Cleanup**: Old jobs (24+ hours) automatically removed
✅ **Status Sync**: Job status synced between localStorage and server
✅ **Error Handling**: Gracefully handles expired or deleted jobs
✅ **Polling Management**: Automatic polling for active jobs
✅ **Memory Efficient**: Completed jobs removed from storage

---

## Testing

1. **Start a download** and note the progress
2. **Refresh the page** - download should still be there
3. **Close the tab** and reopen - download should restore
4. **Wait 24 hours** - old jobs should auto-cleanup
5. **Restart server** - completed downloads should restore (Celery mode)

---

## Notes

- Jobs are stored with a 24-hour expiry (matches backend Redis expiry)
- Completed jobs stay in UI for 5 seconds before being removed
- Invalid/corrupted localStorage entries are auto-cleaned
- Works for both Celery and threading modes
- Minimal performance impact (localStorage operations are fast)

---

## Alternative: Using React Query

If you're using React Query/TanStack Query:

```typescript
import { useQuery, useQueryClient } from '@tanstack/react-query';

const queryClient = useQueryClient();

// Enable persistence
import { persistQueryClient } from '@tanstack/react-query-persist-client'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'

const persister = createSyncStoragePersister({
  storage: window.localStorage,
});

persistQueryClient({
  queryClient,
  persister,
  maxAge: 24 * 60 * 60 * 1000, // 24 hours
});

// Then use queries as normal - they'll auto-persist!
```

This is simpler but requires adding React Query to your project.
