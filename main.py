import time
import re
import logging
import threading
from typing import Tuple, List

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from lrclib import LrcLibAPI
from lrclib.models import Lyrics
from lrclib.exceptions import NotFoundError

from internal.secrets import CLIENT_SECRET, CLIENT_ID
from config.models import *
from services.ocdify_db.ocdify_db import get_database
from services.trigger_service.trigger_service import get_trigger_service
from services.user_service.user_service import get_user_service
from services.lyrics_processor import (
    create_trigger_timestamps_from_synced_lyrics,
    search_plain_lyrics_for_triggers
)
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spotify_ocd_saver.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

api = LrcLibAPI(user_agent="spotify-ocd-saver/0.1.0")
db = get_database()
trigger_service = get_trigger_service(db)
user_service = get_user_service(db)

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
    redirect_uri = "http://127.0.0.1:5000/callback",
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




def queue_scanning_thread():
    """
    Periodically scan Spotify queue for unanalyzed songs.
    Runs every 300 seconds (5 minutes) to check the queue and analyze new songs.
    """
    logger.info("Starting queue scanning thread...")
    
    while True:
        try:
            time.sleep(300)  # Wait 5 minutes between scans
            
            logger.info("Starting periodic queue scan...")
            
            # Get current queue
            try:
                queue = sp.queue()
                if not queue or 'queue' not in queue:
                    logger.debug("No queue available or empty queue")
                    continue
                
                queue_tracks = queue['queue']
                logger.info(f"Found {len(queue_tracks)} tracks in queue")
                
                new_songs_count = 0
                existing_songs_count = 0
                
                for track in queue_tracks:
                    if not track or 'id' not in track:
                        continue
                    
                    spotify_id = track['id']
                    
                    # Check if song already exists in database
                    existing_song = db.get_song_by_spotify_id(spotify_id)
                    
                    if existing_song:
                        existing_songs_count += 1
                        
                        # If song exists but hasn't been scanned, trigger scan
                        if existing_song.status == SongStatus.NOT_SCANNED:
                            logger.info(f"Triggering scan for unscanned song: '{existing_song.title}' by {existing_song.artist}")
                            threading.Thread(target=scan_song_in_background, args=(existing_song, None), daemon=True).start()
                    else:
                        # Add new song to database and scan it
                        logger.info(f"Adding new queue song: '{track['name']}' by {track['artists'][0]['name']}")
                        
                        new_song = Song(
                            title=track['name'],
                            artist=track['artists'][0]['name'],
                            album=track['album']['name'],
                            duration_ms=track['duration_ms'],
                            spotify_id=spotify_id,
                            status=SongStatus.NOT_SCANNED
                        )
                        
                        song_id = db.add_new_song(new_song)
                        new_song.id = song_id
                        new_songs_count += 1
                        
                        # Scan in background
                        logger.info(f"Triggering scan for new queue song: '{new_song.title}'")
                        threading.Thread(target=scan_song_in_background, args=(new_song, None), daemon=True).start()
                
                logger.info(f"Queue scan completed. New songs: {new_songs_count}, Existing: {existing_songs_count}")
                
            except Exception as queue_error:
                logger.warning(f"Error accessing Spotify queue: {queue_error}")
                # Queue access might fail due to permissions or player state
                continue
                
        except Exception as e:
            logger.error(f"Error in queue scanning thread: {e}")
            # Continue running even if there's an error
            continue


def spotify_monitoring_thread():
    """
    Monitor Spotify playback and skip trigger words.
    Will run every second to check current playback status.
    """
    currently_played_song_id = None
    clean_song = True
    trigger_timestamps_list = []
    current_trigger_index = 0
    buffer_ms = 3000
    
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
                        threading.Thread(target=scan_song_in_background, args=(db_song, None), daemon=True).start()
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
                    threading.Thread(target=scan_song_in_background, args=(new_song, None), daemon=True).start()
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


def scan_song_in_background(song: Song, user_id: Optional[int] = None):
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
        
        # Check if we have synced lyrics
        if lyrics.synced_lyrics:
            logger.info(f"Found synced lyrics for '{song.title}', processing for triggers...")
            # Use the new lyrics processor for synced lyrics
            trigger_timestamps_objs = create_trigger_timestamps_from_synced_lyrics(
                synced_lyrics=lyrics.synced_lyrics,
                song_id=song.id,
                trigger_service=trigger_service,
                user_id=user_id
            )
            
            if trigger_timestamps_objs:
                # Song has triggers, mark as contaminated and save timestamps
                db.update_song_status(song.id, SongStatus.SCANNED_CONTAMINATED)
                
                for trigger in trigger_timestamps_objs:
                    db.add_trigger_of_song(trigger)
                
                logger.info(f"Saved {len(trigger_timestamps_objs)} trigger timestamps for '{song.title}'")
            else:
                # Song is clean
                db.update_song_status(song.id, SongStatus.SCANNED_CLEAN)
                logger.info(f"Song '{song.title}' marked as clean (synced lyrics)")
        
        elif lyrics.plain_lyrics:
            logger.info(f"Found plain lyrics for '{song.title}', checking for triggers...")
            # Update song with non-synced lyrics ID if available
            if hasattr(lyrics, 'id') and lyrics.id:
                db.update_song_not_sync_lrclib_id(song.id, str(lyrics.id))
            
            # Use the new lyrics processor for plain lyrics
            has_triggers = search_plain_lyrics_for_triggers(
                lyrics.plain_lyrics, 
                trigger_service, 
                user_id
            )
            
            if has_triggers:
                db.update_song_status(song.id, SongStatus.SCANNED_CONTAMINATED)
                logger.info(f"Song '{song.title}' marked as contaminated (plain lyrics)")
            else:
                db.update_song_status(song.id, SongStatus.SCANNED_CLEAN)
                logger.info(f"Song '{song.title}' marked as clean (plain lyrics)")
        else:
            logger.warning(f"No usable lyrics found for '{song.title}' by {song.artist}")
            db.update_song_status(song.id, SongStatus.SCANNED_CLEAN)
    
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
        
        # Start queue scanning thread
        logger.info("Starting queue scanning thread...")
        queue_thread = threading.Thread(target=queue_scanning_thread, daemon=True)
        queue_thread.start()
        
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