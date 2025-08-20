from typing import Optional, List
import logging

from services.lyrics_finder_service.lyrics_searcher_interface import LyricsSearcherInterface, LyricsSearchResult

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


if __name__ == '__main__':
    from services.lyrics_finder_service.lyrics_apis.lrclib_searcher import LRCLibSearcher
    import concurrent.futures
    import datetime

    songs_list = [
        ("Angry Sea",	"Mother Mother",	"Touch Up",	185360),
        ("Arms Tonite",	"Mother Mother",	"O My Heart",	216666),
        ("Body Of Years",	"Mother Mother",	"O My Heart",	278400),
        ("Burning Pile",	"Mother Mother",	"O My Heart",	262173),
        ("Dirty Town",	"Mother Mother",	"Touch Up",	152800),
        ("Do It All The Time",	"I DONT KNOW HOW BUT THEY FOUND ME",	"Do It All The Time",	167803),
        ("Next Semester",	"Twenty One Pilots",	"Clancy",	234400),
        ("O My Heart",	"Mother Mother",	"O My Heart",	211453),
        ("Oh Ana",	"Mother Mother",	"Touch Up",	197080),
        ("Overcompensate",	"Twenty One Pilots",	"Clancy",	236000),
        ("Polynesia",	"Mother Mother",	"Touch Up",	139973),
        ("Routines In The Night",	"Twenty One Pilots",	"Clancy",	202600),
        ("SIXFT",	"I DONT KNOW HOW BUT THEY FOUND ME",	"GLOOM DIVISION",	204642),
        ("Try To Change",	"Mother Mother",	"O My Heart",	241666),
        ("Vignette",	"Twenty One Pilots",	"Clancy",	202133),
        ("Wisdom",	"Mother Mother",	"O My Heart",	207960)
    ]


    lyrics_service = LyricsFinderService(LRCLibSearcher())

    start = datetime.datetime.now()
    lrc = lyrics_service
    all_lyricses = []

    def fetch_lyrics(song):
        return lrc.find_synced_lyrics(
            title=song[0],
            artist=song[1],
            album=song[2],
            duration_ms=song[3]
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_lyrics, songs_list))

    for lyr in results:
        print(lyr)
        all_lyricses.append(lyr)

    print(all_lyricses)
    print(len(all_lyricses))
    print(f"full time is: {datetime.datetime.now() - start}")