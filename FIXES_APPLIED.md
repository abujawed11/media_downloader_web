# Download System Fixes Applied

## Issues Fixed

### 🔴 CRITICAL: Files Downloading to Temporary Folder
**Problem**: Files were being downloaded to system temp directory (`/tmp`) instead of the persistent Docker volume, causing "file not found" errors after download completion.

**Root Cause**:
- Threading job manager (`job_manager.py`) was using `tempfile.mkdtemp()` without specifying a directory
- This created temp folders in system `/tmp` which are ephemeral and get cleaned up
- Docker volume was mounted at `/app/downloads` but wasn't being used

**Fix Applied**:
- Modified `job_manager.py` to use `YTDLP_OUTPUT_PATH` from config
- Downloads now go to `./downloads` (local) or `/app/downloads` (Docker)
- Added `__post_init__` method to Job dataclass to create tmpdir in persistent location
- Added logging to show where files are being downloaded

**Files Changed**:
- `server/app/services/job_manager.py` - Added DOWNLOADS_DIR configuration and proper tmpdir initialization

---

### 🟡 Pause/Resume Not Working in Celery Mode
**Problem**: Pause/resume functionality existed in threading mode but was non-functional in Celery mode (just returned current state without actually pausing).

**Root Cause**:
- Celery doesn't natively support pause/resume
- Functions existed but did nothing

**Fix Applied**:
- Implemented Redis-based pause/resume using flags
- When pause is requested, a Redis key `job:{job_id}:pause` is set
- The download task checks this flag during progress updates
- When paused, task raises `TaskPausedException` and preserves downloaded files
- Resume clears the flag and restarts the task with `continuedl: True` (yt-dlp resumes partial downloads)

**Files Changed**:
- `server/app/services/celery_job_manager.py` - Implemented pause/resume with Redis flags
- `server/app/tasks.py` - Added pause/cancel checking in progress hook

---

### 🟡 Better Cancel Implementation
**Problem**: Cancel wasn't cleaning up properly

**Fix Applied**:
- Added Redis flag `job:{job_id}:cancel` for graceful cancellation
- Task checks flag during download and raises `TaskCanceledException`
- Properly cleans up temporary files on cancel

**Files Changed**:
- `server/app/services/celery_job_manager.py` - Set cancel flag
- `server/app/tasks.py` - Check cancel flag and clean up

---

### 🟡 File Not Found on Download Complete
**Problem**: Even when download completed successfully, file serving endpoint couldn't find the file

**Root Cause**:
- File was in temp directory but path wasn't being tracked correctly
- Fallback logic wasn't checking all possible locations

**Fix Applied**:
- Enhanced file search logic to check multiple patterns (mp4, mkv, webm, etc.)
- Added comprehensive debugging logs
- Better error messages showing what files exist in tmpdir

**Files Changed**:
- `server/app/routers/media.py` - Enhanced file serving endpoint with better search and debugging

---

### 🟡 Job Persistence Across Page Refreshes
**Issue**: When page refreshes, UI loses job ID (if not saved in frontend localStorage)

**Current State**:
- **Threading mode**: Jobs stored in memory (lost on server restart)
- **Celery mode**: Jobs stored in Redis with 24-hour expiry (persisted)

**Frontend Recommendation**:
- Save active job IDs to `localStorage` when starting a download
- On page load, restore job IDs from `localStorage` and poll for status
- Clear from `localStorage` when job reaches `done`, `error`, or `canceled` state

---

## How It Works Now

### Threading Mode (Local Development)
1. Job starts, creates tmpdir in `./downloads/mdjob_{id}_xxxxx/`
2. yt-dlp downloads file to this directory
3. File persists in `./downloads/` folder
4. Pause/resume works by setting flags and re-spawning thread
5. Job state stored in memory (lost on restart)

### Celery Mode (Docker Production)
1. Job starts, Celery task submitted to worker
2. Worker creates tmpdir in `/app/downloads/md_{task_id}_xxxxx/`
3. yt-dlp downloads file to this directory (in Docker volume)
4. File persists in Docker volume `downloads:/app/downloads`
5. Pause/resume works via Redis flags
6. Job metadata stored in Redis (persists for 24 hours)

---

## Environment Configuration

### For Docker (docker-compose):
```env
YTDLP_OUTPUT_PATH=/app/downloads
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### For Local Development:
```env
YTDLP_OUTPUT_PATH=./downloads
REDIS_URL=redis://localhost:6379/0  # If Redis available
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

If Redis is not available locally, the app automatically falls back to threading mode.

---

## Volume Mounting (Docker)

Ensure your `docker-compose.yml` has proper volume mounts:

```yaml
services:
  api:
    volumes:
      - downloads:/app/downloads  # Persistent storage
      - ./server/cookies:/app/cookies

  worker:
    volumes:
      - downloads:/app/downloads  # Same volume as API
      - ./server/cookies:/app/cookies

volumes:
  downloads:  # Named volume for persistence
```

---

## Testing the Fixes

### Test 1: File Persistence
1. Start a download
2. Wait for completion
3. Check that file exists in `./downloads/` (local) or `/app/downloads/` (Docker)
4. Call `/jobs/{job_id}/file` endpoint - should successfully serve file

### Test 2: Pause/Resume (Celery mode only)
1. Start a download
2. While downloading, call `/jobs/{job_id}/pause`
3. Download should pause
4. Call `/jobs/{job_id}/resume`
5. Download should continue from where it left off

### Test 3: Page Refresh
1. Start a download in browser
2. Note the job ID
3. Refresh the page
4. Poll `/jobs/{job_id}` with the same job ID
5. Download should still be running/completed

### Test 4: Cancel
1. Start a download
2. Call `/jobs/{job_id}/cancel`
3. Download should stop and temp files should be cleaned up

---

## Debugging

### Check Download Directory
```bash
# Local
ls -la ./downloads/

# Docker
docker exec media-downloader-api ls -la /app/downloads/
```

### Check Logs
```bash
# Look for these log messages:
[INFO] Job manager using downloads directory: /app/downloads
[DEBUG] Starting job {id} - Download directory: /app/downloads/mdjob_{id}_xxxxx
[DEBUG] Job {id} - Serving file: /app/downloads/.../video.mp4
```

### Check Redis (Celery mode)
```bash
docker exec media-downloader-redis redis-cli KEYS "job:*"
docker exec media-downloader-redis redis-cli HGETALL "job:{job_id}"
```

---

## Additional Improvements Made

1. **Better Logging**: Added debug logs throughout the download pipeline
2. **Absolute Paths**: Convert relative paths to absolute for consistency
3. **Error Messages**: More descriptive error messages with actual file listings
4. **File Search**: Enhanced pattern matching for finding downloaded files
5. **Exception Handling**: Proper cleanup on pause/cancel/error

---

## Known Limitations

1. **Threading Mode**:
   - Jobs lost on server restart (in-memory only)
   - Consider using Redis for persistence even in threading mode

2. **Celery Pause/Resume**:
   - Not true pause (task stops, then restarts)
   - Relies on yt-dlp's `continuedl` to resume from partial files
   - May re-download small portions if fragments were incomplete

3. **Job Expiry**:
   - Redis job metadata expires after 24 hours
   - Old jobs auto-cleanup but files remain in downloads folder
   - Consider adding manual cleanup endpoint

---

## Recommendations

### Frontend (UI):
1. Save job IDs to `localStorage` when starting downloads
2. On page load, restore and poll for active jobs
3. Show reconnection UI when regaining job status after refresh
4. Handle expired jobs gracefully (24+ hours old)

### Backend:
1. Consider implementing job persistence for threading mode (SQLite or Redis)
2. Add cleanup endpoint to remove old completed jobs and files
3. Add health check endpoint to verify download directory is writable
4. Consider adding job priority/queue management

### DevOps:
1. Monitor volume usage (`docker volume inspect downloads`)
2. Set up log rotation for download logs
3. Consider adding metrics (download speed, success rate)
4. Backup/restore strategy for downloads volume

---

## Files Modified

- ✅ `server/app/services/job_manager.py` - Fixed temp directory location
- ✅ `server/app/services/celery_job_manager.py` - Implemented pause/resume
- ✅ `server/app/tasks.py` - Added pause/cancel checking
- ✅ `server/app/routers/media.py` - Enhanced file serving
- ✅ `server/.env.example` - Updated documentation
- ✅ `FIXES_APPLIED.md` - This document
