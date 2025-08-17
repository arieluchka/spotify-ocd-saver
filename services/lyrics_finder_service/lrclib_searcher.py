import requests
from typing import Optional, List
import logging
import json

from .lyrics_searcher_interface import LyricsSearcherInterface, LyricsSearchResult
from config.models import SyncedLyricsLine

logger = logging.getLogger(__name__)


class LRCLibSearcher(LyricsSearcherInterface):
    """LRCLib API implementation for lyrics searching"""
    
    def __init__(self):
        self.base_url = "https://lrclib.net/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Spotify-OCD-Saver/1.0'
        })
    
    def search_synced_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """Search for synced lyrics from LRCLib API"""
        logger.debug(f"LRCLib: Searching synced lyrics for {artist} - {title}")
        
        try:
            # Build search parameters
            params = {
                'artist_name': artist,
                'track_name': title
            }
            
            if album:
                params['album_name'] = album
            
            if duration_ms:
                params['duration'] = duration_ms // 1000  # Convert to seconds
            
            # Make API request
            response = self.session.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            
            results = response.json()
            
            if not results:
                logger.debug("LRCLib: No results found")
                return LyricsSearchResult(found=False, source="LRCLib")
            
            # Find best match with synced lyrics
            for result in results:
                if result.get('syncedLyrics'):
                    synced_lyrics = self._parse_lrc_content(result['syncedLyrics'])
                    
                    return LyricsSearchResult(
                        found=True,
                        synced_lyrics=synced_lyrics,
                        source="LRCLib",
                        track_id=str(result.get('id', ''))
                    )
            
            logger.debug("LRCLib: No synced lyrics found in results")
            return LyricsSearchResult(found=False, source="LRCLib")
            
        except requests.RequestException as e:
            logger.error(f"LRCLib API request failed: {e}")
            return LyricsSearchResult(found=False, source="LRCLib")
        except Exception as e:
            logger.error(f"LRCLib parsing error: {e}")
            return LyricsSearchResult(found=False, source="LRCLib")
    
    def search_plain_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """Search for plain lyrics from LRCLib API"""
        logger.debug(f"LRCLib: Searching plain lyrics for {artist} - {title}")
        
        try:
            # Build search parameters
            params = {
                'artist_name': artist,
                'track_name': title
            }
            
            if album:
                params['album_name'] = album
            
            if duration_ms:
                params['duration'] = duration_ms // 1000  # Convert to seconds
            
            # Make API request
            response = self.session.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            
            results = response.json()
            
            if not results:
                logger.debug("LRCLib: No results found")
                return LyricsSearchResult(found=False, source="LRCLib")
            
            # Find best match with plain lyrics
            for result in results:
                if result.get('plainLyrics'):
                    return LyricsSearchResult(
                        found=True,
                        plain_lyrics=result['plainLyrics'],
                        source="LRCLib",
                        track_id=str(result.get('id', ''))
                    )
            
            logger.debug("LRCLib: No plain lyrics found in results")
            return LyricsSearchResult(found=False, source="LRCLib")
            
        except requests.RequestException as e:
            logger.error(f"LRCLib API request failed: {e}")
            return LyricsSearchResult(found=False, source="LRCLib")
        except Exception as e:
            logger.error(f"LRCLib parsing error: {e}")
            return LyricsSearchResult(found=False, source="LRCLib")
    
    def _parse_lrc_content(self, lrc_content: str) -> List[SyncedLyricsLine]:
        """Parse LRC format content into SyncedLyricsLine objects"""
        lines = []
        
        for line in lrc_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Parse LRC format: [mm:ss.xx]lyrics
            import re
            match = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)', line)
            
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                centiseconds = int(match.group(3))
                lyrics_text = match.group(4).strip()
                
                # Convert to milliseconds
                timestamp_ms = (minutes * 60 + seconds) * 1000 + centiseconds * 10
                
                if lyrics_text:  # Skip empty lyrics
                    lines.append(SyncedLyricsLine(
                        start_timestamp=timestamp_ms,
                        line=lyrics_text
                    ))
        
        logger.debug(f"LRCLib: Parsed {len(lines)} synced lyrics lines")
        return lines