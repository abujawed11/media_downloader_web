type ModalName = 'downloadOptions' | 'toast'
type ModalPayload = Record<string, unknown> | undefined

let listeners: Array<(name: ModalName | null, payload?: ModalPayload) => void> = []

export function useModal() {
  function open(name: ModalName, payload?: ModalPayload) {
    listeners.forEach(l => l(name, payload))
  }
  function close() {
    listeners.forEach(l => l(null))
  }
  function subscribe(cb: (name: ModalName | null, payload?: ModalPayload) => void) {
    listeners.push(cb)
    return () => { listeners = listeners.filter(x => x !== cb) }
  }
  return { open, close, subscribe }
}
