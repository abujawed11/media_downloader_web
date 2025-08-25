export function isLikelyUrl(text: string) {
    try { new URL(text); return true } catch { return false }
  }
  
  export function useClipboardUrl() {
    async function readUrlFromClipboard(): Promise<string | null> {
      try {
        const text = await navigator.clipboard.readText()
        if (text && isLikelyUrl(text)) return text.trim()
      } catch { /* permissions or no clipboard */ }
      return null
    }
    return { readUrlFromClipboard }
  }
  