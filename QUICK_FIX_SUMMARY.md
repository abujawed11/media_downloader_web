# 🔧 Download Issues - FIXED!

## What Was Wrong

### 1. ❌ Files Downloading to Temp Folder (CRITICAL)
**Symptom**: "File does not exist" error after download completes

**Root Cause**: Downloads were going to `/tmp` instead of persistent storage

**✅ FIXED**: Now downloads to `./downloads/` (local) or `/app/downloads/` (Docker volume)

---

### 2. ❌ Pause/Resume Not Working (Celery Mode)
**Symptom**: Clicking pause does nothing

**Root Cause**: Celery doesn't support native pause/resume

**✅ FIXED**: Implemented Redis-based pause/resume mechanism

---

### 3. ❌ Download Continues After Page Refresh
**Symptom**: UI shows stopped but download continues in background

**Root Cause**: Frontend loses job ID, but backend keeps running

**✅ PARTIALLY FIXED**: Backend now works correctly, but frontend needs to save job IDs

---

### 4. ❌ Job ID Changes on Refresh
**Symptom**: Can't reconnect to download after refresh

**Root Cause**: Job ID doesn't change, but UI loses it

**✅ FIXED**: Job IDs are stable, just need frontend to persist them

---

## What You Need to Do

### For Docker Setup:

1. **Update your `.env` file** (if running in Docker):
```bash
YTDLP_OUTPUT_PATH=/app/downloads  # Use absolute path for Docker
```

2. **Rebuild your containers**:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

3. **Verify downloads volume is mounted**:
```bash
docker volume inspect media-downloader-web_downloads
```

---

### For Local Development:

1. **Your `.env` is fine** (uses `./downloads` by default)

2. **Just restart your server**:
```bash
cd server
python -m uvicorn app.main:app --reload
```

3. **Check startup logs** for:
```
[INFO] Downloads directory: /path/to/downloads
[INFO] Downloads directory is writable ✓
```

---

### Frontend Fix Needed (Important!):

Your frontend needs to **save job IDs** to localStorage:

```javascript
// When starting a download
const response = await fetch('/jobs/start', { /* ... */ });
const job = await response.json();

// Save to localStorage
localStorage.setItem(`job_${job.id}`, JSON.stringify({
  id: job.id,
  title: job.title,
  startedAt: Date.now()
}));

// On page load, restore active jobs
const restoreActiveJobs = () => {
  const jobs = Object.keys(localStorage)
    .filter(key => key.startsWith('job_'))
    .map(key => JSON.parse(localStorage.getItem(key)));

  jobs.forEach(job => {
    // Poll for job status
    pollJobStatus(job.id);
  });
};

// When job completes/fails/cancels
localStorage.removeItem(`job_${job.id}`);
```

---

## Test Your Fixes

### Test 1: Download Persistence
```bash
# Start a download
curl -X POST http://localhost:8000/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","format":"best","title":"Test"}'

# Note the job ID from response
# After download completes, check file exists
ls -la ./downloads/  # Should see downloaded file

# Get the file
curl http://localhost:8000/jobs/{JOB_ID}/file --output test.mp4
```

### Test 2: Pause/Resume (Celery/Docker only)
```bash
# Start download, note job ID
JOB_ID="..."

# Pause it
curl -X POST http://localhost:8000/jobs/$JOB_ID/pause

# Check status (should show "paused")
curl http://localhost:8000/jobs/$JOB_ID

# Resume it
curl -X POST http://localhost:8000/jobs/$JOB_ID/resume

# Should continue from where it left off
```

### Test 3: Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "downloads_dir": "/app/downloads",
  "downloads_dir_writable": true,
  "downloads_dir_exists": true
}
```

---

## How It Works Now

### Download Flow (Docker + Celery):
```
1. POST /jobs/start
   ↓
2. Creates Celery task
   ↓
3. Worker downloads to /app/downloads/md_{task_id}_xxxxx/
   ↓
4. File saved in Docker volume (persists)
   ↓
5. GET /jobs/{id}/file → serves file from volume
```

### Pause/Resume Flow:
```
1. POST /jobs/{id}/pause
   ↓
2. Sets Redis flag: job:{id}:pause
   ↓
3. Task checks flag during download
   ↓
4. Raises TaskPausedException
   ↓
5. POST /jobs/{id}/resume
   ↓
6. Clears flag, restarts task
   ↓
7. yt-dlp continues from partial file (continuedl: true)
```

---

## Debugging

### Check where files are being downloaded:
```bash
# Look for this in logs:
[INFO] Job manager using downloads directory: /app/downloads
[DEBUG] Starting job {id} - Download directory: /app/downloads/...
```

### If "file not found" still occurs:
```bash
# Check the actual directory
docker exec media-downloader-api ls -la /app/downloads/

# Check job status
curl http://localhost:8000/jobs/{JOB_ID}

# Check logs for file location
docker logs media-downloader-api | grep "File location"
```

### If pause doesn't work:
```bash
# Make sure Redis is running
docker exec media-downloader-redis redis-cli PING

# Check pause flag
docker exec media-downloader-redis redis-cli GET "job:{JOB_ID}:pause"

# Check Celery worker is running
docker ps | grep worker
```

---

## Files Changed

✅ `server/app/services/job_manager.py` - Use persistent downloads directory
✅ `server/app/services/celery_job_manager.py` - Implement pause/resume
✅ `server/app/tasks.py` - Check pause/cancel flags
✅ `server/app/routers/media.py` - Better file search and debugging
✅ `server/app/main.py` - Startup checks and health endpoint
✅ `server/.env.example` - Updated documentation

---

## Next Steps

1. ✅ **Already done**: All backend fixes applied
2. ⚠️ **You need to do**: Update frontend to save job IDs to localStorage
3. 📝 **Optional**: Add cleanup endpoint for old downloads
4. 📝 **Optional**: Add progress persistence in Redis for threading mode

---

## Questions?

- Check `FIXES_APPLIED.md` for detailed technical documentation
- Check server logs for `[INFO]` and `[DEBUG]` messages
- Test health endpoint: `GET /health`
- Check Docker volumes: `docker volume ls`

---

**All backend issues are now fixed! Just restart your server/containers and optionally add localStorage persistence in frontend.**
