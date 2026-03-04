import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { getStorageSettings, setStorageType, type StorageType } from '../lib/settingsApi'

interface StorageOption {
  value: StorageType
  label: string
  description: string
  detail: string
  icon: string
}

const STORAGE_OPTIONS: StorageOption[] = [
  {
    value: 'local',
    label: 'Local Filesystem',
    description: 'Saves media directly on the server disk.',
    detail: 'Fastest option. No external service required.',
    icon: '💾',
  },
  {
    value: 'minio',
    label: 'MinIO',
    description: 'Local S3-compatible object storage.',
    detail: 'http://localhost:9000 · Console: http://localhost:9001',
    icon: '🗄️',
  },
  {
    value: 's3',
    label: 'Cloudflare R2',
    description: 'Cloud object storage via Cloudflare R2.',
    detail: 'Configured via S3_ENDPOINT_URL in .env',
    icon: '☁️',
  },
]

export default function Settings() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['settings', 'storage'],
    queryFn: getStorageSettings,
  })

  const mutation = useMutation({
    mutationFn: setStorageType,
    onSuccess: (updated) => {
      queryClient.setQueryData(['settings', 'storage'], updated)
      toast.success(`Storage switched to ${updated.storage_type}`)
    },
    onError: () => {
      toast.error('Failed to update storage setting')
    },
  })

  const active = data?.storage_type ?? 'local'

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-white/50 mt-1 text-sm">Configure where uploaded media is stored.</p>
      </div>

      {/* Storage Backend */}
      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-medium">Storage Backend</h2>
        <p className="text-white/50 text-sm">
          Choose where downloaded videos and thumbnails are stored. The setting takes effect on the
          next download.
        </p>

        <div className="space-y-3">
          {STORAGE_OPTIONS.map((opt) => {
            const isActive = active === opt.value
            const isPending = mutation.isPending && mutation.variables === opt.value

            return (
              <button
                key={opt.value}
                onClick={() => !isActive && mutation.mutate(opt.value)}
                disabled={isLoading || mutation.isPending}
                className={[
                  'w-full text-left rounded-xl border px-4 py-4 transition-all',
                  isActive
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/25 hover:bg-white/10',
                  mutation.isPending ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
                ].join(' ')}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{opt.icon}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{opt.label}</span>
                        {isActive && (
                          <span className="text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full">
                            Active
                          </span>
                        )}
                        {isPending && (
                          <span className="text-xs text-white/50">Saving…</span>
                        )}
                      </div>
                      <p className="text-sm text-white/60 mt-0.5">{opt.description}</p>
                      <p className="text-xs text-white/35 mt-0.5 font-mono">{opt.detail}</p>
                    </div>
                  </div>

                  <div
                    className={[
                      'w-5 h-5 rounded-full border-2 flex-shrink-0 transition-colors',
                      isActive ? 'border-blue-500 bg-blue-500' : 'border-white/30',
                    ].join(' ')}
                  >
                    {isActive && (
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-white" />
                      </div>
                    )}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </section>
    </div>
  )
}
