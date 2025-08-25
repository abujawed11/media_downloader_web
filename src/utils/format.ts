export function bytesHuman(n?: number | null) {
    if (n == null || n < 0) return '0 B'     // handles null/undefined
    const u = ['B','KB','MB','GB','TB']
    let i = 0, v = n
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++ }
    return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${u[i]}`
  }
  
  export function speedHuman(bps?: number | null) {
    if (bps == null || bps <= 0) return '—'
    return `${bytesHuman(bps)}/s`
  }
  
  export function etaHuman(sec?: number | null) {
    if (sec == null) return ''
    if (sec < 60) return `${sec}s`
    const m = Math.floor(sec / 60), s = sec % 60
    if (m < 60) return `${m}m ${s}s`
    const h = Math.floor(m / 60), m2 = m % 60
    return `${h}h ${m2}m`
  }
  