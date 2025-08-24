"""
Multi-User Monitoring Service for OCDify

This service manages Spotify monitoring for multiple users simultaneously.
Each user can have their own monitoring thread that tracks their playback
and applies trigger word filtering based on their personal categories.
"""

import threading
import time
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

import warnings
from config.models import User, Song, TriggerTimestamp, TriggerScanStatus, SongStatus
from services.user_service.user_service import UserService
from services.ocdify_db.ocdify_db import OCDifyDb
from services.lyrics_finder_service.lyrics_finder_service import LyricsFinderService
from services.lyrics_finder_service.lyrics_apis.lrclib_searcher import LRCLibSearcher
from services.trigger_scanner_service.trigger_scanner_service import TriggerScannerService
from services.trigger_service.trigger_service import get_trigger_service

logger = logging.getLogger(__name__)


class UserMonitoringSession:
    """Represents a monitoring session for a single user"""
    
    def __init__(self, user_id: int, user_service: UserService, db: OCDifyDb):
        self.user_id = user_id
        self.user_service = user_service
        self.db = db
        self.is_active = False
        self.thread: Optional[threading.Thread] = None
        self.last_song_id: Optional[str] = None
        self.trigger_timestamps = []
        self.current_trigger_index = 0
        self.buffer_ms = 3000
        # Initialize services needed for scanning
        self.lyrics_finder = LyricsFinderService(LRCLibSearcher())
        self.trigger_scanner = TriggerScannerService(get_trigger_service(self.db))
        
    def start(self):
        """Start monitoring for this user"""
        if self.is_active:
            logger.warning(f"Monitoring already active for user {self.user_id}")
            return False
            
        self.is_active = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started monitoring for user {self.user_id}")
        return True
        
    def stop(self):
        """Stop monitoring for this user"""
        if not self.is_active:
            return False
            
        self.is_active = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info(f"Stopped monitoring for user {self.user_id}")
        return True
        
    def _get_spotify_client_for_user(self):
        """Create a Spotipy client using the user's access token."""
        try:
            import spotipy
            user = self.user_service.get_user_by_id(self.user_id)
            if not user or not user.access_token:
                return None
            return spotipy.Spotify(auth=user.access_token)
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client for user {self.user_id}: {e}")
            return None
        
    def _monitor_loop(self):
        """Main monitoring loop for this user"""
        sp = None
        last_token_refresh = datetime.now()
        
        while self.is_active:
            try:
                # Refresh Spotify client every 30 minutes or if it's None
                if sp is None or (datetime.now() - last_token_refresh).total_seconds() > 1800:
                    sp = self._get_spotify_client_for_user()
                    last_token_refresh = datetime.now()
                    
                if not sp:
                    logger.error(f"Failed to get Spotify client for user {self.user_id}")
                    time.sleep(30)  # Wait before retrying
                    continue
                
                # Get current playback
                current_playback = sp.currently_playing()
                
                if not current_playback or not current_playback.get('item'):
                    time.sleep(5)  # No song playing, check less frequently
                    continue
                
                current_song_id = current_playback['item']['id']
                current_timestamp = current_playback.get('progress_ms', 0)
                
                # Handle new song
                if current_song_id != self.last_song_id:
                    self._handle_new_song(current_playback, sp)
                    self.last_song_id = current_song_id
                
                # Handle trigger skipping
                self._handle_trigger_skipping(current_timestamp, sp)
                
                time.sleep(1)  # Check every second during playback
                
            except Exception as e:
                logger.error(f"Error in monitoring loop for user {self.user_id}: {e}")
                time.sleep(5)  # Wait before retrying on error
                
    def _handle_new_song(self, current_playback, sp):
        """Handle when a new song starts playing"""
        song_info = current_playback['item']
        spotify_id = song_info['id']
        
        logger.info(f"User {self.user_id} - New song: {song_info['name']} by {song_info['artists'][0]['name']}")
        
        # Reset trigger tracking
        self.current_trigger_index = 0
        self.trigger_timestamps = []
        
        # Check if song exists in database
        db_song = self.db.get_song_by_spotify_id(spotify_id)
        
        if db_song:
            # Update ISRC if it's missing and available from Spotify
            isrc = song_info.get('external_ids', {}).get('isrc')
            if isrc and not db_song.isrc:
                self.db.update_song_isrc(db_song.id, isrc)
                logger.info(f"Updated ISRC for song '{db_song.title}': {isrc}")
            
            # First, check if there are triggers for this song for this specific user
            triggers = self.db.get_triggers_of_song(db_song.id, self.user_id)
            if triggers:
                self.trigger_timestamps = [(t.start_time_ms, t.end_time_ms) for t in triggers]
                logger.info(f"User {self.user_id} - Loaded {len(self.trigger_timestamps)} trigger sections")
                if self.trigger_timestamps:
                    logger.info(f"User {self.user_id} - Trigger sections: {self.trigger_timestamps}")
            else:
                # No triggers stored for this user. Check per-user song status
                user_status = self.db.get_user_song_status(db_song.id, self.user_id)
                if user_status:
                    if user_status.trigger_scan_status == TriggerScanStatus.SCANNED_CLEAN:
                        logger.info(f"User {self.user_id} - Song '{db_song.title}' previously scanned clean for this user")
                    elif user_status.trigger_scan_status == TriggerScanStatus.SCANNED_CONTAMINATED:
                        # Contaminated for this user but no triggers stored implies unsynced processing
                        if not user_status.sync:
                            msg = (
                                f"User {self.user_id} - Song '{db_song.title}' has trigger words but no synced lyrics; "
                                f"cannot skip sections (will be handled later by settings)"
                            )
                            warnings.warn(msg, UserWarning)
                            logger.warning(msg)
                        else:
                            # Sync=True but no triggers found in DB; schedule a rescan as fallback
                            logger.warning(f"User {self.user_id} - Expected synced triggers for '{db_song.title}' but none found; scheduling rescan")
                            self._schedule_lyrics_scan(db_song)
                    else:
                        # NOT_SCANNED per-user, schedule scan
                        self._schedule_lyrics_scan(db_song)
                else:
                    # No per-user status; create entry and schedule scan
                    self.db.upsert_user_song_status(db_song.id, self.user_id, TriggerScanStatus.NOT_SCANNED, sync=False)
                    self._schedule_lyrics_scan(db_song)
        else:
            # Add new song and scan it
            # Extract ISRC from external_ids if available
            isrc = song_info.get('external_ids', {}).get('isrc')
            
            new_song = Song(
                title=song_info['name'],
                artist=song_info['artists'][0]['name'],
                album=song_info['album']['name'],
                duration_ms=song_info['duration_ms'],
                spotify_id=spotify_id,
                isrc=isrc,
                status=SongStatus.NOT_SCANNED
            )
            
            song_id = self.db.add_new_song(new_song)
            new_song.id = song_id
            # Create per-user status and schedule lyrics scan
            self.db.upsert_user_song_status(new_song.id, self.user_id, TriggerScanStatus.NOT_SCANNED, sync=False)
            self._schedule_lyrics_scan(new_song)
            
    def _handle_trigger_skipping(self, current_timestamp, sp):
        """Handle skipping trigger sections"""
        if not self.trigger_timestamps:
            return
        
        # Add debug logging
        logger.debug(f"User {self.user_id} - Checking triggers at {current_timestamp}ms, have {len(self.trigger_timestamps)} triggers")
            
        # Find next trigger that needs to be skipped
        for i in range(self.current_trigger_index, len(self.trigger_timestamps)):
            start_time, end_time = self.trigger_timestamps[i]
            
            if current_timestamp < start_time - self.buffer_ms:
                # We're before this trigger
                break
            elif start_time - self.buffer_ms <= current_timestamp <= end_time:
                # We're in a trigger zone, skip it
                skip_to_time = end_time + 100
                logger.info(f"User {self.user_id} - Skipping trigger {start_time}-{end_time}ms, jumping to {skip_to_time}ms")
                try:
                    sp.seek_track(position_ms=skip_to_time)
                    self.current_trigger_index = i + 1
                except Exception as e:
                    logger.error(f"Failed to skip for user {self.user_id}: {e}")
                break
            else:
                # We've passed this trigger
                self.current_trigger_index = i + 1

    def _schedule_lyrics_scan(self, song: Song):
        """Schedule a lyrics scan for a song for this user in background."""
        def run_scan():
            try:
                # Find lyrics preferring synced
                result = self.lyrics_finder.find_any_lyrics(
                    artist=song.artist,
                    title=song.title,
                    album=song.album,
                    duration_ms=song.duration_ms,
                    prefer_synced=True
                )

                if not result or not result.found:
                    # Update general song status
                    self.db.update_song_status(song.id, SongStatus.NO_RESULTS)
                    # Update per-user status
                    self.db.upsert_user_song_status(song.id, self.user_id, TriggerScanStatus.NOT_SCANNED, sync=False)
                    logger.info(f"User {self.user_id} - No lyrics found for '{song.title}'")
                    return

                if getattr(result, 'synced_lyrics', None):
                    # We have synced lyrics - scan and persist trigger timestamps
                    synced_lines = result.synced_lyrics
                    from services.lyrics_processor import create_trigger_timestamps_from_synced_lyrics
                    trigger_timestamps = create_trigger_timestamps_from_synced_lyrics(
                        synced_lyrics='\n'.join([f"[{int(line.start_timestamp/60000):02d}:{int((line.start_timestamp%60000)/1000):02d}.{int((line.start_timestamp%1000)/10):02d}]{line.line}" for line in synced_lines]),
                        song_id=song.id,
                        trigger_service=self.trigger_scanner.trigger_service,
                        user_id=self.user_id
                    )

                    if trigger_timestamps:
                        for t in trigger_timestamps:
                            self.db.add_trigger_of_song(t)
                        self.db.upsert_user_song_status(song.id, self.user_id, TriggerScanStatus.SCANNED_CONTAMINATED, sync=True)
                        # Load timestamps for skipping immediately
                        self.trigger_timestamps = [(t.start_time_ms, t.end_time_ms) for t in trigger_timestamps]
                        logger.info(f"User {self.user_id} - Stored {len(trigger_timestamps)} triggers for '{song.title}'")
                    else:
                        self.db.upsert_user_song_status(song.id, self.user_id, TriggerScanStatus.SCANNED_CLEAN, sync=True)
                        logger.info(f"User {self.user_id} - '{song.title}' scanned clean with synced lyrics")

                    # Update general song status to SYNC_LYRICS
                    self.db.update_song_status(song.id, SongStatus.SYNC_LYRICS)
                    return

                if getattr(result, 'plain_lyrics', None):
                    # Plain lyrics present; quick check for triggers
                    has_triggers = self.trigger_scanner.has_triggers(result.plain_lyrics, self.user_id)
                    if has_triggers:
                        # Contaminated but no sync lyrics
                        self.db.upsert_user_song_status(song.id, self.user_id, TriggerScanStatus.SCANNED_CONTAMINATED, sync=False)
                        warnings.warn(
                            f"User {self.user_id} - Song '{song.title}' has trigger words but no synced lyrics; cannot skip sections",
                            UserWarning
                        )
                        logger.warning(f"User {self.user_id} - '{song.title}' contaminated with plain lyrics only")
                    else:
                        self.db.upsert_user_song_status(song.id, self.user_id, TriggerScanStatus.SCANNED_CLEAN, sync=False)
                        logger.info(f"User {self.user_id} - '{song.title}' scanned clean with plain lyrics")

                    # Update general song status to PLAIN_LYRICS
                    self.db.update_song_status(song.id, SongStatus.PLAIN_LYRICS)
                    return

                # Fallback: no lyrics content found
                self.db.update_song_status(song.id, SongStatus.NO_RESULTS)
                self.db.upsert_user_song_status(song.id, self.user_id, TriggerScanStatus.NOT_SCANNED, sync=False)
            except Exception as e:
                logger.error(f"User {self.user_id} - Error scanning song '{song.title}': {e}")

        threading.Thread(target=run_scan, daemon=True).start()


class MonitoringService:
    """Service that manages monitoring sessions for multiple users"""
    
    def __init__(self, user_service: UserService, db: OCDifyDb):
        self.user_service = user_service
        self.db = db
        self.active_sessions: Dict[int, UserMonitoringSession] = {}
        self._lock = threading.Lock()
        
    def start_monitoring_for_user(self, user_id: int) -> bool:
        """Start monitoring for a specific user"""
        with self._lock:
            if user_id in self.active_sessions:
                logger.warning(f"Monitoring already active for user {user_id}")
                return False
                
            session = UserMonitoringSession(user_id, self.user_service, self.db)
            if session.start():
                self.active_sessions[user_id] = session
                return True
            return False
            
    def stop_monitoring_for_user(self, user_id: int) -> bool:
        """Stop monitoring for a specific user"""
        with self._lock:
            session = self.active_sessions.get(user_id)
            if session:
                success = session.stop()
                if success:
                    del self.active_sessions[user_id]
                return success
            return False
            
    def get_active_users(self) -> Set[int]:
        """Get set of user IDs that are currently being monitored"""
        with self._lock:
            return set(self.active_sessions.keys())
            
    def is_monitoring_user(self, user_id: int) -> bool:
        """Check if a user is currently being monitored"""
        with self._lock:
            return user_id in self.active_sessions
            
    def get_monitoring_status(self) -> Dict:
        """Get overall monitoring status"""
        with self._lock:
            return {
                'total_active_users': len(self.active_sessions),
                'active_user_ids': list(self.active_sessions.keys()),
                'sessions': {
                    user_id: {
                        'is_active': session.is_active,
                        'last_song_id': session.last_song_id,
                        'trigger_count': len(session.trigger_timestamps)
                    }
                    for user_id, session in self.active_sessions.items()
                }
            }
            
    def stop_all_monitoring(self):
        """Stop monitoring for all users"""
        with self._lock:
            for user_id in list(self.active_sessions.keys()):
                self.stop_monitoring_for_user(user_id)
                
    def cleanup_inactive_sessions(self):
        """Remove sessions that are no longer active"""
        with self._lock:
            inactive_users = [
                user_id for user_id, session in self.active_sessions.items()
                if not session.is_active
            ]
            for user_id in inactive_users:
                del self.active_sessions[user_id]
                logger.info(f"Cleaned up inactive session for user {user_id}")


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service(user_service: UserService, db: OCDifyDb) -> MonitoringService:
    """Get the global monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService(user_service, db)
    return _monitoring_service