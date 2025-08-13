"""
Data models for Spotify OCD Saver
Defines dataclasses for database entities
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TriggerWordCategory:
    """Represents a category of trigger words"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TriggerWord:
    """Represents a trigger word"""
    id: Optional[int] = None
    word: str = ""
    category_id: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class StreamingService:
    """Represents a streaming service"""
    id: Optional[int] = None
    name: str = ""
    api_endpoint: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class LyricsService:
    """Represents a lyrics service"""
    id: Optional[int] = None
    name: str = ""
    api_endpoint: Optional[str] = None
    is_active: bool = True
    priority: int = 1
    created_at: Optional[datetime] = None


@dataclass
class Song:
    """Represents a song"""
    id: Optional[int] = None
    title: str = ""
    artist: str = ""
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    spotify_id: Optional[str] = None
    isrc: Optional[str] = None
    lrclib_id: Optional[str] = None
    lyrics_service_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TriggerTimestamp:
    """Represents a timestamp where a trigger word occurs in a song"""
    id: Optional[int] = None
    song_id: int = 0
    trigger_word_id: int = 0
    start_time_ms: int = 0
    end_time_ms: int = 0
    line_text: Optional[str] = None
    created_at: Optional[datetime] = None
