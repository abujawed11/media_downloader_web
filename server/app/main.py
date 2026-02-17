from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import media
from .routers import media_library
from .config import settings
import os
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup → yield → shutdown."""
    # ── Startup ──────────────────────────────────────────────────────────────
    print("[INFO] Starting MediaDownloader API")

    # Ensure downloads directory exists and is writable
    downloads_dir = os.path.abspath(settings.YTDLP_OUTPUT_PATH)
    os.makedirs(downloads_dir, exist_ok=True)
    try:
        test_file = os.path.join(downloads_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print(f"[INFO] Downloads directory writable: {downloads_dir} ✓")
    except Exception as e:
        print(f"[ERROR] Downloads directory not writable: {e}")

    # Ensure local media storage directory exists
    storage_path = os.path.abspath(settings.LOCAL_STORAGE_PATH)
    os.makedirs(os.path.join(storage_path, "videos"), exist_ok=True)
    os.makedirs(os.path.join(storage_path, "thumbnails"), exist_ok=True)
    print(f"[INFO] Media storage directory: {storage_path} ✓")

    # Initialize database (create tables if not present)
    try:
        from .database import init_db
        await init_db()
        print("[INFO] Database tables initialised ✓")
    except Exception as exc:
        print(f"[WARNING] Database init failed (PostgreSQL may not be configured): {exc}")
        print("[WARNING] Media library features will be unavailable.")

    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("[INFO] Shutting down MediaDownloader API")


app = FastAPI(title="MediaDownloader API", version="0.2.0", lifespan=lifespan)

# CORS configuration from environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(media.router)
app.include_router(media_library.router)

# ── Static file serving for local media storage ───────────────────────────── #
_storage_path = os.path.abspath(settings.LOCAL_STORAGE_PATH)
os.makedirs(_storage_path, exist_ok=True)
app.mount("/media-storage", StaticFiles(directory=_storage_path), name="media-storage")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    downloads_dir = os.path.abspath(settings.YTDLP_OUTPUT_PATH)
    is_writable = False
    try:
        test_file = os.path.join(downloads_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        is_writable = True
    except Exception:
        pass

    db_ok = False
    try:
        from .database import async_engine
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if is_writable else "degraded",
        "downloads_dir": downloads_dir,
        "downloads_dir_writable": is_writable,
        "downloads_dir_exists": os.path.isdir(downloads_dir),
        "database_connected": db_ok,
    }
