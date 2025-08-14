import time
import re
import logging
import threading
from typing import Tuple, List, Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from lrclib import LrcLibAPI
from lrclib.models import Lyrics
from lrclib.exceptions import NotFoundError

from internal.secrets import CLIENT_SECRET, CLIENT_ID
from models import *
from database import get_database
from config.bad_words_list import death_words
# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spotify_ocd_saver.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

api = LrcLibAPI(user_agent="spotify-ocd-saver/0.1.0")
db = get_database()

# todo: fine grain the scopes needed
#https://developer.spotify.com/documentation/web-api/concepts/scopes
scopes = [
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-read-playback-state"
]


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri = "https://arieluchka.com",
    scope = scopes
))


class SyncLyricsScraper:
    """Scraper for synchronized lyrics"""
    
    def __init__(self, scrapers_list: list):
        self._scrapers_list = scrapers_list
        self._scraper = scrapers_list[0]

    def find_synced_lyrics_of_song(self, song: Song) -> Optional[Lyrics]:
        """Find synchronized lyrics for a song"""
        try:
            # First try get_lyrics
            song_lyrics_res = self._scraper.get_lyrics(
                track_name=song.title,
                artist_name=song.artist,
                album_name=song.album,
                duration=(song.duration_ms // 1000) + 1
            )
            
            # Check if we got synced lyrics
            if song_lyrics_res and song_lyrics_res.synced_lyrics:
                logger.debug(f"Found synced lyrics via get_lyrics for '{song.title}'")
                return song_lyrics_res
            else:
                logger.info(f"No synced lyrics in get_lyrics result for '{song.title}', trying search...")
                
        except NotFoundError:
            logger.info(f"get_lyrics failed for '{song.title}', trying search...")
        except Exception as e:
            logger.warning(f"Error in get_lyrics for '{song.title}': {e}, trying search...")
        
        # Fallback to search_lyrics
        try:
            search_results = self._scraper.search_lyrics(
                track_name=song.title,
                artist_name=song.artist,
                album_name=song.album
            )
            
            # Look for the first result with synced lyrics
            for result in search_results:
                if result.synced_lyrics:
                    logger.info(f"Found synced lyrics via search for '{song.title}' (result: {result.name})")
                    # Convert search result to full lyrics object
                    full_lyrics = self._scraper.get_lyrics_by_id(result.id)
                    if full_lyrics and full_lyrics.synced_lyrics:
                        return full_lyrics
            
            logger.warning(f"No synced lyrics found in search results for '{song.title}'")
            return None
            
        except NotFoundError:
            logger.warning(f"Search lyrics not found for '{song.title}' by {song.artist}")
            return None
        except Exception as e:
            logger.error(f"Error searching lyrics for '{song.title}': {e}")
            return None



def parse_lrc_timestamp(timestamp_str: str) -> int:
    """Parse LRC timestamp format [mm:ss.xx] to milliseconds"""
    # Remove brackets and split
    timestamp_str = timestamp_str.strip('[]')
    parts = timestamp_str.split(':')
    minutes = int(parts[0])
    
    # Handle seconds and centiseconds
    seconds_part = parts[1].split('.')
    seconds = int(seconds_part[0])
    centiseconds = int(seconds_part[1]) if len(seconds_part) > 1 else 0
    
    # Convert to milliseconds
    total_ms = (minutes * 60 + seconds) * 1000 + centiseconds * 10
    return total_ms


def process_song_for_trigger_words(song: Song, lyrics: Lyrics) -> List[Tuple[int, int]]:
    """
    Process song lyrics to find trigger words and return their timestamps.
    
    :param song: Song object
    :param lyrics: Lyrics object with synced lyrics
    :return: List of tuples (start_time_ms, end_time_ms) for trigger sections
    """
    if not lyrics.synced_lyrics:
        logger.warning(f"No synced lyrics found for {song.title} by {song.artist}")
        return []
    
    trigger_timestamps = []
    trigger_words_found = set()
    
    # Split lyrics into lines
    lines = lyrics.synced_lyrics.strip().split('\n')
    
    for i, line in enumerate(lines):
        # Parse timestamp and lyrics
        if not line.strip() or not line.startswith('['):
            continue
            
        try:
            # Extract timestamp and lyrics text
            timestamp_match = re.match(r'\[([^\]]+)\](.*)$', line)
            if not timestamp_match:
                continue
                
            timestamp_str = timestamp_match.group(1)
            lyrics_text = timestamp_match.group(2).strip()
            
            if not lyrics_text:  # Skip empty lines
                continue
            
            # Check for trigger words (case insensitive)
            lyrics_lower = lyrics_text.lower()
            line_has_trigger = False
            
            for trigger_word in death_words:
                # Use word boundaries to match whole words only
                pattern = r'\b' + re.escape(trigger_word.lower()) + r'\b'
                if re.search(pattern, lyrics_lower):
                    line_has_trigger = True
                    trigger_words_found.add(trigger_word)
                    logger.debug(f"Found trigger word '{trigger_word}' in line: {lyrics_text}")
                    break  # Only process this line once even if multiple triggers
            
            if line_has_trigger:
                start_time_ms = parse_lrc_timestamp(timestamp_str)
                
                # Find end time by looking at next line's timestamp
                end_time_ms = start_time_ms + 5000  # Default 5 second buffer
                
                # Try to find the next line with a timestamp
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if next_line and next_line.startswith('['):
                        next_timestamp_match = re.match(r'\[([^\]]+)\]', next_line)
                        if next_timestamp_match:
                            end_time_ms = parse_lrc_timestamp(next_timestamp_match.group(1))
                            break
                
                trigger_timestamps.append((start_time_ms, end_time_ms))
                logger.info(f"Added trigger timestamp: {start_time_ms}-{end_time_ms}ms for '{lyrics_text}'")
        
        except Exception as e:
            logger.warning(f"Error processing lyrics line '{line}': {e}")
            continue
    
    # Combine nearby trigger timestamps (less than 5 seconds apart)
    if trigger_timestamps:
        logger.info(f"Found {len(trigger_timestamps)} initial trigger sections in '{song.title}' by {song.artist}")
        
        # Sort timestamps by start time
        trigger_timestamps.sort(key=lambda x: x[0])
        
        # Combine nearby triggers
        combined_timestamps = []
        current_start, current_end = trigger_timestamps[0]
        
        for i in range(1, len(trigger_timestamps)):
            next_start, next_end = trigger_timestamps[i]
            
            # If less than 5 seconds between end of current and start of next
            if next_start - current_end < 5000:
                # Extend current trigger to include the next one
                current_end = max(current_end, next_end)
                logger.debug(f"Combined triggers: extending to {current_start}-{current_end}ms")
            else:
                # Gap is too large, save current trigger and start new one
                combined_timestamps.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        
        # Don't forget the last trigger
        combined_timestamps.append((current_start, current_end))
        
        if len(combined_timestamps) < len(trigger_timestamps):
            logger.info(f"Combined {len(trigger_timestamps)} triggers into {len(combined_timestamps)} sections")
            for i, (start, end) in enumerate(combined_timestamps):
                logger.info(f"  Combined trigger {i+1}: {start}-{end}ms ({(end-start)/1000:.1f}s)")
        
        trigger_timestamps = combined_timestamps
        logger.info(f"Final trigger sections: {len(trigger_timestamps)}")
        logger.info(f"Trigger words found: {', '.join(trigger_words_found)}")
    else:
        logger.info(f"No trigger words found in '{song.title}' by {song.artist}")
    
    return trigger_timestamps

def spotify_monitoring_thread():
    """
    Monitor Spotify playback and skip trigger words.
    Will run every second to check current playback status.
    """
    currently_played_song_id = None
    clean_song = True
    trigger_timestamps_list = []
    current_trigger_index = 0
    buffer_ms = 1000
    
    logger.info("Starting Spotify monitoring thread...")
    
    while True:
        try:
            # Get current playback state
            current_playback = sp.currently_playing()
            
            if not current_playback or not current_playback.get('item'):
                logger.debug("No song currently playing")
                time.sleep(1)
                continue
            
            current_song_spotify_id = current_playback['item']['id']
            current_timestamp = current_playback.get('progress_ms', 0)
            
            # Check if we have a new song
            if current_song_spotify_id != currently_played_song_id:
                logger.info(f"New song detected: {current_playback['item']['name']} by {current_playback['item']['artists'][0]['name']}")
                currently_played_song_id = current_song_spotify_id
                current_trigger_index = 0
                
                # Check if song exists in database
                db_song = db.get_song_by_spotify_id(current_song_spotify_id)
                
                if db_song:
                    logger.info(f"Song found in database with status: {db_song.status}")
                    
                    if db_song.status == SongStatus.SCANNED_CLEAN:
                        clean_song = True
                        trigger_timestamps_list = []
                        logger.info("Song is clean, no skipping needed")
                    elif db_song.status == SongStatus.SCANNED_CONTAMINATED:
                        clean_song = False
                        # Load trigger timestamps from database
                        triggers = db.get_triggers_of_song(db_song.id)
                        trigger_timestamps_list = [(t.start_time_ms, t.end_time_ms) for t in triggers]
                        logger.info(f"Song has {len(trigger_timestamps_list)} trigger sections")
                    else:  # NOT_SCANNED
                        clean_song = True  # Assume clean until scanned
                        trigger_timestamps_list = []
                        # Scan in background
                        threading.Thread(target=scan_song_in_background, args=(db_song,), daemon=True).start()
                else:
                    # Add new song to database
                    logger.info("Adding new song to database...")
                    new_song = Song(
                        title=current_playback['item']['name'],
                        artist=current_playback['item']['artists'][0]['name'],
                        album=current_playback['item']['album']['name'],
                        duration_ms=current_playback['item']['duration_ms'],
                        spotify_id=current_song_spotify_id,
                        status=SongStatus.NOT_SCANNED
                    )
                    
                    song_id = db.add_new_song(new_song)
                    new_song.id = song_id
                    clean_song = True  # Assume clean until scanned
                    trigger_timestamps_list = []
                    
                    # Scan in background
                    threading.Thread(target=scan_song_in_background, args=(new_song,), daemon=True).start()
            else:
                # Same song playing - check if scan status has changed for unscanned songs
                if clean_song and not trigger_timestamps_list:  # Only check if we think it's clean and have no triggers
                    db_song = db.get_song_by_spotify_id(currently_played_song_id)
                    if db_song and db_song.status == SongStatus.SCANNED_CONTAMINATED:
                        logger.info(f"Song scan completed. Now marked as contaminated.")
                        clean_song = False
                        # Load trigger timestamps from database
                        triggers = db.get_triggers_of_song(db_song.id)
                        trigger_timestamps_list = [(t.start_time_ms, t.end_time_ms) for t in triggers]
                        current_trigger_index = 0  # Reset trigger index
                        logger.info(f"Loaded {len(trigger_timestamps_list)} trigger sections for skipping")
            
            # Skip logic for contaminated songs
            if not clean_song and trigger_timestamps_list:
                # Find next trigger timestamp that we haven't passed yet
                next_trigger = None
                for i in range(current_trigger_index, len(trigger_timestamps_list)):
                    start_time, end_time = trigger_timestamps_list[i]
                    
                    if current_timestamp < start_time - buffer_ms:
                        # We're before this trigger, this is our next target
                        next_trigger = (start_time, end_time, i)
                        break
                    elif start_time - buffer_ms <= current_timestamp <= end_time:
                        # We're in a trigger zone, skip immediately
                        skip_to_time = end_time + 100  # Add small buffer after trigger
                        logger.info(f"Skipping trigger section {start_time}-{end_time}ms, jumping to {skip_to_time}ms")
                        sp.seek_track(position_ms=skip_to_time)
                        current_trigger_index = i + 1
                        break
                    else:
                        # We've passed this trigger
                        current_trigger_index = i + 1
                        continue
                
                if next_trigger:
                    start_time, end_time, index = next_trigger
                    logger.debug(f"Next trigger at {start_time}ms (current: {current_timestamp}ms)")
        
        except Exception as e:
            logger.error(f"Error in monitoring thread: {e}")
        
        # Wait before next check
        time.sleep(1)


def scan_song_in_background(song: Song):
    """Scan a song for trigger words in the background"""
    try:
        logger.info(f"Starting background scan for '{song.title}' by {song.artist}")
        
        # Create lyrics scraper and get lyrics
        scraper = SyncLyricsScraper([api])
        lyrics = scraper.find_synced_lyrics_of_song(song)
        
        if not lyrics:
            logger.warning(f"No lyrics found for '{song.title}' by {song.artist}")
            db.update_song_status(song.id, SongStatus.SCANNED_CLEAN)
            return
        
        # Process lyrics for trigger words
        trigger_timestamps = process_song_for_trigger_words(song, lyrics)
        
        if trigger_timestamps:
            # Song has triggers, mark as contaminated and save timestamps
            db.update_song_status(song.id, SongStatus.SCANNED_CONTAMINATED)
            
            for start_time, end_time in trigger_timestamps:
                trigger = TriggerTimestamp(
                    trigger_id=1,  # Using 1 for death words category
                    song_id=song.id,
                    start_time_ms=start_time,
                    end_time_ms=end_time
                )
                db.add_trigger_of_song(trigger)
            
            logger.info(f"Saved {len(trigger_timestamps)} trigger timestamps for '{song.title}'")
        else:
            # Song is clean
            db.update_song_status(song.id, SongStatus.SCANNED_CLEAN)
            logger.info(f"Song '{song.title}' marked as clean")
    
    except NotFoundError:
        logger.warning(f"Lyrics not found for '{song.title}' by {song.artist}")
        db.update_song_status(song.id, SongStatus.SCANNED_CLEAN)
    except Exception as e:
        logger.error(f"Error scanning song '{song.title}': {e}")
        # Don't update status on error, leave as NOT_SCANNED for retry

def main():
    """Main function to start the Spotify OCD Saver"""
    logger.info("=" * 50)
    logger.info("Starting Spotify OCD Saver")
    logger.info("=" * 50)
    
    try:
        # Test Spotify connection
        logger.info("Testing Spotify connection...")
        current_user = sp.current_user()
        logger.info(f"Connected to Spotify as: {current_user['display_name']}")
        
        # Test database connection
        logger.info("Testing database connection...")
        song_count = db.get_song_count()
        trigger_count = db.get_trigger_count()
        logger.info(f"Database connected. Songs: {song_count}, Triggers: {trigger_count}")
        
        # Start monitoring thread
        logger.info("Starting monitoring thread...")
        monitor_thread = threading.Thread(target=spotify_monitoring_thread, daemon=True)
        monitor_thread.start()
        
        logger.info("Spotify OCD Saver is now running. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Spotify OCD Saver...")
            
    except Exception as e:
        logger.error(f"Failed to start Spotify OCD Saver: {e}")
        raise


if __name__ == '__main__':
    main()