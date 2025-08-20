"""
Song-related API models for OCDify service
"""

from pydantic import BaseModel
from typing import Optional


class SongResponse(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    duration_ms: int
    status: str
    spotify_id: Optional[str]
    trigger_count: Optional[int] = None
    created_at: Optional[str]


class TriggerResponse(BaseModel):
    id: int
    trigger_word: Optional[str]
    start_time_ms: int
    end_time_ms: int
    category_id: int
    created_at: Optional[str]