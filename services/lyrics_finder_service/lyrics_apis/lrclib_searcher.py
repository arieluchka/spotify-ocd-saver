import datetime
import time
import warnings

import requests
from typing import Optional, List
import logging
import json

from Tools.scripts.highlight import alltt_escape

from services.lyrics_finder_service.lyrics_searcher_interface import LyricsSearcherInterface, LyricsSearchResult
from config.models import SyncedLyricsLine

logger = logging.getLogger(__name__)
from lrclib import LrcLibAPI

class LRCLibSearcher(LyricsSearcherInterface):
    def __init__(self):
        self.name = "LRCLib"
        self._client = LrcLibAPI(
            user_agent="OCDify/0.0.1"
        )

    def __build_return_object(
            self,
            found: bool,
            synced_lyrics: Optional[List[SyncedLyricsLine]] = None,
            plain_lyrics: Optional[str] = None,
            track_id: Optional[str] = None  # ID from the source API
    ):
        if not found:
            return LyricsSearchResult(
                found=False,
                source=self.name
            )

        elif synced_lyrics:
            return LyricsSearchResult(
                found=True,
                synced_lyrics=synced_lyrics,
                source=self.name,
                track_id=track_id
            )
        elif plain_lyrics:
            return LyricsSearchResult(
                found=True,
                plain_lyrics=plain_lyrics,
                source=self.name,
                track_id=track_id
            )
        else:
            ... #todo: some error?

    def search_synced_lyrics(
        self, 
        artist: str, 
        title: str, 
        album: str,
        duration_ms: int
    ) -> LyricsSearchResult|bool:
        """Search for synced lyrics from LRCLib API"""

        logger.debug(f"LRCLib: Searching synced lyrics for {artist} - {title}")
        
        try:
            duration = duration_ms // 1000
            
            res = self._client.get_lyrics(
                track_name=title,
                artist_name=artist,
                album_name=album,
                duration=duration,
            )
            if not res.synced_lyrics: #todo: make smarter search
                res = self._client.search_lyrics(
                    track_name=title,
                    artist_name=artist,
                    # album_name=album
                )
                for song_res in res:
                    if song_res.synced_lyrics and (duration - 2) <= song_res.duration <= (duration + 2):
                        res = song_res
                        break
                else:
                    logger.warning("")
                    return False
                # todo: wider seach with "search_lyrics" (with log)
                #   if unsuccesful, return false and log

            return self.__build_return_object(
                found=True,
                synced_lyrics=self._parse_lrc_content(res.synced_lyrics),
                track_id=str(res.id),
            )
            
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
        warnings.warn("Not implemented yet", UserWarning)
        # """Search for plain lyrics from LRCLib API"""
        # logger.debug(f"LRCLib: Searching plain lyrics for {artist} - {title}")
        #
        # try:
        #     # Build search parameters
        #     params = {
        #         'artist_name': artist,
        #         'track_name': title
        #     }
        #
        #     if album:
        #         params['album_name'] = album
        #
        #     if duration_ms:
        #         params['duration'] = duration_ms // 1000  # Convert to seconds
        #
        #     # Make API request
        #     response = self.session.get(f"{self.base_url}/search", params=params)
        #     response.raise_for_status()
        #
        #     results = response.json()
        #
        #     if not results:
        #         logger.debug("LRCLib: No results found")
        #         return LyricsSearchResult(found=False, source="LRCLib")
        #
        #     # Find best match with plain lyrics
        #     for result in results:
        #         if result.get('plainLyrics'):
        #             return LyricsSearchResult(
        #                 found=True,
        #                 plain_lyrics=result['plainLyrics'],
        #                 source="LRCLib",
        #                 track_id=str(result.get('id', ''))
        #             )
        #
        #     logger.debug("LRCLib: No plain lyrics found in results")
        #     return LyricsSearchResult(found=False, source="LRCLib")
        #
        # except requests.RequestException as e:
        #     logger.error(f"LRCLib API request failed: {e}")
        #     return LyricsSearchResult(found=False, source="LRCLib")
        # except Exception as e:
        #     logger.error(f"LRCLib parsing error: {e}")
        #     return LyricsSearchResult(found=False, source="LRCLib")
    
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

if __name__ == '__main__':
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

    import concurrent.futures

    start = datetime.datetime.now()
    lrc = LRCLibSearcher()
    all_lyricses = []

    def fetch_lyrics(song):
        return lrc.search_synced_lyrics(
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