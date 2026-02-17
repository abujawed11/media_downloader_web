# import os, tempfile
# from typing import Dict, List, Optional
# import yt_dlp

# COOKIES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "cookies")

# def _cookies_for(url: str) -> Optional[str]:
#     u = url.lower()
#     for name, keys in {
#         "youtube.txt": ["youtube.com", "youtu.be"],
#         "instagram.txt": ["instagram.com"],
#         "facebook.txt": ["facebook.com", "fb.watch"],
#         "twitter.txt": ["twitter.com", "x.com"],
#     }.items():
#         if any(k in u for k in keys):
#             path = os.path.join(COOKIES_DIR, name)
#             return path if os.path.exists(path) else None
#     return None

# def extract_info(url: str) -> Dict:
#     import time
#     start_time = time.time()
#     ydl_opts = {
#         "quiet": True,
#         "skip_download": True,
#         "nocheckcertificate": True,
#         "cachedir": False,
#     }
#     cookies = _cookies_for(url)
#     if cookies:
#         ydl_opts["cookiefile"] = cookies
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         result = ydl.extract_info(url, download=False)
#         end_time = time.time()
#         print(f"[PERF] yt-dlp extraction took {end_time - start_time:.2f} seconds")
#         return result

# def select_thumbnail(meta: Dict) -> Optional[str]:
#     if isinstance(meta.get("thumbnail"), str):
#         return meta["thumbnail"]
#     thumbs = meta.get("thumbnails") or []
#     best = None
#     for t in thumbs:
#         if isinstance(t, dict) and t.get("url"):
#             if best is None or (t.get("height") or 0) > (best.get("height") or 0):
#                 best = t
#     return best.get("url") if best else None


# def bytes_human(size_bytes: Optional[int]) -> str:
#     """Convert bytes to human readable format"""
#     if not size_bytes:
#         return ""
    
#     for unit in ['B', 'KB', 'MB', 'GB']:
#         if size_bytes < 1024.0:
#             return f"{size_bytes:.1f} {unit}" if size_bytes % 1 else f"{int(size_bytes)} {unit}"
#         size_bytes /= 1024.0
#     return f"{size_bytes:.1f} TB"


# def get_height(f: dict) -> Optional[int]:
#     """Derive a numeric height from various fields used by different sites."""
#     h = f.get("height")
#     if isinstance(h, int):
#         return h
#     # resolution like "1280x720"
#     res = f.get("resolution")
#     if isinstance(res, str) and "x" in res:
#         try:
#             return int(res.split("x")[1])
#         except Exception:
#             pass
#     # format_note like "sd", "hd", "1080p", "4k", "fhd", etc.
#     note = (f.get("format_note") or "").lower()
#     mapping = {
#         "sd": 480, "hd": 720, "fhd": 1080, "full hd": 1080,
#         "2k": 1440, "4k": 2160, "8k": 4320,
#     }
#     for k, v in mapping.items():
#         if k in note:
#             return v
#     # also catch explicit numbers in note ("1080p")
#     for cand in (4320, 2160, 1440, 1080, 720, 480, 360, 240):
#         if f"{cand}" in note:
#             return cand
#     return None


# def build_formats(info: Dict) -> List[Dict]:
#     """
#     Return clean options for ANY site:
#       - Progressive if available
#       - Else merged (best video-only + best audio) per height
#       - Multiple audio language options when available
#     """
#     fmts = info.get("formats") or []

#     # best candidates per height
#     best_prog_mp4 = {}
#     best_prog_webm = {}
#     best_vo_mp4 = {}
#     best_vo_webm = {}

#     # Track best audio by language
#     best_audio_by_lang = {}  # lang -> {m4a: format, webm: format}
#     best_audio_m4a = None
#     best_audio_webm = None

#     def better(a, b, key="tbr"):
#         return (a or {}).get(key, 0) > (b or {}).get(key, 0)

#     for f in fmts:
#         ext = f.get("ext")
#         v   = f.get("vcodec")
#         a   = f.get("acodec")
#         h   = get_height(f)
#         # Track best audio by language
#         if v == "none" and a != "none":
#             lang = f.get("language") or f.get("lang") or "unknown"
            
#             if lang not in best_audio_by_lang:
#                 best_audio_by_lang[lang] = {"m4a": None, "webm": None}
            
#             if ext in ("m4a", "mp4"):
#                 if better(f, best_audio_by_lang[lang]["m4a"]): 
#                     best_audio_by_lang[lang]["m4a"] = f
#                 if better(f, best_audio_m4a): best_audio_m4a = f
#             elif ext in ("webm", "opus"):
#                 if better(f, best_audio_by_lang[lang]["webm"]): 
#                     best_audio_by_lang[lang]["webm"] = f
#                 if better(f, best_audio_webm): best_audio_webm = f
#             continue

#         if v == "none":
#             continue  # not a video track

#         # Prefer H.264 when present for mp4
#         vcodec = (v or "").lower()
#         is_h264 = "avc1" in vcodec or "h264" in vcodec

#         if h is not None:
#             if a != "none":  # progressive
#                 if ext == "mp4":
#                     cur = best_prog_mp4.get(h)
#                     if not cur or better(f, cur) or (is_h264 and not ("avc1" in (cur.get("vcodec") or ""))):
#                         best_prog_mp4[h] = f
#                 elif ext == "webm":
#                     cur = best_prog_webm.get(h)
#                     if not cur or better(f, cur):
#                         best_prog_webm[h] = f
#             else:  # video-only
#                 if ext == "mp4":
#                     cur = best_vo_mp4.get(h)
#                     if not cur or better(f, cur) or (is_h264 and not ("avc1" in (cur.get("vcodec") or ""))):
#                         best_vo_mp4[h] = f
#                 elif ext == "webm":
#                     cur = best_vo_webm.get(h)
#                     if not cur or better(f, cur):
#                         best_vo_webm[h] = f

#     heights = sorted(set(
#         list(best_prog_mp4.keys()) +
#         list(best_prog_webm.keys()) +
#         list(best_vo_mp4.keys()) +
#         list(best_vo_webm.keys())
#     ))

#     out: List[Dict] = []

#     for h in heights:
#         # 1) progressive mp4 (ideal)
#         if h in best_prog_mp4:
#             f = best_prog_mp4[h]
#             out.append({
#                 "format_id": str(f.get("format_id")),
#                 "format_string": str(f.get("format_id")),
#                 "label": f"{h}p mp4",
#                 "ext": "mp4",
#                 "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#             })
#             continue
#         # 2) merged mp4: video-only mp4 + best audio (m4a preferred)
#         if h in best_vo_mp4 and (best_audio_m4a or best_audio_webm):
#             v = best_vo_mp4[h]
            
#             # If multiple languages available, create options for each
#             if len(best_audio_by_lang) > 1:
#                 for lang, audio_formats in best_audio_by_lang.items():
#                     a = audio_formats["m4a"] or audio_formats["webm"]
#                     if a:
#                         lang_label = f" [{lang}]" if lang != "unknown" else ""
#                         # Estimate combined size (video + audio)
#                         v_size = v.get("filesize") or v.get("filesize_approx") or 0
#                         a_size = a.get("filesize") or a.get("filesize_approx") or 0
#                         combined_size = v_size + a_size if v_size and a_size else None
#                         out.append({
#                             "format_id": None,
#                             "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
#                             "label": f"{h}p mp4{lang_label}",
#                             "ext": "mp4",
#                             "filesize": bytes_human(combined_size),
#                         })
#             else:
#                 # Single language - use default behavior
#                 a = best_audio_m4a or best_audio_webm
#                 v_size = v.get("filesize") or v.get("filesize_approx") or 0
#                 a_size = a.get("filesize") or a.get("filesize_approx") or 0
#                 combined_size = v_size + a_size if v_size and a_size else None
#                 out.append({
#                     "format_id": None,
#                     "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
#                     "label": f"{h}p mp4",
#                     "ext": "mp4",
#                     "filesize": bytes_human(combined_size),
#                 })
#             continue
#         # 3) progressive webm
#         if h in best_prog_webm:
#             f = best_prog_webm[h]
#             out.append({
#                 "format_id": str(f.get("format_id")),
#                 "format_string": str(f.get("format_id")),
#                 "label": f"{h}p webm",
#                 "ext": "webm",
#                 "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#             })
#             continue
#         # 4) merged webm
#         if h in best_vo_webm and best_audio_webm:
#             v = best_vo_webm[h]
#             a = best_audio_webm
#             v_size = v.get("filesize") or v.get("filesize_approx") or 0
#             a_size = a.get("filesize") or a.get("filesize_approx") or 0
#             combined_size = v_size + a_size if v_size and a_size else None
#             out.append({
#                 "format_id": None,
#                 "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
#                 "label": f"{h}p webm (merge)",
#                 "ext": "webm",
#                 "filesize": bytes_human(combined_size),
#             })

#     # Audio-only options for each language
#     if len(best_audio_by_lang) > 1:
#         for lang, audio_formats in best_audio_by_lang.items():
#             lang_label = f" [{lang}]" if lang != "unknown" else ""
#             if audio_formats["m4a"]:
#                 f = audio_formats["m4a"]
#                 out.append({
#                     "format_id": str(f.get("format_id")),
#                     "format_string": str(f.get("format_id")),
#                     "label": f"Audio m4a{lang_label}",
#                     "ext": "m4a",
#                     "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#                 })
#             elif audio_formats["webm"]:
#                 f = audio_formats["webm"]
#                 out.append({
#                     "format_id": str(f.get("format_id")),
#                     "format_string": str(f.get("format_id")),
#                     "label": f"Audio webm{lang_label}",
#                     "ext": "webm",
#                     "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#                 })
#     else:
#         # Single language - use default behavior
#         if best_audio_m4a:
#             out.append({
#                 "format_id": str(best_audio_m4a.get("format_id")),
#                 "format_string": str(best_audio_m4a.get("format_id")),
#                 "label": "Audio m4a",
#                 "ext": "m4a",
#                 "filesize": bytes_human(best_audio_m4a.get("filesize") or best_audio_m4a.get("filesize_approx")),
#             })
#         elif best_audio_webm:
#             out.append({
#                 "format_id": str(best_audio_webm.get("format_id")),
#                 "format_string": str(best_audio_webm.get("format_id")),
#                 "label": "Audio webm",
#                 "ext": "webm",
#                 "filesize": bytes_human(best_audio_webm.get("filesize") or best_audio_webm.get("filesize_approx")),
#             })

#     return out


# def download_to_temp(url: str, format_string: str) -> str:
#     tmpdir = tempfile.mkdtemp(prefix="md_")
#     outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

#     ydl_opts = {
#         "format": format_string,               # can be "137+140" or "18"
#         "outtmpl": outtmpl,
#         "noprogress": True,
#         "nocheckcertificate": True,
#         "cachedir": False,
#         "quiet": True,
#         # Let yt-dlp/ffmpeg pick the right container automatically:
#         # "merge_output_format": "mp4",  # uncomment to force mp4 when possible
#     }
#     cookies = _cookies_for(url)
#     if cookies:
#         ydl_opts["cookiefile"] = cookies

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         result = ydl.extract_info(url, download=True)
#         if "_filename" in result:
#             return result["_filename"]
#         entries = result.get("entries") or []
#         if entries and "_filename" in entries[0]:
#             return entries[0]["_filename"]
#         for f in os.listdir(tmpdir):
#             p = os.path.join(tmpdir, f)
#             if os.path.isfile(p):
#                 return p
#     raise RuntimeError("Download failed: file not found")





# ytdlp_service.py
import os
import tempfile
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import yt_dlp

# Folder where cookie files (youtube.txt, etc.) live
COOKIES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "cookies")


# --------------------------- Cookies ---------------------------

def _cookies_for(url: str) -> Optional[str]:
    u = url.lower()
    for name, keys in {
        "youtube.txt":   ["youtube.com", "youtu.be"],
        "instagram.txt": ["instagram.com"],
        "facebook.txt":  ["facebook.com", "fb.watch", "facebook.com/share"],
        "twitter.txt":   ["twitter.com", "x.com"],
    }.items():
        if any(k in u for k in keys):
            path = os.path.join(COOKIES_DIR, name)
            return path if os.path.exists(path) else None
    return None


# --------------------------- URL normalization (YouTube: single video only) ---------------------------

def _normalize_youtube_url(url: str) -> str:
    """
    If a YouTube URL contains playlist context (&list=...&index=...), normalize it to a
    single-video watch URL so yt-dlp won't enumerate the whole playlist.
    """
    u = urlparse(url)
    host = (u.netloc or "").lower()
    if "youtube.com" in host or "youtu.be" in host:
        q = parse_qs(u.query)
        vid = None
        if "v" in q and q["v"]:
            vid = q["v"][0]
        elif host.endswith("youtu.be"):
            # short link form: https://youtu.be/VIDEO_ID?t=123
            vid = u.path.lstrip("/").split("/")[0] or None
        if vid:
            clean_q = urlencode({"v": vid})
            return urlunparse(("https", "www.youtube.com", "/watch", "", clean_q, ""))
    return url


# --------------------------- Common yt-dlp options ---------------------------

def _base_ydl_opts(skip_download: bool = True, url: str = None) -> Dict:
    """
    Reasonable defaults that:
      - avoid playlist enumeration
      - reduce stalls/timeouts in VMs/Wi-Fi
      - behave better against throttling
    """
    opts = {
        "quiet": True,
        "skip_download": skip_download,
        "nocheckcertificate": True,
        "cachedir": False,

        # Force single video behavior:
        "noplaylist": True,
        "playlist_items": "1",

        # Networking robustness:
        "socket_timeout": 30,  # Increased for Facebook
        "retries": 3,          # Increased for Facebook
        "source_address": "0.0.0.0",   # prefer IPv4 paths
        
        # JavaScript runtime for YouTube signature decryption
        # "javascript_runtimes": ["node", "javascript"],

        # Better User-Agent for Facebook:
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    }
    
    # Facebook-specific configuration
    if url and "facebook.com" in url.lower():
        opts.update({
            # Facebook needs these for new URL formats
            "extractor_args": {
                "facebook": {
                    "api_version": "v17.0",
                }
            },
            "socket_timeout": 45,  # Facebook can be slow
            "retries": 5,
        })
    
    return opts


# --------------------------- Public API ---------------------------

def extract_info(url: str) -> Dict:
    """
    Extract metadata for a single video (fast), even if the original URL was a playlist-y watch URL.
    """
    import time
    start_time = time.time()

    # Normalize YT URLs so &list=... doesn't slow things down
    url = _normalize_youtube_url(url)

    ydl_opts = _base_ydl_opts(skip_download=True, url=url)
    cookies = _cookies_for(url)
    if cookies:
        ydl_opts["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)
        print(f"[PERF] yt-dlp extraction took {time.time() - start_time:.2f} seconds")
        return result


# def download_to_temp(url: str, format_string: str) -> str:
#     """
#     Download the chosen format to a temp dir and return the file path.
#     format_string can be progressive (e.g., "18") or merged (e.g., "137+140").
#     """
#     tmpdir = tempfile.mkdtemp(prefix="md_")
#     outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

#     # Normalize first so we don't accidentally start a full playlist download

#      # Build a resilient format selector:
#     #  - try the exact user's choice first (e.g. "137+140")
#     #  - then generic bestvideo+bestaudio
#     #  - then best progressive
#     url = _normalize_youtube_url(url)

#     safe_format = f"({format_string})/bv*+ba/best"

#     ydl_opts = _base_ydl_opts(skip_download=False)
#     ydl_opts.update({
#         "format": format_string,
#         "outtmpl": outtmpl,
#         "noprogress": True,
#         "quiet": True,
#         # Let yt-dlp/ffmpeg pick the container automatically.
#         # Uncomment to force mp4 when possible:
#         # "merge_output_format": "mp4",
#     })

#     cookies = _cookies_for(url)
#     if cookies:
#         ydl_opts["cookiefile"] = cookies

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         result = ydl.extract_info(url, download=True)
#         # Single entry
#         if "_filename" in result:
#             return result["_filename"]
#         # Playlist-y structures (we forced playlist_items=1 but just in case):
#         entries = result.get("entries") or []
#         if entries and "_filename" in entries[0]:
#             return entries[0]["_filename"]
#         # Fallback: return first file created in tmpdir
#         for f in os.listdir(tmpdir):
#             p = os.path.join(tmpdir, f)
#             if os.path.isfile(p):
#                 return p
#     raise RuntimeError("Download failed: file not found")


# def download_to_temp(url: str, format_string: str) -> str:
#     tmpdir = tempfile.mkdtemp(prefix="md_")
#     outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

#     # Normalize first so we don't accidentally start a full playlist download
#     url = _normalize_youtube_url(url)

#     # Build a resilient format selector:
#     #  - try the exact user's choice first (e.g. "137+140")
#     #  - then generic bestvideo+bestaudio
#     #  - then best progressive
#     safe_format = f"({format_string})/bv*+ba/best"

#     ydl_opts = _base_ydl_opts(skip_download=False)
#     ydl_opts.update({
#         "format": safe_format,
#         "outtmpl": outtmpl,
#         "noprogress": True,
#         "quiet": True,
#         # If you want final container mp4 when possible:
#         "merge_output_format": "mp4",
#     })

#     cookies = _cookies_for(url)
#     if cookies:
#         ydl_opts["cookiefile"] = cookies

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         result = ydl.extract_info(url, download=True)
#         if "_filename" in result:
#             return result["_filename"]
#         entries = result.get("entries") or []
#         if entries and "_filename" in entries[0]:
#             return entries[0]["_filename"]
#         for f in os.listdir(tmpdir):
#             p = os.path.join(tmpdir, f)
#             if os.path.isfile(p):
#                 return p
#     raise RuntimeError("Download failed: file not found")


def download_to_temp(url: str, format_string: str) -> str:
    import yt_dlp
    tmpdir = tempfile.mkdtemp(prefix="md_")
    outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

    # Normalize first so we don't accidentally start a full playlist download
    url = _normalize_youtube_url(url)

    def run_with_format(fmt_expr: str) -> Optional[str]:
        ydl_opts = _base_ydl_opts(skip_download=False, url=url)
        ydl_opts.update({
            "format": fmt_expr,
            "outtmpl": outtmpl,
            "noprogress": True,
            "quiet": True,
            # Prefer mp4 when a merge happens
            "merge_output_format": "mp4",
        })
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
        return None

    # 1) Try the user-provided expression first
    try:
        p = run_with_format(format_string)
        if p:
            return p
    except yt_dlp.utils.DownloadError as e:
        # Known: “Requested format is not available …”
        print(f"[WARN] primary format failed: {e}")

    # 2) Fallbacks (very resilient)
    for fallback in [
        "bv*+ba/best",                                 # merged best
        "best",                                        # any best
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",  # mp4-ish merged
    ]:
        try:
            p = run_with_format(fallback)
            if p:
                return p
        except yt_dlp.utils.DownloadError as e:
            print(f"[WARN] fallback '{fallback}' failed: {e}")

    raise RuntimeError("Download failed: no viable format")




# --------------------------- Presentation helpers (unchanged logic) ---------------------------

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


def bytes_human(size_bytes: Optional[int]) -> str:
    """Convert bytes to human readable format"""
    if not size_bytes:
        return ""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}" if size_bytes % 1 else f"{int(size_bytes)} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


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
    Emit resilient format expressions instead of fragile raw itags.
    Strategy per height h (descending):
      1) Try progressive mp4 at <=h
      2) Else merged: bestvideo mp4/avc1 at <=h + best m4a
      3) Else merged: bestvideo at <=h + bestaudio
      4) Else best progressive at <=h (any ext)
    """
    fmts = info.get("formats") or []

    # Debug logging
    print(f"[DEBUG] Total formats available: {len(fmts)}")

    # Collect available heights (from formats with video)
    heights = set()
    has_video = False
    has_audio = False

    for f in fmts:
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"

        if vcodec != "none":
            has_video = True
            h = get_height(f)
            if isinstance(h, int):
                heights.add(h)
            else:
                # Try to get height from format_note or format_id
                format_note = str(f.get("format_note") or "").lower()
                format_id = str(f.get("format_id") or "")

                # Check for common resolution indicators
                for res in [2160, 1440, 1080, 720, 480, 360, 240, 144]:
                    if f"{res}p" in format_note or f"{res}" in format_note or f"{res}" in format_id:
                        heights.add(res)
                        break

        if acodec != "none":
            has_audio = True

    print(f"[DEBUG] Has video: {has_video}, Has audio: {has_audio}")
    print(f"[DEBUG] Detected heights: {sorted(heights)}")

    if not heights and has_video:
        # We have video formats but couldn't detect heights
        # Fall back to generic format selectors
        print("[DEBUG] Video detected but no heights found, using generic selectors")
        return [
            {
                "format_id": None,
                "format_string": "best[ext=mp4][vcodec!*=none]/best[vcodec!*=none]",
                "label": "Best quality (mp4)",
                "ext": "mp4",
                "filesize": "",
            },
            {
                "format_id": None,
                "format_string": "(bv*[ext=mp4]+ba[ext=m4a])/(bv*+ba)/best",
                "label": "Best video+audio (merged)",
                "ext": "mp4",
                "filesize": "",
            },
            {
                "format_id": None,
                "format_string": "bestaudio[ext=m4a]/bestaudio",
                "label": "Audio only (best)",
                "ext": "m4a",
                "filesize": "",
            },
        ]

    if not heights:
        # audio-only case
        print("[DEBUG] No video formats found, audio-only content")
        out_audio = []
        best_audio = None
        for f in fmts:
            if (f.get("vcodec") or "none") == "none" and (f.get("acodec") or "none") != "none":
                if not best_audio or (f.get("tbr", 0) > best_audio.get("tbr", 0)):
                    best_audio = f
        if best_audio:
            out_audio.append({
                "format_id": str(best_audio.get("format_id")),
                "format_string": f"bestaudio[ext=m4a]/bestaudio",   # expression
                "label": "Audio (best)",
                "ext": best_audio.get("ext") or "m4a",
                "filesize": bytes_human(best_audio.get("filesize") or best_audio.get("filesize_approx")),
            })
        return out_audio

    heights = sorted(heights, reverse=True)  # descending (highest first)
    out: List[Dict] = []

    # Map actual heights to standard resolutions for labeling
    # But use actual heights for filtering
    def get_standard_label(h: int) -> str:
        """Map actual height to nearest standard resolution label."""
        # Handle both standard (1080, 720, 480) and non-standard (1920, 1280, 640) heights
        if h >= 2000:
            return "4K"      # 2160p+
        elif h >= 1400:
            return "1440p"   # 1440-1999 (2K)
        elif h >= 1000:
            return "1080p"   # 1000-1399 (catches both 1080 and 1920)
        elif h >= 700:
            return "720p"    # 700-999 (catches both 720 and 1280, 960)
        elif h >= 450:
            return "480p"    # 450-699 (catches both 480 and 640)
        elif h >= 300:
            return "360p"    # 300-449 (catches both 360 and 428, 320)
        elif h >= 200:
            return "240p"    # 200-299 (catches both 240 and 214)
        elif h >= 100:
            return "144p"    # 100-199 (catches both 144 and 128)
        else:
            return f"{h}p"   # <100

    # Use all detected heights, but limit to top 6 to keep UI clean
    ordered_heights = heights[:6] if len(heights) > 6 else heights

    print(f"[DEBUG] Using heights for format generation: {ordered_heights}")

    # Expression helpers
    def label_for(h: int, ext="mp4", merged=False):
        label = get_standard_label(h)
        if merged:
            return f"{label} {ext} (merge)"
        return f"{label} {ext}"

    for h in ordered_heights:
        # Progressive mp4 first (best <= h)
        out.append({
            "format_id": None,
            "format_string": f"best[ext=mp4][vcodec!*=none][height<={h}]"
                              f"/best[height<={h}]",  # fallback progressive of any ext
            "label": label_for(h, "mp4"),
            "ext": "mp4",
            "filesize": "",  # unknown until chosen; keep empty
        })
        # Merged mp4 (video-only + audio)
        out.append({
            "format_id": None,
            "format_string": f"(bv*[ext=mp4][vcodec^=avc1][height<={h}]+ba[ext=m4a])"
                             f"/(bv*[height<={h}]+ba)"
                             f"/best[height<={h}]",
            "label": label_for(h, "mp4", merged=True),
            "ext": "mp4",
            "filesize": "",
        })
        # WebM merged (optional extra; comment out if you want fewer options)
        out.append({
            "format_id": None,
            "format_string": f"(bv*[ext=webm][height<={h}]+ba[ext=webm])"
                             f"/(bv*[height<={h}]+ba)"
                             f"/best[height<={h}]",
            "label": label_for(h, "webm", merged=True),
            "ext": "webm",
            "filesize": "",
        })

    # Best audio only
    out.append({
        "format_id": None,
        "format_string": "bestaudio[ext=m4a]/bestaudio",
        "label": "Audio (best)",
        "ext": "m4a",
        "filesize": "",
    })

    # Safety check: if we somehow ended up with no formats, add a fallback
    if not out:
        print("[WARN] No formats generated, adding fallback 'best' option")
        out.append({
            "format_id": None,
            "format_string": "best",
            "label": "Best available",
            "ext": "mp4",
            "filesize": "",
        })

    print(f"[DEBUG] Generated {len(out)} format options")
    return out

# def build_formats(info: Dict) -> List[Dict]:
#     """
#     Return clean options for ANY site:
#       - Progressive if available
#       - Else merged (best video-only + best audio) per height
#       - Multiple audio language options when available
#     """
#     fmts = info.get("formats") or []

#     # best candidates per height
#     best_prog_mp4: Dict[int, dict] = {}
#     best_prog_webm: Dict[int, dict] = {}
#     best_vo_mp4: Dict[int, dict] = {}
#     best_vo_webm: Dict[int, dict] = {}

#     # Track best audio by language
#     best_audio_by_lang: Dict[str, Dict[str, Optional[dict]]] = {}
#     best_audio_m4a: Optional[dict] = None
#     best_audio_webm: Optional[dict] = None

#     def better(a, b, key="tbr"):
#         return (a or {}).get(key, 0) > (b or {}).get(key, 0)

#     for f in fmts:
#         ext = f.get("ext")
#         v   = f.get("vcodec")
#         a   = f.get("acodec")
#         h   = get_height(f)

#         # Audio-only
#         if v == "none" and a != "none":
#             lang = f.get("language") or f.get("lang") or "unknown"
#             if lang not in best_audio_by_lang:
#                 best_audio_by_lang[lang] = {"m4a": None, "webm": None}
#             if ext in ("m4a", "mp4"):
#                 if better(f, best_audio_by_lang[lang]["m4a"]):
#                     best_audio_by_lang[lang]["m4a"] = f
#                 if better(f, best_audio_m4a):
#                     best_audio_m4a = f
#             elif ext in ("webm", "opus"):
#                 if better(f, best_audio_by_lang[lang]["webm"]):
#                     best_audio_by_lang[lang]["webm"] = f
#                 if better(f, best_audio_webm):
#                     best_audio_webm = f
#             continue

#         if v == "none":
#             continue  # not a video track

#         # Prefer H.264 when present for mp4
#         vcodec = (v or "").lower()
#         is_h264 = "avc1" in vcodec or "h264" in vcodec

#         if h is not None:
#             if a != "none":  # progressive
#                 if ext == "mp4":
#                     cur = best_prog_mp4.get(h)
#                     if not cur or better(f, cur) or (is_h264 and not ("avc1" in (cur.get("vcodec") or ""))):
#                         best_prog_mp4[h] = f
#                 elif ext == "webm":
#                     cur = best_prog_webm.get(h)
#                     if not cur or better(f, cur):
#                         best_prog_webm[h] = f
#             else:  # video-only
#                 if ext == "mp4":
#                     cur = best_vo_mp4.get(h)
#                     if not cur or better(f, cur) or (is_h264 and not ("avc1" in (cur.get("vcodec") or ""))):
#                         best_vo_mp4[h] = f
#                 elif ext == "webm":
#                     cur = best_vo_webm.get(h)
#                     if not cur or better(f, cur):
#                         best_vo_webm[h] = f

#     heights = sorted(set(
#         list(best_prog_mp4.keys()) +
#         list(best_prog_webm.keys()) +
#         list(best_vo_mp4.keys()) +
#         list(best_vo_webm.keys())
#     ))

#     out: List[Dict] = []

#     for h in heights:
#         # 1) progressive mp4 (ideal)
#         if h in best_prog_mp4:
#             f = best_prog_mp4[h]
#             out.append({
#                 "format_id": str(f.get("format_id")),
#                 "format_string": str(f.get("format_id")),
#                 "label": f"{h}p mp4",
#                 "ext": "mp4",
#                 "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#             })
#             continue

#         # 2) merged mp4: video-only mp4 + best audio (m4a preferred)
#         if h in best_vo_mp4 and (best_audio_m4a or best_audio_webm):
#             v = best_vo_mp4[h]

#             if len(best_audio_by_lang) > 1:
#                 # multiple language options
#                 for lang, audio_formats in best_audio_by_lang.items():
#                     a = audio_formats["m4a"] or audio_formats["webm"]
#                     if a:
#                         lang_label = f" [{lang}]" if lang != "unknown" else ""
#                         v_size = v.get("filesize") or v.get("filesize_approx") or 0
#                         a_size = a.get("filesize") or a.get("filesize_approx") or 0
#                         combined_size = v_size + a_size if v_size and a_size else None
#                         out.append({
#                             "format_id": None,
#                             "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
#                             "label": f"{h}p mp4{lang_label}",
#                             "ext": "mp4",
#                             "filesize": bytes_human(combined_size),
#                         })
#             else:
#                 # single language
#                 a = best_audio_m4a or best_audio_webm
#                 v_size = v.get("filesize") or v.get("filesize_approx") or 0
#                 a_size = a.get("filesize") or a.get("filesize_approx") or 0
#                 combined_size = v_size + a_size if v_size and a_size else None
#                 out.append({
#                     "format_id": None,
#                     "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
#                     "label": f"{h}p mp4",
#                     "ext": "mp4",
#                     "filesize": bytes_human(combined_size),
#                 })
#             continue

#         # 3) progressive webm
#         if h in best_prog_webm:
#             f = best_prog_webm[h]
#             out.append({
#                 "format_id": str(f.get("format_id")),
#                 "format_string": str(f.get("format_id")),
#                 "label": f"{h}p webm",
#                 "ext": "webm",
#                 "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#             })
#             continue

#         # 4) merged webm
#         if h in best_vo_webm and best_audio_webm:
#             v = best_vo_webm[h]
#             a = best_audio_webm
#             v_size = v.get("filesize") or v.get("filesize_approx") or 0
#             a_size = a.get("filesize") or a.get("filesize_approx") or 0
#             combined_size = v_size + a_size if v_size and a_size else None
#             out.append({
#                 "format_id": None,
#                 "format_string": f"{v.get('format_id')}+{a.get('format_id')}",
#                 "label": f"{h}p webm (merge)",
#                 "ext": "webm",
#                 "filesize": bytes_human(combined_size),
#             })

#     # Audio-only options
#     if len(best_audio_by_lang) > 1:
#         for lang, audio_formats in best_audio_by_lang.items():
#             lang_label = f" [{lang}]" if lang != "unknown" else ""
#             if audio_formats["m4a"]:
#                 f = audio_formats["m4a"]
#                 out.append({
#                     "format_id": str(f.get("format_id")),
#                     "format_string": str(f.get("format_id")),
#                     "label": f"Audio m4a{lang_label}",
#                     "ext": "m4a",
#                     "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#                 })
#             elif audio_formats["webm"]:
#                 f = audio_formats["webm"]
#                 out.append({
#                     "format_id": str(f.get("format_id")),
#                     "format_string": str(f.get("format_id")),
#                     "label": f"Audio webm{lang_label}",
#                     "ext": "webm",
#                     "filesize": bytes_human(f.get("filesize") or f.get("filesize_approx")),
#                 })
#     else:
#         if best_audio_m4a:
#             out.append({
#                 "format_id": str(best_audio_m4a.get("format_id")),
#                 "format_string": str(best_audio_m4a.get("format_id")),
#                 "label": "Audio m4a",
#                 "ext": "m4a",
#                 "filesize": bytes_human(best_audio_m4a.get("filesize") or best_audio_m4a.get("filesize_approx")),
#             })
#         elif best_audio_webm:
#             out.append({
#                 "format_id": str(best_audio_webm.get("format_id")),
#                 "format_string": str(best_audio_webm.get("format_id")),
#                 "label": "Audio webm",
#                 "ext": "webm",
#                 "filesize": bytes_human(best_audio_webm.get("filesize") or best_audio_webm.get("filesize_approx")),
#             })

#     return out
