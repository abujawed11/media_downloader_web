import os, tempfile
from typing import Dict, List, Optional
import yt_dlp

COOKIES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "cookies")

def _cookies_for(url: str) -> Optional[str]:
    u = url.lower()
    for name, keys in {
        "youtube.txt": ["youtube.com", "youtu.be"],
        "instagram.txt": ["instagram.com"],
        "facebook.txt": ["facebook.com", "fb.watch"],
        "twitter.txt": ["twitter.com", "x.com"],
    }.items():
        if any(k in u for k in keys):
            path = os.path.join(COOKIES_DIR, name)
            return path if os.path.exists(path) else None
    return None

def extract_info(url: str) -> Dict:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "cachedir": False,
    }
    cookies = _cookies_for(url)
    if cookies:
        ydl_opts["cookiefile"] = cookies
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def select_thumbnail(meta: Dict) -> Optional[str]:
    if isinstance(meta.get("thumbnail"), str):
        return meta["thumbnail"]
    thumbs = meta.get("thumbnails") or []
    best = None
    for t in thumbs:
        if isinstance(t, dict) and t.get("url"):
            if best is None or (t.get("height") or 0) > (best.get("height") or 0):
                best = t
    return best.get("url") if best else None


def get_height(f: dict) -> Optional[int]:
    """Derive a numeric height from various fields used by different sites."""
    h = f.get("height")
    if isinstance(h, int):
        return h
    # resolution like "1280x720"
    res = f.get("resolution")
    if isinstance(res, str) and "x" in res:
        try:
            return int(res.split("x")[1])
        except Exception:
            pass
    # format_note like "sd", "hd", "1080p", "4k", "fhd", etc.
    note = (f.get("format_note") or "").lower()
    mapping = {
        "sd": 480, "hd": 720, "fhd": 1080, "full hd": 1080,
        "2k": 1440, "4k": 2160, "8k": 4320,
    }
    for k, v in mapping.items():
        if k in note:
            return v
    # also catch explicit numbers in note ("1080p")
    for cand in (4320, 2160, 1440, 1080, 720, 480, 360, 240):
        if f"{cand}" in note:
            return cand
    return None


def build_formats(info: Dict) -> List[Dict]:
    """
    Return clean options for ANY site:
      - Progressive if available
      - Else merged (best video-only + best audio) per height
      - One best audio at the end
    """
    fmts = info.get("formats") or []

    # best candidates per height
    best_prog_mp4 = {}
    best_prog_webm = {}
    best_vo_mp4 = {}
    best_vo_webm = {}

    best_audio_m4a = None
    best_audio_webm = None

    def better(a, b, key="tbr"):
        return (a or {}).get(key, 0) > (b or {}).get(key, 0)

    for f in fmts:
        ext = f.get("ext")
        v   = f.get("vcodec")
        a   = f.get("acodec")
        h   = get_height(f)
        # Track best audio
        if v == "none" and a != "none":
            if ext in ("m4a", "mp4"):
                if better(f, best_audio_m4a): best_audio_m4a = f
            elif ext in ("webm", "opus"):
                if better(f, best_audio_webm): best_audio_webm = f
            continue

        if v == "none":
            continue  # not a video track

        # Prefer H.264 when present for mp4
        vcodec = (v or "").lower()
        is_h264 = "avc1" in vcodec or "h264" in vcodec

        if h is not None:
            if a != "none":  # progressive
                if ext == "mp4":
                    cur = best_prog_mp4.get(h)
                    if not cur or better(f, cur) or (is_h264 and not ("avc1" in (cur.get("vcodec") or ""))):
                        best_prog_mp4[h] = f
                elif ext == "webm":
                    cur = best_prog_webm.get(h)
                    if not cur or better(f, cur):
                        best_prog_webm[h] = f
            else:  # video-only
                if ext == "mp4":
                    cur = best_vo_mp4.get(h)
                    if not cur or better(f, cur) or (is_h264 and not ("avc1" in (cur.get("vcodec") or ""))):
                        best_vo_mp4[h] = f
                elif ext == "webm":
                    cur = best_vo_webm.get(h)
                    if not cur or better(f, cur):
                        best_vo_webm[h] = f

    heights = sorted(set(
        list(best_prog_mp4.keys()) +
        list(best_prog_webm.keys()) +
        list(best_vo_mp4.keys()) +
        list(best_vo_webm.keys())
    ))

    out: List[Dict] = []

    for h in heights:
        # 1) progressive mp4 (ideal)
        if h in best_prog_mp4:
            f = best_prog_mp4[h]
            out.append({
                "format_id": str(f.get("format_id")),
                "format_string": str(f.get("format_id")),
                "label": f"{h}p mp4",
                "ext": "mp4",
            })
            continue
        # 2) merged mp4: video-only mp4 + best audio (m4a preferred)
        if h in best_vo_mp4 and (best_audio_m4a or best_audio_webm):
            v = best_vo_mp4[h]
            a = best_audio_m4a or best_audio_webm
            out.append({
                "format_id": None,
                "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
                "label": f"{h}p mp4 (merge)",
                "ext": "mp4",
            })
            continue
        # 3) progressive webm
        if h in best_prog_webm:
            f = best_prog_webm[h]
            out.append({
                "format_id": str(f.get("format_id")),
                "format_string": str(f.get("format_id")),
                "label": f"{h}p webm",
                "ext": "webm",
            })
            continue
        # 4) merged webm
        if h in best_vo_webm and best_audio_webm:
            v = best_vo_webm[h]
            a = best_audio_webm
            out.append({
                "format_id": None,
                "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
                "label": f"{h}p webm (merge)",
                "ext": "webm",
            })

    # One best audio option at the end
    if best_audio_m4a:
        out.append({
            "format_id": str(best_audio_m4a.get("format_id")),
            "format_string": str(best_audio_m4a.get("format_id")),
            "label": "Audio m4a",
            "ext": "m4a",
        })
    elif best_audio_webm:
        out.append({
            "format_id": str(best_audio_webm.get("format_id")),
            "format_string": str(best_audio_webm.get("format_id")),
            "label": "Audio webm",
            "ext": "webm",
        })

    return out


def download_to_temp(url: str, format_string: str) -> str:
    tmpdir = tempfile.mkdtemp(prefix="md_")
    outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": format_string,               # can be "137+140" or "18"
        "outtmpl": outtmpl,
        "noprogress": True,
        "nocheckcertificate": True,
        "cachedir": False,
        "quiet": True,
        # Let yt-dlp/ffmpeg pick the right container automatically:
        # "merge_output_format": "mp4",  # uncomment to force mp4 when possible
    }
    cookies = _cookies_for(url)
    if cookies:
        ydl_opts["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        if "_filename" in result:
            return result["_filename"]
        entries = result.get("entries") or []
        if entries and "_filename" in entries[0]:
            return entries[0]["_filename"]
        for f in os.listdir(tmpdir):
            p = os.path.join(tmpdir, f)
            if os.path.isfile(p):
                return p
    raise RuntimeError("Download failed: file not found")
