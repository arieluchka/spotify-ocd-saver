"""
User-related API models for OCDify service
"""

from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    spotify_user_id: str = Field(..., description="Spotify user ID")
    display_name: str = Field(..., description="User display name")
    access_token: str = Field(..., description="Spotify access token")
    refresh_token: str = Field(..., description="Spotify refresh token")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    id: int
    spotify_user_id: str
    display_name: str
    token_valid: Optional[bool] = None
    token_expires_at: Optional[str] = None
    created_at: Optional[str] = None