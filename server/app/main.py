from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import media
from .config import settings
import os

app = FastAPI(title="MediaDownloader API", version="0.1.0")

# CORS configuration from environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)


@app.on_event("startup")
async def startup_event():
    """Verify downloads directory on startup."""
    downloads_dir = os.path.abspath(settings.YTDLP_OUTPUT_PATH)
    print(f"[INFO] Starting MediaDownloader API")
    print(f"[INFO] Downloads directory: {downloads_dir}")

    # Create directory if it doesn't exist
    os.makedirs(downloads_dir, exist_ok=True)

    # Verify it's writable
    try:
        test_file = os.path.join(downloads_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print(f"[INFO] Downloads directory is writable ✓")
    except Exception as e:
        print(f"[ERROR] Downloads directory is not writable: {e}")
        print(f"[ERROR] This will cause download failures!")


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
    except:
        pass

    return {
        "status": "healthy" if is_writable else "degraded",
        "downloads_dir": downloads_dir,
        "downloads_dir_writable": is_writable,
        "downloads_dir_exists": os.path.isdir(downloads_dir),
    }
