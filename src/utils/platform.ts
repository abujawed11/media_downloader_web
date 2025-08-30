import type { Platform } from '../features/downloads/types'

export function detectPlatformFromUrl(url: string): Platform {
  const u = url.toLowerCase()
  
  // Major video platforms
  if (u.includes('youtube.com') || u.includes('youtu.be')) return 'youtube'
  if (u.includes('instagram.com')) return 'instagram'
  if (u.includes('facebook.com') || u.includes('fb.watch')) return 'facebook'
  if (u.includes('twitter.com') || u.includes('x.com')) return 'twitter'
  
  // Try to extract domain name for display
  try {
    const domain = new URL(url).hostname.replace('www.', '')
    return domain as Platform // Use domain as platform name
  } catch {
    return 'other'
  }
}
