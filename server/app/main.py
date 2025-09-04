from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import media

app = FastAPI(title="MediaDownloader API", version="0.1.0")

# allow your dev site and multiple ports/IPs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",  # Vite started on 5174
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://10.20.2.78:5173", # WSL IP
        "http://10.20.2.78:5174",
        "http://93.127.199.118",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)
