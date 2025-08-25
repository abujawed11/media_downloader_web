import { useState } from 'react'
import { useClipboardUrl } from '../hooks/useClipboardUrl'
import { useModal } from '../hooks/useModal'

export default function FloatingBubble() {
  const [drag, setDrag] = useState({ x: 16, y: 16 })
  const { readUrlFromClipboard } = useClipboardUrl()
  const { open } = useModal()

  async function handleClick() {
    const url = await readUrlFromClipboard()
    if (url) {
      open('downloadOptions', { url })
    } else {
      open('toast', { message: 'Clipboard does not contain a URL' })
    }
  }

  return (
    <button
      aria-label="Quick Download"
      onClick={handleClick}
      className="fixed bottom-4 right-4 z-50 size-14 rounded-full bg-yellow-400 text-black shadow-soft hover:brightness-95 active:scale-95"
      style={{ transform: `translate(${-drag.x}px, ${-drag.y}px)` }}
    >
      ⬇️
    </button>
  )
}
