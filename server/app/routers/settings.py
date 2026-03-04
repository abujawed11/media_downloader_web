"""Settings API — persists user preferences in Redis."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
import redis

from ..config import settings

router = APIRouter()

STORAGE_TYPE_KEY = "settings:storage_type"
VALID_TYPES = {"local", "s3", "minio"}

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class StorageSettingResponse(BaseModel):
    storage_type: str


class StorageSettingUpdate(BaseModel):
    storage_type: Literal["local", "s3", "minio"]


@router.get("/storage", response_model=StorageSettingResponse)
async def get_storage_setting():
    """Return the active storage type (Redis override or env default)."""
    val = redis_client.get(STORAGE_TYPE_KEY)
    if val in VALID_TYPES:
        return {"storage_type": val}
    return {"storage_type": settings.STORAGE_TYPE}


@router.put("/storage", response_model=StorageSettingResponse)
async def set_storage_setting(body: StorageSettingUpdate):
    """Persist a new storage type to Redis."""
    redis_client.set(STORAGE_TYPE_KEY, body.storage_type)
    return {"storage_type": body.storage_type}
