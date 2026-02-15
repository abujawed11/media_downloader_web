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
from ..services import hybrid_job_manager as jm

router = APIRouter(tags=["media"])


# ---------- Metadata ----------
@router.post("/info", response_model=InfoResponse)
def info(body: InfoRequest):
    print(f"[DEBUG] Received info request for URL: {body.url}")
    try:
        print(f"[DEBUG] Starting yt-dlp extraction...")
        data = extract_info(str(body.url))
        print(f"[DEBUG] yt-dlp extraction completed successfully")
        
        # Check if any formats were found
        formats = build_formats(data)
        if not formats:
            raise HTTPException(status_code=400, detail="No downloadable formats found for this URL")
        
        return InfoResponse(
            title=data.get("title") or "Untitled",
            thumbnail=select_thumbnail(data),
            duration=(int(data.get("duration")) if data.get("duration") else None),
            formats=formats,
        )
    except Exception as e:
        error_msg = str(e)
        if "Unsupported URL" in error_msg or "No video formats found" in error_msg:
            raise HTTPException(status_code=400, detail=f"This video site is not supported or the URL contains no downloadable video")
        raise HTTPException(status_code=400, detail=f"Failed to extract video info: {error_msg}")


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


@router.delete("/jobs/{job_id}")
def jobs_delete(job_id: str, delete_file: bool = False):
    """Delete a job from history (and optionally delete the downloaded file)."""
    try:
        job = jm.get_job(job_id)

        # Optionally delete the downloaded file
        if delete_file and job.status == "done":
            import shutil
            tmpdir = getattr(job, "tmpdir", None)
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)
                print(f"[INFO] Deleted files for job {job_id}")

        # Delete job from manager
        jm.delete_job(job_id)

        return {"status": "deleted", "job_id": job_id, "file_deleted": delete_file}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.delete("/jobs")
def jobs_clear_all(delete_files: bool = False):
    """Clear all jobs from history (and optionally delete all downloaded files)."""
    try:
        jobs = jm.list_jobs()
        deleted_count = 0
        files_deleted_count = 0

        for job in jobs:
            # Optionally delete files
            if delete_files and job.status == "done":
                import shutil
                tmpdir = getattr(job, "tmpdir", None)
                if tmpdir and os.path.isdir(tmpdir):
                    try:
                        shutil.rmtree(tmpdir, ignore_errors=True)
                        files_deleted_count += 1
                    except:
                        pass

            # Delete job
            try:
                jm.delete_job(job.id)
                deleted_count += 1
            except:
                pass

        print(f"[INFO] Cleared {deleted_count} jobs, deleted {files_deleted_count} file directories")

        return {
            "status": "cleared",
            "jobs_deleted": deleted_count,
            "files_deleted": files_deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    print(f"[DEBUG] Job {job_id} - Primary filename: {path}")
    print(f"[DEBUG] Job {job_id} - Temp directory: {getattr(job, 'tmpdir', None)}")

    if not path or not os.path.isfile(path):
        # Fallback: look for any file created in the job's temp dir (merge/rename quirks)
        tmpdir = getattr(job, "tmpdir", None)
        if tmpdir and os.path.isdir(tmpdir):
            print(f"[DEBUG] Job {job_id} - Searching in tmpdir: {tmpdir}")
            import glob
            # Look for common video/audio extensions
            patterns = ['*.mp4', '*.mkv', '*.webm', '*.avi', '*.mov', '*.m4a', '*.mp3', '*.flac', '*.wav']
            for pattern in patterns:
                files = glob.glob(os.path.join(tmpdir, pattern))
                if files:
                    # Get the largest file (likely the merged result)
                    path = max(files, key=os.path.getsize)
                    print(f"[DEBUG] Job {job_id} - Found file using pattern {pattern}: {path}")
                    break

    if not path or not os.path.isfile(path):
        # Additional debugging info
        tmpdir = getattr(job, "tmpdir", None)
        if tmpdir and os.path.isdir(tmpdir):
            files_in_dir = os.listdir(tmpdir)
            print(f"[DEBUG] Job {job_id} - Files in tmpdir: {files_in_dir}")
            error_detail = f"File not found. Tmpdir exists with files: {files_in_dir}"
        else:
            error_detail = f"File not found. Tmpdir: {tmpdir} (exists: {os.path.isdir(tmpdir) if tmpdir else False})"

        raise HTTPException(status_code=404, detail=error_detail)

    print(f"[DEBUG] Job {job_id} - Serving file: {path} (size: {os.path.getsize(path)} bytes)")

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
