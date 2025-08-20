"""
Utility-related API models for OCDify service
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class LyricsScanRequest(BaseModel):
    lyrics: str = Field(..., description="Lyrics text to scan for triggers")


class LyricsScanResponse(BaseModel):
    has_triggers: bool
    trigger_count: int
    triggers: List[Dict[str, Any]]


class StatsResponse(BaseModel):
    total_songs: int
    total_triggers: int
    contaminated_songs: int
    clean_songs: int
    unscanned_songs: int
    user_categories: int
    monitoring_active: bool