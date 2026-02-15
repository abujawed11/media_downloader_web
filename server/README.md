# Media Downloader Server

FastAPI backend with Redis + Celery for distributed media downloading.

## Architecture

- **FastAPI**: REST API server
- **Redis**: Job queue and cache
- **Celery**: Distributed task queue for downloads
- **Flower**: Web-based monitoring dashboard (optional)
- **yt-dlp**: Media download engine

## Features

✅ **Multiple concurrent downloads** - Process many downloads in parallel
✅ **Job persistence** - Downloads survive server restarts
✅ **Auto-retry** - Failed downloads retry automatically
✅ **Progress tracking** - Real-time download progress
✅ **Worker scaling** - Add more workers as needed
✅ **Monitoring** - Flower dashboard at http://localhost:5555

---

## Quick Start

### Option 1: Docker (Recommended)

From the project root:

```bash
# Start all services (API + Redis + Workers + Flower)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

**Services:**
- API: http://localhost:8000
- Flower Dashboard: http://localhost:5555
- Redis: localhost:6379

### Option 2: Local Development

1. **Install Redis:**
   ```bash
   # Windows (using Chocolatey)
   choco install redis-64
   redis-server

   # Or use WSL/Docker
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Install Python dependencies:**
   ```bash
   cd server
   python -m venv venv
   source venv/Scripts/activate  # Windows Git Bash
   pip install -r requirements.txt
   ```

3. **Start services:**
   ```bash
   # Terminal 1: Start API
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   # Terminal 2: Start Celery Worker
   celery -A app.celery_app worker --loglevel=info --concurrency=4

   # Terminal 3 (Optional): Start Flower
   celery -A app.celery_app flower --port=5555
   ```

---

## Configuration

Edit `server/.env`:

```env
# Server
HOST=0.0.0.0
PORT=8000

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_WORKER_CONCURRENCY=4  # Number of parallel downloads

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174
```

---

## Scaling Workers

### In Docker:

Edit `docker-compose.yml` and change worker concurrency:

```yaml
worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=8
```

Or scale worker containers:

```bash
docker-compose up -d --scale worker=3
```

### Locally:

```bash
# Start multiple workers
celery -A app.celery_app worker --loglevel=info --concurrency=8
```

---

## API Endpoints

### Get video info
```bash
POST /info
{
  "url": "https://www.youtube.com/watch?v=..."
}
```

### Start download job
```bash
POST /jobs/start
{
  "url": "https://www.youtube.com/watch?v=...",
  "format": "best[height<=1080]",
  "title": "My Video",
  "ext": "mp4"
}
```

### Get job status
```bash
GET /jobs/{job_id}
```

### List all jobs
```bash
GET /jobs
```

### Cancel job
```bash
POST /jobs/{job_id}/cancel
```

### Download file
```bash
GET /jobs/{job_id}/file
```

---

## Monitoring

### Flower Dashboard

Access at http://localhost:5555

- View active/completed tasks
- Monitor worker status
- See task statistics
- Retry failed tasks

### Redis CLI

```bash
# Connect to Redis
docker exec -it media-downloader-redis redis-cli

# View all jobs
SMEMBERS jobs:all

# View job details
HGETALL job:{job_id}
```

---

## Troubleshooting

### Worker not processing jobs

```bash
# Check worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker
```

### Redis connection error

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker exec -it media-downloader-redis redis-cli ping
```

### Download fails

- Check cookie files in `server/cookies/`
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check Flower dashboard for error details

---

## Performance Tips

1. **Increase concurrent fragments**: Edit `tasks.py` → `concurrent_fragments: 32`
2. **Scale workers**: `docker-compose up -d --scale worker=3`
3. **Use faster storage**: Mount downloads to SSD
4. **Add more memory**: For large files, increase Docker memory limit

---

## Production Deployment

1. **Use production WSGI server** (already using Uvicorn)
2. **Enable Redis persistence** (already configured)
3. **Set up monitoring** (Flower + error tracking)
4. **Use environment-specific .env files**
5. **Set up reverse proxy** (nginx)
6. **Enable SSL/TLS**

---

## Development

### Run tests
```bash
pytest
```

### Format code
```bash
black app/
```

### Type checking
```bash
mypy app/
```
