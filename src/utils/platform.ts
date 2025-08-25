import type { Platform } from '../features/downloads/types'

export function detectPlatformFromUrl(url: string): Platform {
  const u = url.toLowerCase()
  if (u.includes('youtube.com') || u.includes('youtu.be')) return 'youtube'
  if (u.includes('instagram.com')) return 'instagram'
  if (u.includes('facebook.com') || u.includes('fb.watch')) return 'facebook'
  if (u.includes('twitter.com') || u.includes('x.com')) return 'twitter'
  return 'other'
}
