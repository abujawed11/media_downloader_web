# VPS Deployment Guide

## How It Works on VPS

### Complete Flow:

```
┌──────────────┐
│ User Browser │ (Anywhere in the world)
└──────┬───────┘
       │ 1. Request download
       ↓
┌──────────────┐
│  VPS Server  │ (Your hosted server)
│              │
│ ┌──────────┐ │
│ │ Backend  │ │ 2. Downloads video
│ │  (API)   │ │    using yt-dlp
│ └────┬─────┘ │
│      │       │
│ ┌────▼─────┐ │ 3. Saves to Docker volume
│ │/downloads│ │    /app/downloads/
│ │  Volume  │ │
│ └──────────┘ │
└──────┬───────┘
       │ 4. User clicks "Download"
       │    GET /jobs/{id}/file
       ↓
┌──────────────┐
│ User Browser │ 5. Streams file VPS → Browser
│   Downloads  │ 6. Saves to local disk
└──────────────┘
```

---

## Storage Architecture

### On VPS:

```
/var/lib/docker/volumes/
└── media-downloader-web_downloads/
    └── _data/
        ├── md_job1_xxxxx/
        │   └── video1.mp4  (stored on VPS)
        ├── md_job2_xxxxx/
        │   └── video2.mp4  (stored on VPS)
        └── md_job3_xxxxx/
            └── video3.webm (stored on VPS)
```

### On User's Machine:
```
~/Downloads/
├── video1.mp4  (downloaded from VPS)
├── video2.mp4  (downloaded from VPS)
└── video3.webm (downloaded from VPS)
```

---

## Deployment Steps

### 1. Clone to VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Clone the repository
git clone https://github.com/yourusername/media-downloader-web.git
cd media-downloader-web
```

### 2. Configure Environment

```bash
# Copy example env
cp server/.env.example server/.env

# Edit configuration for VPS
nano server/.env
```

**VPS Configuration:**
```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production

# CORS - Add your frontend URL
ALLOWED_ORIGINS=http://your-domain.com,https://your-domain.com

# Downloads - Use absolute path for Docker
YTDLP_OUTPUT_PATH=/app/downloads

# Redis (Docker internal network)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d --build

# Check if running
docker-compose ps

# Check logs
docker-compose logs -f api
docker-compose logs -f worker
```

### 4. Setup Nginx Reverse Proxy (Optional but Recommended)

```nginx
# /etc/nginx/sites-available/media-downloader

server {
    listen 80;
    server_name your-domain.com;

    # File upload size limit (for large downloads)
    client_max_body_size 10G;

    # API backend
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # Timeout for large file downloads
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Frontend (if serving from same server)
    location / {
        root /var/www/media-downloader;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/media-downloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Setup SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Storage Management

### Monitor Disk Usage

```bash
# Check Docker volumes
docker volume ls
docker volume inspect media-downloader-web_downloads

# Check disk usage
df -h

# Check downloads folder size
du -sh /var/lib/docker/volumes/media-downloader-web_downloads/_data/
```

### Manual Cleanup

```bash
# Using the management script
cd media-downloader-web
./manage-jobs.sh clean  # Deletes all jobs and files

# Or clean specific job
./manage-jobs.sh list
docker exec media-downloader-api rm -rf /app/downloads/md_OLD_JOB_ID_*
```

### Automatic Cleanup (Recommended)

Set up a cron job to run cleanup daily:

```bash
# Copy cleanup script to server
docker cp server/cleanup_old_files.py media-downloader-api:/app/

# Add cron job
crontab -e
```

Add this line:
```cron
# Clean up files older than 24 hours, every 6 hours
0 */6 * * * docker exec media-downloader-api python /app/cleanup_old_files.py >> /var/log/media-cleanup.log 2>&1
```

Test it first:
```bash
# Dry run (see what would be deleted)
docker exec media-downloader-api python /app/cleanup_old_files.py --dry-run

# Actual run
docker exec media-downloader-api python /app/cleanup_old_files.py
```

---

## Security Considerations

### 1. Rate Limiting

Add rate limiting to prevent abuse:

```python
# server/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In routes
@router.post("/jobs/start")
@limiter.limit("10/minute")  # Max 10 downloads per minute
def jobs_start(request: Request, body: StartJobRequest):
    # ...
```

### 2. Authentication (Optional)

For private use, add basic auth:

```nginx
# In nginx config
location /api/ {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8000/;
}
```

Create password:
```bash
sudo htpasswd -c /etc/nginx/.htpasswd yourusername
```

### 3. Firewall

```bash
# Allow only HTTP/HTTPS
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

---

## Monitoring

### Check Service Health

```bash
# API health check
curl http://localhost:8000/health

# Check if worker is processing
docker logs media-downloader-worker --tail 50

# Check Redis
docker exec media-downloader-redis redis-cli PING

# Check active downloads
./manage-jobs.sh status
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker

# Export logs
docker-compose logs --no-color > logs.txt
```

### Resource Usage

```bash
# Docker stats
docker stats

# Disk usage by service
docker system df
docker system df -v
```

---

## Backup & Restore

### Backup Downloads Volume

```bash
# Create backup
docker run --rm \
  -v media-downloader-web_downloads:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/downloads-backup-$(date +%Y%m%d).tar.gz /data

# Restore backup
docker run --rm \
  -v media-downloader-web_downloads:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/downloads-backup-20260215.tar.gz -C /
```

### Backup Redis Data

```bash
# Redis automatically saves to volume (redis_data)
# Backup the volume
docker run --rm \
  -v media-downloader-web_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz /data
```

---

## Troubleshooting

### Issue: Downloads slow on VPS

**Cause**: VPS bandwidth limitation

**Solution**:
- Upgrade VPS plan
- Or use direct download links (serve download URL instead of downloading first)

### Issue: Disk full

```bash
# Check what's using space
du -sh /var/lib/docker/volumes/*/

# Clean up old files
docker exec media-downloader-api python /app/cleanup_old_files.py

# Remove unused Docker images
docker image prune -a
```

### Issue: Worker not processing jobs

```bash
# Restart worker
docker-compose restart worker

# Check logs
docker logs media-downloader-worker

# Check if Redis is accessible
docker exec media-downloader-worker redis-cli -h redis PING
```

---

## Scaling (For High Traffic)

### Horizontal Scaling

```yaml
# docker-compose.yml
worker:
  # ... existing config ...
  deploy:
    replicas: 4  # Run 4 worker instances
```

Or manually:
```bash
docker-compose up -d --scale worker=4
```

### Use S3 for Storage

Instead of local storage, save to S3:

```python
# After download completes, upload to S3
import boto3

s3 = boto3.client('s3')
s3.upload_file(local_file, 'my-bucket', f'downloads/{job_id}/file.mp4')

# Serve download via S3 presigned URL
url = s3.generate_presigned_url('get_object',
    Params={'Bucket': 'my-bucket', 'Key': f'downloads/{job_id}/file.mp4'},
    ExpiresIn=3600)  # URL valid for 1 hour
```

---

## Cost Optimization

### 1. Auto-cleanup
- Delete files after 24 hours (saves storage)
- Users must download within 24 hours

### 2. Compression
- Compress files before serving (saves bandwidth)

### 3. CDN
- Use CloudFlare or similar CDN to cache static assets
- Reduce VPS bandwidth usage

---

## Summary

✅ **VPS downloads videos** (not user's machine)
✅ **Users download FROM VPS** (clicking "Download" button)
✅ **Files stored in Docker volume** (persistent)
✅ **Auto-cleanup recommended** (prevent disk full)
✅ **Nginx recommended** (reverse proxy, SSL, timeouts)
✅ **Security measures** (rate limiting, auth, firewall)

**You understood it perfectly!** The flow you described is exactly how it works! 🎯
