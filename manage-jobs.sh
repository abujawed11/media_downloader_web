#!/bin/bash
# Job Management Script for Media Downloader

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_help() {
    echo "Media Downloader - Job Management Script"
    echo ""
    echo "Usage: ./manage-jobs.sh [command]"
    echo ""
    echo "Commands:"
    echo "  list          - List all jobs in Redis"
    echo "  clean         - Clean up all jobs (stop tasks and clear Redis)"
    echo "  cancel-all    - Cancel all running Celery tasks"
    echo "  status        - Show worker and Redis status"
    echo "  logs-api      - Show API container logs"
    echo "  logs-worker   - Show worker container logs"
    echo "  restart       - Restart API and worker containers"
    echo ""
}

list_jobs() {
    echo -e "${GREEN}Listing all jobs in Redis:${NC}"
    docker exec media-downloader-redis redis-cli SMEMBERS "jobs:all"

    echo ""
    echo -e "${GREEN}Job details:${NC}"
    docker exec media-downloader-api python -c "
import redis
from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
job_ids = redis_client.smembers('jobs:all')

print(f'Total jobs: {len(job_ids)}\n')

for job_id in job_ids:
    job_key = f'job:{job_id}'
    job_data = redis_client.hgetall(job_key)

    if job_data:
        url = job_data.get('url', 'N/A')
        # Truncate URL if too long
        if len(url) > 60:
            url = url[:57] + '...'

        print(f'Job: {job_id}')
        print(f'  URL: {url}')

        # Check flags
        pause_key = f'job:{job_id}:pause'
        cancel_key = f'job:{job_id}:cancel'

        if redis_client.exists(pause_key):
            print(f'  Status: PAUSED ⏸')
        if redis_client.exists(cancel_key):
            print(f'  Status: CANCELED ❌')
        print()
"
}

clean_all() {
    echo -e "${YELLOW}⚠ This will stop all downloads and clear all jobs!${NC}"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi

    echo -e "${GREEN}Revoking all Celery tasks...${NC}"
    docker exec media-downloader-api python -c "
from celery import Celery
from app.config import settings
import redis

celery_app = Celery('app', broker=settings.CELERY_BROKER_URL)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

job_ids = redis_client.smembers('jobs:all')
print(f'Revoking {len(job_ids)} tasks...')

for job_id in job_ids:
    celery_app.control.revoke(job_id, terminate=True, signal='SIGKILL')
    print(f'  ✓ Revoked {job_id}')

print('Done!')
"

    echo -e "${GREEN}Clearing Redis data...${NC}"
    docker exec media-downloader-redis redis-cli FLUSHDB

    echo -e "${GREEN}✅ All jobs cleaned up!${NC}"
}

cancel_all_tasks() {
    echo -e "${GREEN}Canceling all running tasks...${NC}"
    docker exec media-downloader-api python -c "
from celery import Celery
from app.config import settings
import redis

celery_app = Celery('app', broker=settings.CELERY_BROKER_URL)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

job_ids = redis_client.smembers('jobs:all')
print(f'Canceling {len(job_ids)} tasks...')

for job_id in job_ids:
    celery_app.control.revoke(job_id, terminate=True, signal='SIGKILL')
    print(f'  ✓ Canceled {job_id}')

print('✅ All tasks canceled!')
"
}

show_status() {
    echo -e "${GREEN}=== Redis Status ===${NC}"
    docker exec media-downloader-redis redis-cli PING || echo "Redis not responding"

    echo ""
    echo -e "${GREEN}=== Worker Status ===${NC}"
    docker exec media-downloader-worker celery -A app.celery_app inspect active || echo "No active tasks"

    echo ""
    echo -e "${GREEN}=== Container Status ===${NC}"
    docker ps | grep media
}

logs_api() {
    docker logs -f media-downloader-api
}

logs_worker() {
    docker logs -f media-downloader-worker
}

restart_containers() {
    echo -e "${GREEN}Restarting API and worker containers...${NC}"
    cd "$(dirname "$0")"
    docker-compose restart api worker
    echo -e "${GREEN}✅ Containers restarted!${NC}"
}

# Main
case "${1:-help}" in
    list)
        list_jobs
        ;;
    clean)
        clean_all
        ;;
    cancel-all)
        cancel_all_tasks
        ;;
    status)
        show_status
        ;;
    logs-api)
        logs_api
        ;;
    logs-worker)
        logs_worker
        ;;
    restart)
        restart_containers
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
