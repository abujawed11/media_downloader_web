import { create } from 'zustand'
import type { DownloadJobDTO } from './types'

type State = {
  jobs: DownloadJobDTO[]
}

type Actions = {
  /** Insert new job or merge fields into an existing one (by id). */
  upsertJob: (job: DownloadJobDTO) => void
  /** Replace the whole list (e.g., initial load). */
  setJobs: (jobs: DownloadJobDTO[]) => void
  /** Remove a job (e.g., after user clears). */
  removeJob: (id: string) => void
  /** Clear everything (optional). */
  reset: () => void
}

export const useDownloads = create<State & Actions>((set) => ({
  jobs: [],

  upsertJob: (job) =>
    set((s) => {
      const i = s.jobs.findIndex((j) => j.id === job.id)
      if (i === -1) {
        // newest first
        return { jobs: [job, ...s.jobs] }
      }
      const next = s.jobs.slice()
      // merge so we don’t lose client-only fields like label/platform
      next[i] = { ...next[i], ...job }
      return { jobs: next }
    }),

  setJobs: (jobs) => set({ jobs }),

  removeJob: (id) =>
    set((s) => ({ jobs: s.jobs.filter((j) => j.id !== id) })),

  reset: () => set({ jobs: [] }),
}))
