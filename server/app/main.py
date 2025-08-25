from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import media

app = FastAPI(title="MediaDownloader API", version="0.1.0")

# allow your dev site
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)
