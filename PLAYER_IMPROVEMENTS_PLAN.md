# Player & Library Improvements — Implementation Plan

## Overview

Three major areas of work:
1. **PlayerContext + Floating Mini Player** — foundation layer
2. **Custom Professional Video Player** — replaces native `<video controls>`
3. **Library Enhancements** — list view, skeletons, bulk delete

---

## Phase 1 — PlayerContext + Floating Mini Player

### Goal
User clicks Minimize on the full player → small floating video appears bottom-right → keeps
playing while they browse anywhere in the app → click it to jump back → close to dismiss.

### 1.1 — `src/context/PlayerContext.tsx` (new file)

Holds the global player state that both the full Watch page and the mini player share.

```ts
interface PlayerState {
  mediaId: string | null        // current media id
  title: string                 // video title (for mini player label)
  streamUrl: string             // /api/library/:id/stream
  currentTime: number           // synced every second
  isPlaying: boolean
  isMini: boolean               // false = full page, true = floating mini
}
```

Key actions exposed via context:
- `openPlayer(mediaId, title, streamUrl)` — called by Watch page on mount
- `minimize()` — called by the Minimize button in the player
- `restore()` — called when user clicks the mini player (navigates back to /watch/:id)
- `close()` — called by the X button on mini player
- `syncTime(t)` — called every second by whichever player is active

### 1.2 — `src/components/MiniPlayer.tsx` (new file)

Fixed-position component, always rendered inside `App.tsx`, only visible when `isMini = true`.

Layout (320×180 video + 40px title bar):
```
┌──────────────────────────────┐
│  video (320×180)         [✕] │  ← close button top-right
│  ▶  ████████████████████    │  ← play/pause overlay on hover
└──────────────────────────────┘
│ Video title here...          │  ← title bar below video
└──────────────────────────────┘
```

Behaviour:
- `<video>` element with `src={streamUrl}` — NOT the same element as the full player
- On mount: set `currentTime` from context, call `play()`
- Every second: call `syncTime(video.currentTime)`
- Click on video area → `restore()` → `navigate('/watch/' + mediaId)`
- Slide-in animation: `translate-y-full` → `translate-y-0` (CSS transition)
- Position: `fixed bottom-4 right-4 z-50`

### 1.3 — Changes to `src/App.tsx`

Wrap everything in `PlayerProvider`, render `<MiniPlayer />` alongside `<Outlet />`:

```tsx
<PlayerProvider>
  <div className="min-h-dvh text-white">
    <Header />
    <main className="container mx-auto px-6 py-8">
      <Outlet />
    </main>
    <MiniPlayer />          {/* ← new */}
    <DownloadOptionsModal />
  </div>
</PlayerProvider>
```

### 1.4 — Changes to `src/pages/Watch.tsx`

On mount: call `openPlayer(id, media.title, streamUrl)`.
When `isMini` becomes true (user clicked minimize): the Watch page should detect this and
navigate(-1) automatically (or show a "minimized" placeholder instead of the video).

The Minimize button lives in the custom player controls (built in Phase 2).

---

## Phase 2 — Custom Professional Video Player

### Goal
Replace `<video controls>` with a fully custom control bar. Dark cinematic look.
Auto-hide controls after 3s idle. Keyboard shortcuts. Loading spinner.

### 2.1 — `src/components/VideoPlayer.tsx` (new file)

Self-contained component. Props:
```ts
interface VideoPlayerProps {
  src: string
  poster?: string
  title?: string
  onTimeUpdate?: (t: number) => void     // for watch-progress saving
  initialTime?: number                   // restore saved position
  onMinimize?: () => void                // triggers mini player
}
```

Internal state managed with `useRef` + `useState`:
- `playing`, `muted`, `volume` (0–1), `currentTime`, `duration`
- `buffered` (for buffer bar), `waiting` (spinner), `fullscreen`
- `controlsVisible` (auto-hide), `idleTimer` ref

#### Control Bar Layout
```
[gradient overlay — bottom 96px]
┌────────────────────────────────────────────────────────────────┐
│ [Title top-left when controls visible]                         │
│                                                                │
│ [spinner if buffering]                                         │
│                                                                │
│ ─────────────────── SEEK BAR ──────────────────────────────── │
│  [buffer track (gray)] [played track (white)] [thumb]          │
│  hover → shows time tooltip above cursor                       │
│                                                                │
│ [▶/⏸]  [0:45 / 23:33]          [🔊──] [⛶ minimize] [⛶ full] │
└────────────────────────────────────────────────────────────────┘
```

#### Seek Bar Details
- Three layers: total (bg), buffered (zinc-600), played (white)
- Hover: show time tooltip above cursor (calculate from mouse X / bar width × duration)
- Click or drag to seek

#### Volume Control
- Speaker icon (click to mute/unmute)
- Horizontal slider (0–100%), hidden on mobile
- Remembers last volume when unmuted

#### Auto-hide Logic
- Mouse move / click inside player → show controls, reset 3s timer
- After 3s idle → fade controls out (opacity-0 transition-opacity duration-300)
- While paused → controls always visible

#### Loading Spinner
- Show when `video.waiting = true` (buffering mid-playback)
- Centered, animated ring, semi-transparent bg

### 2.2 — Keyboard Shortcuts

Add `keydown` listener on the player container (or window when player is focused).

| Key | Action |
|-----|--------|
| `Space` / `K` | Play / Pause |
| `←` | Seek −5s |
| `→` | Seek +5s |
| `↑` | Volume +10% |
| `↓` | Volume −10% |
| `M` | Mute toggle |
| `F` | Fullscreen toggle |

### 2.3 — Fullscreen

Use `element.requestFullscreen()` on the player container div (not just the video).
This ensures custom controls are visible in fullscreen too.
Listen to `document.fullscreenchange` to sync the fullscreen state.

### 2.4 — Visual Style

```
- Player bg: black
- Gradient overlay: linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 40%)
- Controls bar: no extra bg — gradient provides contrast
- Seek bar height: 4px, expands to 6px on hover
- All buttons: text-white/80 hover:text-white, size-5 icons
- Duration text: font-mono text-sm text-white/90
- Title: text-sm font-medium text-white/90 truncate max-w-[50%]
```

### 2.5 — Update `src/pages/Watch.tsx`

Replace native `<video controls ...>` with `<VideoPlayer>`:
```tsx
<VideoPlayer
  src={streamUrl}
  poster={resolveThumbnail(media.thumbnail_url)}
  title={media.title}
  initialTime={savedProgress?.current_time}
  onTimeUpdate={(t) => { /* debounced save to API */ }}
  onMinimize={() => minimize()}   // from PlayerContext
/>
```

Remove the existing `videoRef`, progress timer, `loadedmetadata` listener — all move inside
`VideoPlayer`.

---

## Phase 3 — Library Enhancements

### 3.1 — Skeleton Loaders

Replace the `<Loader2>` spinner in `Library.tsx` with skeleton cards.

`src/components/SkeletonCard.tsx` (new file):
```tsx
// Mimics MediaCard shape — same aspect-video ratio, same info rows
// Uses animate-pulse bg-zinc-800 blocks
```

Show a grid of 12 skeleton cards while `isLoading = true`.

### 3.2 — Grid / List View Toggle

Add a toggle button (Grid icon / List icon) in the Library filter bar.
State: `viewMode: 'grid' | 'list'` — persisted to `localStorage`.

**List row layout** (for list view):
```
[thumbnail 120×68] [title + uploader]  [resolution] [size] [date] [▶ play] [⬇ download] [🗑 delete]
```

No new backend needed — same `items` array, different render.

`src/components/MediaListRow.tsx` (new file) — the list-view equivalent of `MediaCard`.

### 3.3 — Bulk Select + Delete

**Frontend changes (`Library.tsx`):**
- `selectMode: boolean` state — toggled by a "Select" button in the filter bar
- `selectedIds: Set<string>` state
- When `selectMode = true`: MediaCard shows a checkbox overlay (top-left)
- Sticky action bar at bottom appears when `selectedIds.size > 0`:
  ```
  [✕ Cancel]  [☐ Select All]  [3 selected]  [🗑 Delete Selected]
  ```
- Confirmation toast before bulk delete

**Backend change (`server/app/routers/media_library.py`):**
Add one new endpoint:
```
DELETE /api/library/bulk
Body: { ids: string[] }
Response: { deleted: number }
```
Loops through ids, calls existing delete logic for each.

### 3.4 — Per-Card Hover Overlay (minor)

Already partially in `MediaCard.tsx` (play overlay on hover).
Add resolution + date-added text to the hover overlay:
```
[▶]
720p · Added Jan 5
```
Small change inside the existing hover overlay div.

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `src/context/PlayerContext.tsx` | Global player state (mini/full sync) |
| `src/components/MiniPlayer.tsx` | Floating bottom-right mini player |
| `src/components/VideoPlayer.tsx` | Custom player with full controls |
| `src/components/SkeletonCard.tsx` | Skeleton loader for library grid |
| `src/components/MediaListRow.tsx` | List-view row for library |

### Modified Files
| File | Change |
|------|--------|
| `src/App.tsx` | Add `PlayerProvider`, `<MiniPlayer />` |
| `src/pages/Watch.tsx` | Use `<VideoPlayer>`, connect to PlayerContext |
| `src/pages/Library.tsx` | Skeleton loaders, view toggle, bulk select |
| `src/components/MediaCard.tsx` | Checkbox overlay (select mode), hover overlay text |
| `server/app/routers/media_library.py` | Add `DELETE /api/library/bulk` endpoint |

---

## Implementation Order

1. `PlayerContext.tsx` — no UI, just state
2. `MiniPlayer.tsx` — floating player (uses native `<video>` internally)
3. Wire context into `App.tsx` + `Watch.tsx` (minimize works end-to-end)
4. `VideoPlayer.tsx` — custom controls (largest single task)
5. `SkeletonCard.tsx` + wire into `Library.tsx`
6. Grid/List toggle + `MediaListRow.tsx`
7. Bulk select/delete (frontend + backend endpoint)
8. Per-card hover overlay tweak

---

## Notes

- The mini player uses its **own** `<video>` element — not the same DOM node as the full player.
  Time is synced via context (close enough; no frame-perfect sync needed).
- No external video player library needed — pure HTML5 Video API.
- The `VideoPlayer` component is fully self-contained and reusable (could be used in mini
  player too in the future).
- Bulk delete backend loops sequentially (not parallel) to avoid hammering storage.
