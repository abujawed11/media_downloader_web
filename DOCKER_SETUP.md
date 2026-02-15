# 🐳 Docker Setup Guide - Redis + Celery

This guide will help you run the Media Downloader with **Docker, Redis, and Celery** for true parallel downloads.

---

## 🎯 What You Get

✅ **Multiple concurrent downloads** - Download 4+ videos simultaneously
✅ **Job persistence** - Downloads survive server restarts
✅ **True parallelism** - No Python GIL limitations
✅ **Auto-retry** - Failed downloads retry automatically
✅ **Monitoring** - Web dashboard to track all downloads
✅ **Scalable** - Add more workers as needed

---

## 📋 Prerequisites

1. **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop))
2. **Docker Compose** (included with Docker Desktop)

Verify installation:
```bash
docker --version
docker-compose --version
```

---

## 🚀 Quick Start

### 1. Start All Services

From the project root directory:

```bash
docker-compose up -d
```

This starts:
- ✅ **Redis** - Job queue (port 6379)
- ✅ **FastAPI API** - Backend server (port 8000)
- ✅ **Celery Worker** - Download processor (4 concurrent workers)
- ✅ **Flower** - Monitoring dashboard (port 5555)

### 2. Check Services

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f worker
docker-compose logs -f api
```

### 3. Access Services

- **Frontend**: http://localhost:5173 (Vite dev server)
- **Backend API**: http://localhost:8000
- **Flower Dashboard**: http://localhost:5555
- **API Docs**: http://localhost:8000/docs

### 4. Stop Services

```bash
docker-compose down
```

---

## 🎛️ Configuration

### Environment Variables

Edit `server/.env` to customize:

```env
# Worker Concurrency (how many downloads at once)
CELERY_WORKER_CONCURRENCY=4

# CORS Origins
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

# Redis URL (use redis://redis:6379/0 in Docker)
REDIS_URL=redis://redis:6379/0
```

### Scale Workers

Want more concurrent downloads? Scale the workers:

```bash
# Run 3 worker containers (4 concurrent downloads each = 12 total)
docker-compose up -d --scale worker=3
```

Or edit `docker-compose.yml`:

```yaml
worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=8
```

---

## 📊 Monitoring with Flower

Access **Flower Dashboard** at http://localhost:5555

**Features:**
- 📈 View active and completed tasks
- 👷 Monitor worker status and performance
- 📊 Task success/failure statistics
- 🔄 Retry failed tasks manually
- 📉 Performance graphs

---

## 🛠️ Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f api
docker-compose logs -f redis
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart worker
docker-compose restart api
```

### Update Code
```bash
# Rebuild containers after code changes
docker-compose up -d --build

# Force rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Clear Everything
```bash
# Stop and remove containers, networks, volumes
docker-compose down -v

# Remove downloaded files
docker volume rm media-downloader-web_downloads
```

### Redis CLI
```bash
# Access Redis
docker exec -it media-downloader-redis redis-cli

# Inside Redis CLI:
PING                    # Test connection
KEYS *                  # List all keys
SMEMBERS jobs:all       # List all jobs
HGETALL job:{job_id}    # View job details
FLUSHALL                # Clear all data (careful!)
```

---

## 🐛 Troubleshooting

### ❌ Worker not processing jobs

```bash
# Check worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker

# Check Celery connection to Redis
docker-compose exec worker celery -A app.celery_app inspect ping
```

### ❌ Redis connection error

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker exec -it media-downloader-redis redis-cli ping
# Should return: PONG

# View Redis logs
docker-compose logs redis
```

### ❌ Port already in use

```bash
# Error: port 8000 is already allocated
# Solution: Stop the service using that port or change the port

# Change API port in docker-compose.yml:
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### ❌ Download fails

1. **Check logs**: `docker-compose logs -f worker`
2. **Check Flower**: http://localhost:5555 for detailed error
3. **Update yt-dlp**:
   ```bash
   docker-compose build --no-cache worker
   docker-compose up -d
   ```
4. **Check cookies**: Make sure cookie files are in `server/cookies/`

---

## 🔄 Development Workflow

### Code Changes

1. **Backend changes** (auto-reload enabled):
   ```bash
   # No action needed - changes auto-reload
   docker-compose logs -f api
   ```

2. **Worker changes** (requires restart):
   ```bash
   docker-compose restart worker
   ```

3. **Dependency changes**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

### Hot Reload

The API service has hot reload enabled in development. Just save your files and the server restarts automatically.

---

## 📈 Performance Tuning

### 1. Increase Concurrent Downloads

Edit `docker-compose.yml`:

```yaml
worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=8
```

Or scale workers:
```bash
docker-compose up -d --scale worker=2
```

### 2. Optimize yt-dlp Settings

Edit `server/app/tasks.py`:

```python
ydl_opts = {
    "concurrent_fragments": 32,  # More parallel chunks
    "http_chunk_size": 20971520,  # 20MB chunks
    # ...
}
```

### 3. More Memory

Edit `docker-compose.yml`:

```yaml
worker:
  deploy:
    resources:
      limits:
        memory: 2G
```

---

## 🌐 Production Deployment

For production, add:

1. **Reverse Proxy** (nginx):
   ```nginx
   location /api {
       proxy_pass http://localhost:8000;
   }
   ```

2. **SSL/TLS**: Use Let's Encrypt with nginx

3. **Persistent Volumes**: Already configured ✅

4. **Health Checks**: Already configured ✅

5. **Monitoring**: Use Flower + error tracking (Sentry)

6. **Environment Variables**: Use `.env.production`

---

## 📝 Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│   FastAPI   │─────▶│    Redis    │
│   (API)     │      │   (Queue)   │
└─────────────┘      └──────┬──────┘
                            │
                     ┌──────┴──────┐
                     │             │
              ┌──────▼─────┐ ┌────▼──────┐
              │  Worker 1  │ │ Worker 2  │
              │  (Celery)  │ │ (Celery)  │
              └────────────┘ └───────────┘
                     │             │
                     └──────┬──────┘
                            ▼
                     ┌─────────────┐
                     │  Downloads  │
                     │   (Files)   │
                     └─────────────┘
```

---

## ✅ Next Steps

1. ✅ Start Docker Compose: `docker-compose up -d`
2. ✅ Open Flower: http://localhost:5555
3. ✅ Test a download from your frontend
4. ✅ Watch the worker process it in Flower
5. ✅ Scale workers if needed

Need help? Check the logs: `docker-compose logs -f`
