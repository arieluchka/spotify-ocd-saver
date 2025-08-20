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

from config.models import User
from services.user_service.user_service import UserService
from services.ocdify_db.ocdify_db import OCDifyDb
from main import get_spotify_client_for_user, scan_song_in_background

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
        
    def _monitor_loop(self):
        """Main monitoring loop for this user"""
        sp = None
        last_token_refresh = datetime.now()
        
        while self.is_active:
            try:
                # Refresh Spotify client every 30 minutes or if it's None
                if sp is None or (datetime.now() - last_token_refresh).total_seconds() > 1800:
                    sp = get_spotify_client_for_user(self.user_id)
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
            
            if db_song.status.value == 'SCANNED_CONTAMINATED':
                # Load trigger timestamps
                triggers = self.db.get_triggers_of_song(db_song.id, self.user_id)
                self.trigger_timestamps = [(t.start_time_ms, t.end_time_ms) for t in triggers]
                logger.info(f"User {self.user_id} - Loaded {len(self.trigger_timestamps)} trigger sections")
                if self.trigger_timestamps:
                    logger.info(f"User {self.user_id} - Trigger sections: {self.trigger_timestamps}")
            elif db_song.status.value == 'NOT_SCANNED':
                # Scan in background
                threading.Thread(target=scan_song_in_background, args=(db_song, self.user_id), daemon=True).start()
        else:
            # Add new song and scan it
            from config.models import Song, SongStatus
            
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
            
            # Scan in background
            threading.Thread(target=scan_song_in_background, args=(new_song, self.user_id), daemon=True).start()
            
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