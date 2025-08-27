import requests
from typing import Optional, List
import logging
import json

from services.lyrics_finder_service.lyrics_searcher_interface import LyricsSearcherInterface, LyricsSearchResult
from common.models.models import SyncedLyricsLine

logger = logging.getLogger(__name__)


class MusixMatchSearcher(LyricsSearcherInterface):
    """MusixMatch API implementation for lyrics searching"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.musixmatch.com/ws/1.1"
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Spotify-OCD-Saver/1.0'
        })
        
        if not self.api_key:
            logger.warning("MusixMatch: No API key provided, functionality will be limited")
    
    def search_synced_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """Search for synced lyrics from MusixMatch API"""
        logger.debug(f"MusixMatch: Searching synced lyrics for {artist} - {title}")
        
        if not self.api_key:
            logger.error("MusixMatch: API key required for synced lyrics")
            return LyricsSearchResult(found=False, source="MusixMatch")
        
        try:
            # First, search for the track
            track_id = self._search_track(artist, title, album, duration_ms)
            
            if not track_id:
                logger.debug("MusixMatch: Track not found")
                return LyricsSearchResult(found=False, source="MusixMatch")
            
            # Get synced lyrics for the track
            synced_lyrics = self._get_synced_lyrics(track_id)
            
            if synced_lyrics:
                return LyricsSearchResult(
                    found=True,
                    synced_lyrics=synced_lyrics,
                    source="MusixMatch",
                    track_id=str(track_id)
                )
            else:
                logger.debug("MusixMatch: No synced lyrics found for track")
                return LyricsSearchResult(found=False, source="MusixMatch")
                
        except requests.RequestException as e:
            logger.error(f"MusixMatch API request failed: {e}")
            return LyricsSearchResult(found=False, source="MusixMatch")
        except Exception as e:
            logger.error(f"MusixMatch parsing error: {e}")
            return LyricsSearchResult(found=False, source="MusixMatch")
    
    def search_plain_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> LyricsSearchResult:
        """Search for plain lyrics from MusixMatch API"""
        logger.debug(f"MusixMatch: Searching plain lyrics for {artist} - {title}")
        
        if not self.api_key:
            logger.error("MusixMatch: API key required for lyrics")
            return LyricsSearchResult(found=False, source="MusixMatch")
        
        try:
            # First, search for the track
            track_id = self._search_track(artist, title, album, duration_ms)
            
            if not track_id:
                logger.debug("MusixMatch: Track not found")
                return LyricsSearchResult(found=False, source="MusixMatch")
            
            # Get plain lyrics for the track
            plain_lyrics = self._get_plain_lyrics(track_id)
            
            if plain_lyrics:
                return LyricsSearchResult(
                    found=True,
                    plain_lyrics=plain_lyrics,
                    source="MusixMatch",
                    track_id=str(track_id)
                )
            else:
                logger.debug("MusixMatch: No plain lyrics found for track")
                return LyricsSearchResult(found=False, source="MusixMatch")
                
        except requests.RequestException as e:
            logger.error(f"MusixMatch API request failed: {e}")
            return LyricsSearchResult(found=False, source="MusixMatch")
        except Exception as e:
            logger.error(f"MusixMatch parsing error: {e}")
            return LyricsSearchResult(found=False, source="MusixMatch")
    
    def _search_track(
        self, 
        artist: str, 
        title: str, 
        album: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> Optional[int]:
        """Search for track ID using MusixMatch API"""
        params = {
            'apikey': self.api_key,
            'q_artist': artist,
            'q_track': title,
            'page_size': 5,
            'page': 1,
            's_track_rating': 'desc'  # Sort by rating
        }
        
        if album:
            params['q_album'] = album
        
        response = self.session.get(f"{self.base_url}/track.search", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if (data.get('message', {}).get('header', {}).get('status_code') == 200 and 
            data.get('message', {}).get('body', {}).get('track_list')):
            
            tracks = data['message']['body']['track_list']
            
            if tracks:
                # Return the first (best matching) track ID
                track_id = tracks[0]['track']['track_id']
                logger.debug(f"MusixMatch: Found track ID {track_id}")
                return track_id
        
        return None
    
    def _get_synced_lyrics(self, track_id: int) -> Optional[List[SyncedLyricsLine]]:
        """Get synced lyrics for a track ID"""
        params = {
            'apikey': self.api_key,
            'track_id': track_id
        }
        
        response = self.session.get(f"{self.base_url}/track.subtitle.get", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if (data.get('message', {}).get('header', {}).get('status_code') == 200 and 
            data.get('message', {}).get('body', {}).get('subtitle')):
            
            subtitle_body = data['message']['body']['subtitle']['subtitle_body']
            
            if subtitle_body:
                return self._parse_musixmatch_subtitle(subtitle_body)
        
        return None
    
    def _get_plain_lyrics(self, track_id: int) -> Optional[str]:
        """Get plain lyrics for a track ID"""
        params = {
            'apikey': self.api_key,
            'track_id': track_id
        }
        
        response = self.session.get(f"{self.base_url}/track.lyrics.get", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if (data.get('message', {}).get('header', {}).get('status_code') == 200 and 
            data.get('message', {}).get('body', {}).get('lyrics')):
            
            lyrics_body = data['message']['body']['lyrics']['lyrics_body']
            
            if lyrics_body:
                # Remove MusixMatch footer if present
                lyrics_body = lyrics_body.replace(
                    "******* This Lyrics is NOT for Commercial use *******", ""
                ).strip()
                
                return lyrics_body if lyrics_body else None
        
        return None
    
    def _parse_musixmatch_subtitle(self, subtitle_body: str) -> List[SyncedLyricsLine]:
        """Parse MusixMatch subtitle format into SyncedLyricsLine objects"""
        lines = []
        
        try:
            # MusixMatch subtitle format is JSON
            subtitle_data = json.loads(subtitle_body)
            
            if isinstance(subtitle_data, list):
                for item in subtitle_data:
                    if isinstance(item, dict) and 'time' in item and 'text' in item:
                        # Convert seconds to milliseconds
                        timestamp_ms = int(float(item['time']['total']) * 1000)
                        lyrics_text = item['text'].strip()
                        
                        if lyrics_text:  # Skip empty lyrics
                            lines.append(SyncedLyricsLine(
                                start_timestamp=timestamp_ms,
                                line=lyrics_text
                            ))
            
            logger.debug(f"MusixMatch: Parsed {len(lines)} synced lyrics lines")
            return lines
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"MusixMatch subtitle parsing error: {e}")
            return []