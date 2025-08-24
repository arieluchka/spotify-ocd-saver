from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import IntEnum


class SongStatus(IntEnum):
    """General lyrics status for a song (user-agnostic)"""
    NOT_SCANNED = 0          # No attempt to fetch lyrics yet
    NO_RESULTS = 1           # No lyrics found from providers
    PLAIN_LYRICS = 2         # Plain (unsynced) lyrics available
    SYNC_LYRICS = 3          # Synced (timestamped) lyrics available

@dataclass
class SyncedLyricsLine:
    """Represents a single line of synced lyrics"""
    start_timestamp: int  # in milliseconds
    line: str
    
    def __post_init__(self):
        # Ensure timestamp is non-negative
        if self.start_timestamp < 0:
            self.start_timestamp = 0


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
    not_sync_lrclib_id: Optional[str] = None  # For non-synced lyrics
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
    category_id: int = 0  # Keep as category_id to match database schema
    song_id: int = 0
    user_id: Optional[int] = None  # Track which user triggered this
    start_time_ms: int = 0
    end_time_ms: int = 0
    trigger_word: Optional[str] = None  # The specific word that triggered
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TriggerScanStatus(IntEnum):
    """Per-user trigger scan result for a song"""
    NOT_SCANNED = 0
    SCANNED_CLEAN = 1
    SCANNED_CONTAMINATED = 2


@dataclass
class UserSongStatus:
    """Tracks a user's trigger scan status for a specific song"""
    id: Optional[int] = None
    song_id: int = 0
    user_id: int = 0
    trigger_scan_status: TriggerScanStatus = TriggerScanStatus.NOT_SCANNED
    sync: bool = False  # True if scan used synced lyrics
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class User:
    """Represents a user in the system"""
    id: Optional[int] = None
    spotify_user_id: str = ""
    display_name: str = ""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class TriggerCategory:
    """Represents a category of trigger words"""
    id: Optional[int] = None
    name: str = ""
    words: List[str] = None  # JSON list of trigger words
    user_id: Optional[int] = None  # None for global categories
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.words is None:
            self.words = []
