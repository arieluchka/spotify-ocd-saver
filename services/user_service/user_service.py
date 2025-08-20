from typing import Optional
from datetime import datetime, timedelta
import logging
import os
import base64
from cryptography.fernet import Fernet

from config.models import User
from config.config import get_config
from services.ocdify_db.ocdify_db import OCDifyDb

logger = logging.getLogger(__name__)

# Load configuration
config = get_config()


class UserService:
    def __init__(self, db: OCDifyDb):
        self.db = db
        self.cipher = self._get_or_create_cipher()

    def _get_or_create_cipher(self) -> Fernet:
        """Get or create encryption key for token encryption"""
        key_file = "token_encryption.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("Generated new encryption key for tokens")
        
        return Fernet(key)

    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token"""
        if not token:
            return token
        return base64.b64encode(self.cipher.encrypt(token.encode())).decode()

    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token"""
        if not encrypted_token:
            return encrypted_token
        try:
            return self.cipher.decrypt(base64.b64decode(encrypted_token.encode())).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            return ""

    def create_or_update_user(self, spotify_user_id: str, display_name: str, 
                             access_token: str, refresh_token: str, expires_in: int) -> User:
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Encrypt tokens before storing
        encrypted_access_token = self._encrypt_token(access_token)
        encrypted_refresh_token = self._encrypt_token(refresh_token)
        
        # Check if user already exists
        existing_user = self.db.get_user_by_spotify_id(spotify_user_id)
        
        if existing_user:
            logger.info(f"Updating tokens for existing user: {display_name}")
            success = self.db.update_user_tokens(
                existing_user.id, encrypted_access_token, encrypted_refresh_token, expires_at
            )
            
            if success:
                # Return updated user with decrypted tokens
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
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                token_expires_at=expires_at
            )
            
            user_id = self.db.add_user(new_user)
            new_user.id = user_id
            # Return user with decrypted tokens for in-memory use
            new_user.access_token = access_token
            new_user.refresh_token = refresh_token
            return new_user

    def get_user_by_spotify_id(self, spotify_user_id: str) -> Optional[User]:
        user = self.db.get_user_by_spotify_id(spotify_user_id)
        if user:
            # Decrypt tokens when retrieving from database
            user.access_token = self._decrypt_token(user.access_token)
            user.refresh_token = self._decrypt_token(user.refresh_token)
        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        user = self.db.get_user_by_id(user_id)
        if user:
            # Decrypt tokens when retrieving from database
            user.access_token = self._decrypt_token(user.access_token)
            user.refresh_token = self._decrypt_token(user.refresh_token)
        return user

    def is_token_valid(self, user: User) -> bool:
        if not user.token_expires_at:
            return False
        
        # Add 5 minute buffer before expiration
        buffer_time = datetime.now() + timedelta(minutes=5)
        return user.token_expires_at > buffer_time

    def refresh_user_token(self, user: User, new_access_token: str, 
                          new_refresh_token: str, expires_in: int) -> bool:
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Encrypt tokens before storing
        encrypted_access_token = self._encrypt_token(new_access_token)
        encrypted_refresh_token = self._encrypt_token(new_refresh_token)
        
        success = self.db.update_user_tokens(
            user.id, encrypted_access_token, encrypted_refresh_token, expires_at
        )
        
        if success:
            # Update the user object with unencrypted tokens for in-memory use
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
    from services.ocdify_db.ocdify_db import get_database

    # Set up SpotifyOAuth with centralized config
    scopes = [
        "user-read-private",
        "user-read-email"
    ]
    
    sp_oauth = SpotifyOAuth(
        client_id=config.spotify_client_id,
        client_secret=config.spotify_client_secret,
        redirect_uri=config.spotify_redirect_uri,
        scope=scopes
    )
    
    # Get access token (this will trigger OAuth flow if needed)
    token_info = sp_oauth.get_access_token()
    
    if not token_info:
        print("Failed to get access token")
        exit(1)
    
    access_token = token_info['access_token']
    refresh_token = token_info.get('refresh_token', 'no_refresh_token')
    expires_in = token_info.get('expires_in', 3600)
    
    # Create Spotipy client with the token
    sp = spotipy.Spotify(auth=access_token)

    # Get current user info from Spotify
    user_info = sp.current_user()
    spotify_user_id = user_info["id"]
    display_name = user_info.get("display_name", "Unknown")

    print(f"Access token: {access_token[:20]}...")
    print(f"Refresh token: {refresh_token}")
    print(f"Expires in: {expires_in} seconds")

    db = get_database()
    user_service = get_user_service(db)

    user = user_service.create_or_update_user(
        spotify_user_id=spotify_user_id,
        display_name=display_name,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    print(f"User created/updated: {user.display_name} (ID: {user.id})")
    print(f"Tokens are encrypted in database")