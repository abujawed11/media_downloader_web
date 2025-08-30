# server/app/routers/media.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, Response
from urllib.parse import unquote
import os
import httpx

from ..models.schemas import (
    InfoRequest,
    InfoResponse,
    StartJobRequest,
    JobResponse,
)
from ..services.ytdlp_service import (
    extract_info,
    build_formats,
    download_to_temp,
    select_thumbnail,
)
from ..services import job_manager as jm

router = APIRouter(tags=["media"])


# ---------- Metadata ----------
@router.post("/info", response_model=InfoResponse)
def info(body: InfoRequest):
    try:
        data = extract_info(str(body.url))
        return InfoResponse(
            title=data.get("title") or "Untitled",
            thumbnail=select_thumbnail(data),
            duration=(int(data.get("duration")) if data.get("duration") else None),
            formats=build_formats(data),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Simple one-shot download (optional; jobs flow is preferred) ----------
@router.get("/download")
def download(url: str, format: str):  # format can be "137+140" or "18"
    try:
        url = unquote(url)
        file_path = download_to_temp(url, format)
        filename = file_path.split("\\")[-1].split("/")[-1]

        def file_iter():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(file_iter(), headers=headers, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Jobs API ----------
def _job_json(job: jm.Job) -> dict:
    """Serialize a Job dataclass safely for the API."""
    d = job.__dict__.copy()
    # remove private/control fields & large internals
    d.pop("_pause_req", None)
    d.pop("_cancel_req", None)
    # keep tmpdir off the wire; we'll still use it internally when serving the file
    # (do NOT remove from the object itself)
    d.pop("tmpdir", None)
    return d


@router.post("/jobs/start", response_model=JobResponse)
def jobs_start(body: StartJobRequest):
    try:
        job = jm.start_job(str(body.url), body.format, title=body.title, ext=body.ext)
        return JobResponse(**_job_json(job))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/pause", response_model=JobResponse)
def jobs_pause(job_id: str):
    try:
        job = jm.pause_job(job_id)
        return JobResponse(**_job_json(job))
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/resume", response_model=JobResponse)
def jobs_resume(job_id: str):
    try:
        job = jm.resume_job(job_id)
        return JobResponse(**_job_json(job))
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def jobs_cancel(job_id: str):
    try:
        job = jm.cancel_job(job_id)
        return JobResponse(**_job_json(job))
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs/{job_id}", response_model=JobResponse)
def jobs_get(job_id: str):
    try:
        job = jm.get_job(job_id)
        return JobResponse(**_job_json(job))
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs", response_model=list[JobResponse])
def jobs_list():
    return [JobResponse(**_job_json(j)) for j in jm.list_jobs()]


@router.get("/jobs/{job_id}/file")
def jobs_file(job_id: str):
    try:
        job = jm.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    # Only allow when finished
    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"Job not done (status={job.status})")

    # Primary path from yt-dlp
    path = job.filename
    if not path or not os.path.isfile(path):
        # Fallback: look for any file created in the job's temp dir (merge/rename quirks)
        tmpdir = getattr(job, "tmpdir", None)
        if tmpdir and os.path.isdir(tmpdir):
            for name in os.listdir(tmpdir):
                p = os.path.join(tmpdir, name)
                if os.path.isfile(p):
                    path = p
                    break

    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=os.path.basename(path),
    )


# ---------- Image Proxy ----------
@router.get("/proxy-image")
async def proxy_image(url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to proxy image: {str(e)}")
