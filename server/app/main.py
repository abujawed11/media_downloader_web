from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import media
from .config import settings

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
