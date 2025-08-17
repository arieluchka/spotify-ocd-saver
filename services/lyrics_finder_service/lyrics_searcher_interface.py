from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass

from config.models import SyncedLyricsLine


@dataclass
class LyricsSearchResult:
    """Result from lyrics search"""
    found: bool
    synced_lyrics: Optional[List[SyncedLyricsLine]] = None
    plain_lyrics: Optional[str] = None
    source: Optional[str] = None  # Name of the API source
    track_id: Optional[str] = None  # ID from the source API


class LyricsSearcherInterface(ABC):
    """Interface for lyrics searcher implementations"""
    
    @abstractmethod
    def search_synced_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """
        Search for synced lyrics with timestamps.
        
        Args:
            artist: Artist name
            title: Song title
            album: Album name (optional)
            duration_ms: Song duration in milliseconds (optional)
            
        Returns:
            LyricsSearchResult with synced lyrics if found
        """
        pass
    
    @abstractmethod
    def search_plain_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """
        Search for plain text lyrics without timestamps.
        
        Args:
            artist: Artist name
            title: Song title
            album: Album name (optional)
            duration_ms: Song duration in milliseconds (optional)
            
        Returns:
            LyricsSearchResult with plain lyrics if found
        """
        pass