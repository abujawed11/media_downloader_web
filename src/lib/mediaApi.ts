import { z } from 'zod'
import { api } from './api'
import type { InfoResponse, DownloadJobDTO } from '../features/downloads/types'

const FormatSchema = z.object({
    format_id: z.string().nullable().optional(),   // <— changed
    format_string: z.string().min(1),              // <— new required
    label: z.string(),
    ext: z.string().optional(),
})

const InfoSchema = z.object({
    title: z.string(),
    thumbnail: z.string().optional(),
    duration: z.number().optional(),
    formats: z.array(FormatSchema),
})

const JobSchema = z.object({
    id: z.string(),
    url: z.string().url(),
    title: z.string().optional(),
    format_string: z.string(),
    ext: z.string().optional(),
    status: z.enum(['queued','downloading','paused','merging','done','error','canceled']),
    progress: z.number(),
    downloaded_bytes: z.number(),
    total_bytes: z.number().nullable().optional(),   // ← nullable
    speed_bps: z.number().nullable().optional(),     // ← nullable
    eta_seconds: z.number().nullable().optional(),   // ← nullable
    filename: z.string().nullable().optional(),      // ← nullable
    error: z.string().nullable().optional(),         // ← nullable
  })

export const mediaApi = {
    async info(url: string): Promise<InfoResponse> {
        const { data } = await api.post('/info', { url })

        // Normal path (backend with format_string)
        const parsed = InfoSchema.safeParse(data)
        if (parsed.success) return parsed.data

        // Fallback: adapt older backend that only returns format_id
        if (data?.formats?.length) {
            const adapted = {
                ...data,
                formats: data.formats.map((f: any) => ({
                    ...f,
                    format_string: f.format_string ?? String(f.format_id ?? ''),
                })),
            }
            const parsed2 = InfoSchema.safeParse(adapted)
            if (parsed2.success) return parsed2.data
        }

        throw new Error('Schema mismatch from /info')
    },


    async startJob(args: { url: string; format_string: string; title?: string; ext?: string }): Promise<DownloadJobDTO> {
        const { data } = await api.post('/jobs/start', { url: args.url, format: args.format_string, title: args.title, ext: args.ext })
        const parsed = JobSchema.parse(data)
        return parsed
    },
    async pauseJob(id: string) {
        const { data } = await api.post(`/jobs/${id}/pause`, {})
        return JobSchema.parse(data)
    },
    async resumeJob(id: string) {
        const { data } = await api.post(`/jobs/${id}/resume`, {})
        return JobSchema.parse(data)
    },
    async cancelJob(id: string) {
        const { data } = await api.post(`/jobs/${id}/cancel`, {})
        return JobSchema.parse(data)
    },
    async getJob(id: string) {
        const { data } = await api.get(`/jobs/${id}`)
        return JobSchema.parse(data)
    },
    async listJobs() {
        const { data } = await api.get('/jobs')
        return z.array(JobSchema).parse(data)
    },
    fileUrl(id: string) {
        // Use this href to download final file
        return `${api.defaults.baseURL}/jobs/${id}/file`
    },
}







