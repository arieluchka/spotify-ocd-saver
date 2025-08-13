from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import IntEnum


class SongStatus(IntEnum):
    """Status of song scanning for trigger words"""
    NOT_SCANNED = 0
    SCANNED_CLEAN = 1
    SCANNED_CONTAMINATED = 2


@dataclass
class Song:
    """Represents a song in the database"""
    id: Optional[int] = None
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_ms: int = 0
    status: SongStatus = SongStatus.NOT_SCANNED
    spotify_id: Optional[str] = None
    isrc: Optional[str] = None
    lrclib_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class TriggerTimestamp:
    """Represents a trigger word timestamp in a song"""
    id: Optional[int] = None
    trigger_id: int = 0
    song_id: int = 0
    start_time_ms: int = 0
    end_time_ms: int = 0
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
