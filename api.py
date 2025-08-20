"""
OCDify API - REST API for the Spotify OCD Saver service

This module provides a clean REST API interface for managing users,
trigger categories, and controlling the Spotify monitoring service.
Built with FastAPI for automatic documentation and validation.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import threading
import json
import os

from services.ocdify_db.ocdify_db import get_database
from services.user_service.user_service import get_user_service
from services.trigger_service.trigger_service import get_trigger_service
from services.trigger_scanner_service.trigger_scanner_service import TriggerScannerService
from config.models import User, TriggerCategory, SongStatus
from services.monitoring_service import get_monitoring_service

# Import API models
from services.api_models.user_models import UserCreate, UserResponse
from services.api_models.trigger_models import (
    TriggerCategoryCreate, 
    TriggerCategoryUpdate, 
    TriggerCategoryResponse
)
from services.api_models.song_models import SongResponse, TriggerResponse
from services.api_models.monitoring_models import MonitoringStatusResponse
from services.api_models.utility_models import (
    LyricsScanRequest, 
    LyricsScanResponse, 
    StatsResponse
)
from services.api_models.common_models import StandardResponse
from config.config import get_config

# Load configuration
config = get_config()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OCDify API",
    description="REST API for Spotify OCD Saver service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
db = get_database()
user_service = get_user_service(db)
trigger_service = get_trigger_service(db)
trigger_scanner = TriggerScannerService(trigger_service)
monitoring_service = get_monitoring_service(user_service, db)

# Global monitoring state (for backward compatibility status checks)
monitoring_threads = {
    'spotify_monitor': None,
    'queue_scanner': None,
    'is_running': False
}


# ============================================================================
# WEB UI ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
async def serve_homepage():
    """Serve the main web UI"""
    try:
        with open("static/index.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Web UI not found"
        )


@app.get("/callback", tags=["Web UI"])
async def spotify_callback(code: Optional[str] = None, error: Optional[str] = None):
    """Handle Spotify OAuth callback"""
    if error:
        # Redirect to home with error
        return RedirectResponse(url=f"/?error={error}")
    
    if code:
        # Redirect to home with authorization code
        return RedirectResponse(url=f"/?code={code}")
    
    # No code or error, redirect to home
    return RedirectResponse(url="/")


@app.post("/api/auth/spotify-token", response_model=StandardResponse, tags=["Authentication"])
async def exchange_spotify_code(request_data: dict):
    """Exchange Spotify authorization code for tokens (secure backend endpoint)"""
    try:
        import requests
        
        code = request_data.get('code')
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
        
        logger.info(f"Exchanging Spotify authorization code...")
        
        # Exchange code for tokens
        token_response = requests.post('https://accounts.spotify.com/api/token', {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': config.spotify_redirect_uri,
            'client_id': config.spotify_client_id,
            'client_secret': config.spotify_client_secret
        })
        
        logger.info(f"Token exchange response status: {token_response.status_code}")
        
        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange authorization code: {token_response.text}"
            )
        
        token_data = token_response.json()
        logger.info("Successfully received tokens from Spotify")
        
        # Get user info from Spotify
        user_response = requests.get('https://api.spotify.com/v1/me', headers={
            'Authorization': f"Bearer {token_data['access_token']}"
        })
        
        logger.info(f"User info response status: {user_response.status_code}")
        
        if user_response.status_code != 200:
            logger.error(f"Failed to get user info: {user_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user information from Spotify: {user_response.text}"
            )
        
        user_info = user_response.json()
        logger.info(f"Successfully authenticated user: {user_info.get('display_name', user_info['id'])}")
        
        # Create user in our system
        user = user_service.create_or_update_user(
            spotify_user_id=user_info['id'],
            display_name=user_info.get('display_name', user_info['id']),
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=token_data.get('expires_in', 3600)
        )
        
        user_data = UserResponse(
            id=user.id,
            spotify_user_id=user.spotify_user_id,
            display_name=user.display_name,
            token_expires_at=user.token_expires_at.isoformat() if user.token_expires_at else None,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
        return StandardResponse(
            success=True,
            message="Authentication successful",
            data=user_data.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Error in Spotify token exchange: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


# Configuration endpoint for frontend
@app.get("/api/config", tags=["Configuration"])
async def get_client_config():
    """Get client-side configuration (safe values only)"""
    return {
        "spotify_client_id": config.spotify_client_id,
        "spotify_redirect_uri": config.spotify_redirect_uri
    }


# ============================================================================
# DEPENDENCY FUNCTIONS
# ============================================================================

async def get_current_user(x_spotify_user_id: Optional[str] = Header(None)) -> User:
    """Get current user from request headers"""
    if not x_spotify_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Include X-Spotify-User-ID header."
        )
    
    user = user_service.get_user_by_spotify_id(x_spotify_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/users", response_model=StandardResponse, tags=["Users"])
async def create_user(user_data: UserCreate):
    """Create or update a user"""
    try:
        user = user_service.create_or_update_user(
            spotify_user_id=user_data.spotify_user_id,
            display_name=user_data.display_name,
            access_token=user_data.access_token,
            refresh_token=user_data.refresh_token,
            expires_in=user_data.expires_in
        )
        
        user_response = UserResponse(
            id=user.id,
            spotify_user_id=user.spotify_user_id,
            display_name=user.display_name,
            token_expires_at=user.token_expires_at.isoformat() if user.token_expires_at else None,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
        return StandardResponse(
            success=True,
            message="User created/updated successfully",
            data=user_response.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@app.get("/api/users/{spotify_user_id}", response_model=StandardResponse, tags=["Users"])
async def get_user(spotify_user_id: str):
    """Get user by Spotify user ID"""
    try:
        user = user_service.get_user_by_spotify_id(spotify_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_response = UserResponse(
            id=user.id,
            spotify_user_id=user.spotify_user_id,
            display_name=user.display_name,
            token_valid=user_service.is_token_valid(user),
            token_expires_at=user.token_expires_at.isoformat() if user.token_expires_at else None,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
        return StandardResponse(
            success=True,
            message="User retrieved successfully",
            data=user_response.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@app.delete("/api/users/{spotify_user_id}", response_model=StandardResponse, tags=["Users"])
async def delete_user(spotify_user_id: str):
    """Delete a user (not yet implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User deletion not yet implemented"
    )


# ============================================================================
# TRIGGER CATEGORY MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/trigger-categories", response_model=StandardResponse, tags=["Trigger Categories"])
async def get_trigger_categories(current_user: User = Depends(get_current_user)):
    """Get all trigger categories for a user"""
    try:
        categories = db.get_trigger_categories(user_id=current_user.id, include_global=True)
        
        categories_data = []
        for category in categories:
            categories_data.append(TriggerCategoryResponse(
                id=category.id,
                name=category.name,
                words=category.words,
                user_id=category.user_id,
                is_global=category.user_id is None,
                is_active=category.is_active,
                created_at=category.created_at.isoformat() if category.created_at else None
            ).model_dump())
        
        return StandardResponse(
            success=True,
            message="Trigger categories retrieved successfully",
            data=categories_data
        )
        
    except Exception as e:
        logger.error(f"Error getting trigger categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trigger categories: {str(e)}"
        )


@app.post("/api/trigger-categories", response_model=StandardResponse, tags=["Trigger Categories"])
async def create_trigger_category(
    category_data: TriggerCategoryCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new trigger category"""
    try:
        category = TriggerCategory(
            name=category_data.name,
            words=category_data.words,
            user_id=current_user.id,
            is_active=category_data.is_active
        )
        
        category_id = db.add_trigger_category(category)
        category.id = category_id
        
        category_response = TriggerCategoryResponse(
            id=category.id,
            name=category.name,
            words=category.words,
            user_id=category.user_id,
            is_global=False,
            is_active=category.is_active,
            created_at=category.created_at.isoformat() if category.created_at else None
        )
        
        return StandardResponse(
            success=True,
            message="Trigger category created successfully",
            data=category_response.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Error creating trigger category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create trigger category: {str(e)}"
        )


@app.put("/api/trigger-categories/{category_id}", response_model=StandardResponse, tags=["Trigger Categories"])
async def update_trigger_category(
    category_id: int,
    category_data: TriggerCategoryUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a trigger category"""
    try:
        # Check if category exists and belongs to user
        existing_category = db.get_trigger_category_by_id(category_id)
        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trigger category not found"
            )
        
        if existing_category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this category"
            )
        
        # Update fields (use existing values if not provided)
        name = category_data.name if category_data.name is not None else existing_category.name
        words = category_data.words if category_data.words is not None else existing_category.words
        is_active = category_data.is_active if category_data.is_active is not None else existing_category.is_active
        
        success = db.update_trigger_category(category_id, name, words, is_active, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update trigger category"
            )
        
        return StandardResponse(
            success=True,
            message="Trigger category updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trigger category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update trigger category: {str(e)}"
        )


@app.delete("/api/trigger-categories/{category_id}", response_model=StandardResponse, tags=["Trigger Categories"])
async def delete_trigger_category(
    category_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a trigger category and its associated triggers"""
    try:
        # Check if category exists and belongs to user
        existing_category = db.get_trigger_category_by_id(category_id)
        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trigger category not found"
            )
        
        if existing_category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this category"
            )
        
        # Delete associated triggers first
        deleted_triggers = db.delete_triggers_by_category(category_id, current_user.id)
        
        # Set category to inactive (or implement proper deletion)
        success = db.update_trigger_category(
            category_id, 
            existing_category.name, 
            existing_category.words, 
            False, 
            current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete trigger category"
            )
        
        return StandardResponse(
            success=True,
            message="Trigger category deleted successfully",
            data={"deleted_triggers": deleted_triggers}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trigger category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete trigger category: {str(e)}"
        )


# ============================================================================
# MONITORING CONTROL ENDPOINTS
# ============================================================================

@app.post("/api/monitoring/start", response_model=StandardResponse, tags=["Monitoring"])
async def start_monitoring(current_user: User = Depends(get_current_user)):
    """Start Spotify monitoring service"""
    try:
        # Check if monitoring is already active for this user
        if monitoring_service.is_monitoring_user(current_user.id):
            return StandardResponse(
                success=True,
                message="Monitoring is already running for this user"
            )
        
        # Start monitoring for this user
        success = monitoring_service.start_monitoring_for_user(current_user.id)
        
        if success:
            # Update global state for backward compatibility
            monitoring_threads['is_running'] = True
            
            logger.info(f"Monitoring started for user: {current_user.display_name} (ID: {current_user.id})")
            return StandardResponse(
                success=True,
                message="Monitoring started successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start monitoring service"
            )
        
    except Exception as e:
        logger.error(f"Error starting monitoring for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@app.post("/api/monitoring/stop", response_model=StandardResponse, tags=["Monitoring"])
async def stop_monitoring(current_user: User = Depends(get_current_user)):
    """Stop Spotify monitoring service"""
    try:
        # Check if monitoring is active for this user
        if not monitoring_service.is_monitoring_user(current_user.id):
            return StandardResponse(
                success=True,
                message="Monitoring is not currently running for this user"
            )
        
        # Stop monitoring for this user
        success = monitoring_service.stop_monitoring_for_user(current_user.id)
        
        # Update global state for backward compatibility
        active_users = monitoring_service.get_active_users()
        if not active_users:
            monitoring_threads['is_running'] = False
            monitoring_threads['spotify_monitor'] = None
            monitoring_threads['queue_scanner'] = None
        
        if success:
            logger.info(f"Monitoring stopped for user: {current_user.display_name} (ID: {current_user.id})")
            return StandardResponse(
                success=True,
                message="Monitoring stopped successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop monitoring service"
            )
        
    except Exception as e:
        logger.error(f"Error stopping monitoring for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}"
        )


@app.get("/api/monitoring/status", response_model=StandardResponse, tags=["Monitoring"])
async def get_monitoring_status(current_user: User = Depends(get_current_user)):
    """Get current monitoring status"""
    try:
        # Get user-specific monitoring status
        user_is_monitored = monitoring_service.is_monitoring_user(current_user.id)
        overall_status = monitoring_service.get_monitoring_status()
        
        # Create backward-compatible status response
        status_data = MonitoringStatusResponse(
            is_running=user_is_monitored,
            threads_active={
                'spotify_monitor': user_is_monitored,
                'queue_scanner': user_is_monitored
            }
        )
        
        # Add additional monitoring service information
        response_data = status_data.model_dump()
        response_data['multi_user_status'] = overall_status
        
        return StandardResponse(
            success=True,
            message="Monitoring status retrieved successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error getting monitoring status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}"
        )


# ============================================================================
# SUGGESTED BY COPILOT - ADDITIONAL USEFUL ENDPOINTS
# ============================================================================

# suggested by copilot
@app.get("/api/songs/contaminated", response_model=StandardResponse, tags=["Songs"])
async def get_contaminated_songs(current_user: User = Depends(get_current_user)):
    """Get all songs marked as contaminated"""
    try:
        songs = db.get_contaminated_songs()
        
        songs_data = []
        for song in songs:
            # Get triggers for this song
            triggers = db.get_triggers_of_song(song.id, current_user.id)
            
            song_response = SongResponse(
                id=song.id,
                title=song.title,
                artist=song.artist,
                album=song.album,
                duration_ms=song.duration_ms,
                status=song.status.name,
                spotify_id=song.spotify_id,
                trigger_count=len(triggers),
                created_at=song.created_at.isoformat() if song.created_at else None
            )
            songs_data.append(song_response.model_dump())
        
        return StandardResponse(
            success=True,
            message="Contaminated songs retrieved successfully",
            data=songs_data
        )
        
    except Exception as e:
        logger.error(f"Error getting contaminated songs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get contaminated songs: {str(e)}"
        )


# suggested by copilot
@app.get("/api/songs/{song_id}/triggers", response_model=StandardResponse, tags=["Songs"])
async def get_song_triggers(song_id: int, current_user: User = Depends(get_current_user)):
    """Get all triggers for a specific song"""
    try:
        song = db.get_song(song_id)
        if not song:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Song not found"
            )
        
        triggers = db.get_triggers_of_song(song_id, current_user.id)
        
        triggers_data = []
        for trigger in triggers:
            trigger_response = TriggerResponse(
                id=trigger.id,
                trigger_word=trigger.trigger_word,
                start_time_ms=trigger.start_time_ms,
                end_time_ms=trigger.end_time_ms,
                category_id=trigger.category_id,
                created_at=trigger.created_at.isoformat() if trigger.created_at else None
            )
            triggers_data.append(trigger_response.model_dump())
        
        response_data = {
            'song': {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album
            },
            'triggers': triggers_data
        }
        
        return StandardResponse(
            success=True,
            message="Song triggers retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting song triggers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get song triggers: {str(e)}"
        )


# suggested by copilot
@app.get("/api/songs/search", response_model=StandardResponse, tags=["Songs"])
async def search_songs(q: str, current_user: User = Depends(get_current_user)):
    """Search songs by title, artist, or album"""
    try:
        if not q.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query is required"
            )
        
        songs = db.search_songs(q)
        
        songs_data = []
        for song in songs:
            song_response = SongResponse(
                id=song.id,
                title=song.title,
                artist=song.artist,
                album=song.album,
                duration_ms=song.duration_ms,
                status=song.status.name,
                spotify_id=song.spotify_id,
                created_at=song.created_at.isoformat() if song.created_at else None
            )
            songs_data.append(song_response.model_dump())
        
        return StandardResponse(
            success=True,
            message="Songs retrieved successfully",
            data=songs_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching songs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search songs: {str(e)}"
        )


# suggested by copilot
@app.get("/api/stats", response_model=StandardResponse, tags=["Statistics"])
async def get_user_stats(current_user: User = Depends(get_current_user)):
    """Get user statistics"""
    try:
        total_songs = db.get_song_count()
        total_triggers = db.get_trigger_count()
        contaminated_songs = len(db.get_contaminated_songs())
        unscanned_songs = len(db.get_unscanned_songs())
        user_categories = len(db.get_trigger_categories(user_id=current_user.id, include_global=False))
        
        stats_data = StatsResponse(
            total_songs=total_songs,
            total_triggers=total_triggers,
            contaminated_songs=contaminated_songs,
            clean_songs=total_songs - contaminated_songs - unscanned_songs,
            unscanned_songs=unscanned_songs,
            user_categories=user_categories,
            monitoring_active=monitoring_service.is_monitoring_user(current_user.id)
        )
        
        return StandardResponse(
            success=True,
            message="Statistics retrieved successfully",
            data=stats_data.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stats: {str(e)}"
        )


# suggested by copilot
@app.post("/api/lyrics/scan", response_model=StandardResponse, tags=["Utilities"])
async def scan_lyrics_for_triggers(
    scan_request: LyricsScanRequest,
    current_user: User = Depends(get_current_user)
):
    """Manually scan lyrics text for trigger words"""
    try:
        results = trigger_scanner.scan_unsynced_lyrics(scan_request.lyrics, current_user.id)
        
        results_data = []
        for result in results:
            results_data.append({
                'trigger_word': result.trigger_word,
                'category_id': result.category_id,
                'line_number': result.line_number
            })
        
        scan_response = LyricsScanResponse(
            has_triggers=len(results) > 0,
            trigger_count=len(results),
            triggers=results_data
        )
        
        return StandardResponse(
            success=True,
            message="Lyrics scanned successfully",
            data=scan_response.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Error scanning lyrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan lyrics: {str(e)}"
        )


# ============================================================================
# HEALTH CHECK AND INFO ENDPOINTS
# ============================================================================

@app.get("/api/health", response_model=StandardResponse, tags=["System"])
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        song_count = db.get_song_count()
        
        health_data = {
            'status': 'healthy',
            'database': 'connected',
            'song_count': song_count,
            'timestamp': datetime.now().isoformat()
        }
        
        return StandardResponse(
            success=True,
            message="System is healthy",
            data=health_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/api/info", response_model=StandardResponse, tags=["System"])
async def get_api_info():
    """Get API information"""
    info_data = {
        'name': 'OCDify API',
        'version': '1.0.0',
        'description': 'REST API for Spotify OCD Saver service built with FastAPI',
        'docs_url': '/docs',
        'redoc_url': '/redoc',
        'endpoints': {
            'users': ['POST /api/users', 'GET /api/users/{id}', 'DELETE /api/users/{id}'],
            'trigger_categories': ['GET /api/trigger-categories', 'POST /api/trigger-categories', 
                                 'PUT /api/trigger-categories/{id}', 'DELETE /api/trigger-categories/{id}'],
            'monitoring': ['POST /api/monitoring/start', 'POST /api/monitoring/stop', 'GET /api/monitoring/status'],
            'songs': ['GET /api/songs/contaminated', 'GET /api/songs/{id}/triggers', 'GET /api/songs/search'],
            'utilities': ['POST /api/lyrics/scan', 'GET /api/stats', 'GET /api/health', 'GET /api/info']
        }
    }
    
    return StandardResponse(
        success=True,
        message="API information retrieved successfully",
        data=info_data
    )


# ============================================================================
# MAIN APPLICATION RUNNER
# ============================================================================

if __name__ == '__main__':
    import uvicorn
    logger.info("Starting OCDify API server with FastAPI...")
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")