from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class InfoRequest(BaseModel):
    url: HttpUrl

class FormatItem(BaseModel):
    format_id: Optional[str] = None       # single itag for progressive or audio-only
    format_string: str                    # e.g. "137+140" or just "18"
    label: str                            # "720p mp4", "Audio m4a"
    ext: Optional[str] = None             # final container hint (mp4/webm/mkv)

class InfoResponse(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    formats: List[FormatItem]


from typing import Literal

class StartJobRequest(BaseModel):
    url: HttpUrl
    format: str
    title: Optional[str] = None
    ext: Optional[str] = None
    label: Optional[str] = None  # for UI; backend ignores

JobStatus = Literal["queued","downloading","paused","merging","done","error","canceled"]

class JobResponse(BaseModel):
    id: str
    url: HttpUrl
    title: Optional[str] = None
    format_string: str
    ext: Optional[str] = None
    status: JobStatus
    progress: float
    downloaded_bytes: int
    total_bytes: Optional[int] = None
    speed_bps: Optional[float] = None
    eta_seconds: Optional[int] = None
    filename: Optional[str] = None
    error: Optional[str] = None
