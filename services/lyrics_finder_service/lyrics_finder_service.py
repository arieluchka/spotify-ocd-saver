from typing import Optional, List
import logging

from .lyrics_searcher_interface import LyricsSearcherInterface, LyricsSearchResult

logger = logging.getLogger(__name__)


class LyricsFinderService:
    """Service for finding lyrics using interchangeable API implementations"""
    
    def __init__(self, lyrics_searcher: LyricsSearcherInterface):
        """
        Initialize with a lyrics searcher implementation.
        
        Args:
            lyrics_searcher: Implementation of LyricsSearcherInterface
        """
        self.lyrics_searcher = lyrics_searcher
        logger.info(f"LyricsFinderService initialized with searcher: {type(lyrics_searcher).__name__}")
    
    def set_searcher(self, lyrics_searcher: LyricsSearcherInterface):
        """
        Switch to a different lyrics searcher implementation.
        
        Args:
            lyrics_searcher: New implementation of LyricsSearcherInterface
        """
        old_searcher = type(self.lyrics_searcher).__name__
        self.lyrics_searcher = lyrics_searcher
        logger.info(f"Switched lyrics searcher from {old_searcher} to {type(lyrics_searcher).__name__}")
    
    def find_synced_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """
        Find synced lyrics with timestamps.
        
        Args:
            artist: Artist name
            title: Song title
            album: Album name (optional)
            duration_ms: Song duration in milliseconds (optional)
            
        Returns:
            LyricsSearchResult with synced lyrics if found
        """
        logger.info(f"Searching for synced lyrics: {artist} - {title}")
        
        try:
            result = self.lyrics_searcher.search_synced_lyrics(artist, title, album, duration_ms)
            
            if result.found and result.synced_lyrics:
                logger.info(f"Found synced lyrics for '{title}' by {artist} from {result.source}")
                logger.debug(f"Synced lyrics contain {len(result.synced_lyrics)} lines")
            else:
                logger.info(f"No synced lyrics found for '{title}' by {artist}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error searching for synced lyrics: {e}")
            return LyricsSearchResult(
                found=False,
                source=type(self.lyrics_searcher).__name__
            )
    
    def find_plain_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """
        Find plain text lyrics without timestamps.
        
        Args:
            artist: Artist name
            title: Song title
            album: Album name (optional)
            duration_ms: Song duration in milliseconds (optional)
            
        Returns:
            LyricsSearchResult with plain lyrics if found
        """
        logger.info(f"Searching for plain lyrics: {artist} - {title}")
        
        try:
            result = self.lyrics_searcher.search_plain_lyrics(artist, title, album, duration_ms)
            
            if result.found and result.plain_lyrics:
                logger.info(f"Found plain lyrics for '{title}' by {artist} from {result.source}")
                logger.debug(f"Plain lyrics length: {len(result.plain_lyrics)} characters")
            else:
                logger.info(f"No plain lyrics found for '{title}' by {artist}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error searching for plain lyrics: {e}")
            return LyricsSearchResult(
                found=False,
                source=type(self.lyrics_searcher).__name__
            )
    
    def find_any_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None,
        prefer_synced: bool = True
    ) -> LyricsSearchResult:
        """
        Find any available lyrics, trying synced first by default.
        
        Args:
            artist: Artist name
            title: Song title
            album: Album name (optional)
            duration_ms: Song duration in milliseconds (optional)
            prefer_synced: Whether to try synced lyrics first
            
        Returns:
            LyricsSearchResult with any available lyrics
        """
        logger.info(f"Searching for any lyrics: {artist} - {title} (prefer_synced={prefer_synced})")
        
        if prefer_synced:
            # Try synced first
            result = self.find_synced_lyrics(artist, title, album, duration_ms)
            if result.found:
                return result
            
            # Fallback to plain
            logger.info("Synced lyrics not found, trying plain lyrics...")
            return self.find_plain_lyrics(artist, title, album, duration_ms)
        else:
            # Try plain first
            result = self.find_plain_lyrics(artist, title, album, duration_ms)
            if result.found:
                return result
            
            # Fallback to synced
            logger.info("Plain lyrics not found, trying synced lyrics...")
            return self.find_synced_lyrics(artist, title, album, duration_ms)