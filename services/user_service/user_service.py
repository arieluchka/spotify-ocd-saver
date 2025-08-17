from typing import Optional
from datetime import datetime, timedelta
import logging

from config.models import User
from services.ocdify_db.ocdify_db import OCDifyDb

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: OCDifyDb):
        self.db = db

    def create_or_update_user(self, spotify_user_id: str, display_name: str, 
                             access_token: str, refresh_token: str, expires_in: int) -> User:
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Check if user already exists
        existing_user = self.db.get_user_by_spotify_id(spotify_user_id)
        
        if existing_user:
            logger.info(f"Updating tokens for existing user: {display_name}")
            success = self.db.update_user_tokens(
                existing_user.id, access_token, refresh_token, expires_at
            )
            
            if success:
                # Return updated user
                existing_user.access_token = access_token
                existing_user.refresh_token = refresh_token
                existing_user.token_expires_at = expires_at
                existing_user.updated_at = datetime.now()
                return existing_user
            else:
                raise Exception("Failed to update user tokens")
        else:
            logger.info(f"Creating new user: {display_name}")
            new_user = User(
                spotify_user_id=spotify_user_id,
                display_name=display_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at
            )
            
            user_id = self.db.add_user(new_user)
            new_user.id = user_id
            return new_user

    def get_user_by_spotify_id(self, spotify_user_id: str) -> Optional[User]:
        return self.db.get_user_by_spotify_id(spotify_user_id)

    def is_token_valid(self, user: User) -> bool:
        if not user.token_expires_at:
            return False
        
        # Add 5 minute buffer before expiration
        buffer_time = datetime.now() + timedelta(minutes=5)
        return user.token_expires_at > buffer_time

    def refresh_user_token(self, user: User, new_access_token: str, 
                          new_refresh_token: str, expires_in: int) -> bool:
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        success = self.db.update_user_tokens(
            user.id, new_access_token, new_refresh_token, expires_at
        )
        
        if success:
            # Update the user object
            user.access_token = new_access_token
            user.refresh_token = new_refresh_token
            user.token_expires_at = expires_at
            user.updated_at = datetime.now()
            logger.info(f"Refreshed tokens for user: {user.display_name}")
        else:
            logger.error(f"Failed to refresh tokens for user: {user.display_name}")
        
        return success

    def get_active_access_token(self, user: User) -> Optional[str]:
        if self.is_token_valid(user):
            return user.access_token
        else:
            logger.warning(f"Access token expired for user: {user.display_name}")
            return None


def get_user_service(db: OCDifyDb) -> UserService:
    return UserService(db)


if __name__ == "__main__":
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    from internal.secrets import CLIENT_ID, CLIENT_SECRET
    from services.ocdify_db.ocdify_db import get_database

    # Set up Spotipy
    scopes = [
        "user-read-private",
        "user-read-email"
    ]
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:5000/callback",
        scope=scopes
    ))

    # Get current user info from Spotify
    user_info = sp.current_user()
    spotify_user_id = user_info["id"]
    display_name = user_info.get("display_name", "Unknown")

    # Fake tokens for test (in real use, get from OAuth flow)
    access_token = sp.auth_manager.get_access_token(as_dict=False)
    refresh_token = getattr(sp.auth_manager, "refresh_token", "dummy_refresh_token")
    expires_in = 3600

    db = get_database()
    user_service = get_user_service(db)

    user = user_service.create_or_update_user(
        spotify_user_id=spotify_user_id,
        display_name=display_name,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    print(f"User created/updated: {user}")