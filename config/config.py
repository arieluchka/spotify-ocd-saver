"""
Centralized Configuration System for OCDify

This module provides a unified way to manage configuration from:
1. Environment variables
2. Configuration files (web_config.py, .env)
3. Default values

Priority order (highest to lowest):
1. Environment variables
2. Configuration file (web_config.py)
3. Default values
"""

import os
from typing import List
from dataclasses import dataclass, field


@dataclass
class OCDifyConfig:
    """OCDify configuration class"""
    
    # Spotify OAuth Configuration
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:5000/callback"
    spotify_scopes: List[str] = field(default_factory=lambda: [
        "user-read-private",
        "user-read-email", 
        "user-modify-playback-state",
        "user-read-currently-playing",
        "user-read-playback-state"
    ])
    
    # Web UI Configuration
    web_ui_host: str = "0.0.0.0"
    web_ui_port: int = 5000
    debug_mode: bool = True
    
    # Database Configuration
    database_path: str = "spotify_ocd_saver.db"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "spotify_ocd_saver.log"


def load_from_env() -> dict:
    """Load configuration from environment variables"""
    env_config = {}
    
    # Spotify configuration
    if os.getenv('SPOTIFY_CLIENT_ID'):
        env_config['spotify_client_id'] = os.getenv('SPOTIFY_CLIENT_ID')
    if os.getenv('SPOTIFY_CLIENT_SECRET'):
        env_config['spotify_client_secret'] = os.getenv('SPOTIFY_CLIENT_SECRET')
    if os.getenv('SPOTIFY_REDIRECT_URI'):
        env_config['spotify_redirect_uri'] = os.getenv('SPOTIFY_REDIRECT_URI')
    if os.getenv('SPOTIFY_SCOPES'):
        env_config['spotify_scopes'] = os.getenv('SPOTIFY_SCOPES').split(',')
    
    # Web UI configuration
    if os.getenv('WEB_UI_HOST'):
        env_config['web_ui_host'] = os.getenv('WEB_UI_HOST')
    if os.getenv('WEB_UI_PORT'):
        env_config['web_ui_port'] = int(os.getenv('WEB_UI_PORT'))
    if os.getenv('DEBUG_MODE'):
        env_config['debug_mode'] = os.getenv('DEBUG_MODE').lower() in ('true', '1', 'yes', 'on')
    
    # Database configuration
    if os.getenv('DATABASE_PATH'):
        env_config['database_path'] = os.getenv('DATABASE_PATH')
    
    # Logging configuration
    if os.getenv('LOG_LEVEL'):
        env_config['log_level'] = os.getenv('LOG_LEVEL')
    if os.getenv('LOG_FILE'):
        env_config['log_file'] = os.getenv('LOG_FILE')
    
    return env_config


def load_from_config_file() -> dict:
    """Load configuration from web_config.py file"""
    file_config = {}
    
    try:
        import web_config
        
        # Spotify configuration
        if hasattr(web_config, 'SPOTIFY_CLIENT_ID'):
            file_config['spotify_client_id'] = web_config.SPOTIFY_CLIENT_ID
        if hasattr(web_config, 'SPOTIFY_CLIENT_SECRET'):
            file_config['spotify_client_secret'] = web_config.SPOTIFY_CLIENT_SECRET
        if hasattr(web_config, 'SPOTIFY_REDIRECT_URI'):
            file_config['spotify_redirect_uri'] = web_config.SPOTIFY_REDIRECT_URI
        if hasattr(web_config, 'SPOTIFY_SCOPES'):
            file_config['spotify_scopes'] = web_config.SPOTIFY_SCOPES
        
        # Web UI configuration
        if hasattr(web_config, 'WEB_UI_HOST'):
            file_config['web_ui_host'] = web_config.WEB_UI_HOST
        if hasattr(web_config, 'WEB_UI_PORT'):
            file_config['web_ui_port'] = web_config.WEB_UI_PORT
        if hasattr(web_config, 'DEBUG_MODE'):
            file_config['debug_mode'] = web_config.DEBUG_MODE
            
    except ImportError:
        print("Warning: web_config.py not found, using defaults and environment variables")
    
    return file_config


def load_from_dotenv() -> dict:
    """Load configuration from .env file"""
    env_config = {}
    
    env_file_path = '.env'
    if os.path.exists(env_file_path):
        try:
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
            
            # Re-load from environment after setting .env variables
            env_config = load_from_env()
        except Exception as e:
            print(f"Warning: Error reading .env file: {e}")
    
    return env_config


def load_config() -> OCDifyConfig:
    """Load configuration from all sources with proper priority"""
    
    # Load configuration from different sources
    default_config = OCDifyConfig()
    dotenv_config = load_from_dotenv()
    file_config = load_from_config_file()
    env_config = load_from_env()
    
    # Merge configurations (later configs override earlier ones)
    merged_config = merge_configs(
        default_config.__dict__,
        dotenv_config,
        file_config,
        env_config
    )
    
    # Create final config object
    config = OCDifyConfig(**merged_config)
    
    # Validate configuration
    errors = validate_config(config)
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check the configuration. Refer to ocdify_readme.md for setup instructions.")
        exit(1)
    
    return config


def merge_configs(*configs) -> dict:
    """Merge multiple configuration dictionaries"""
    merged = {}
    for config in configs:
        merged.update(config)
    return merged


def validate_config(config: OCDifyConfig) -> List[str]:
    """Validate configuration and return list of errors"""
    errors = []
    
    if not config.spotify_client_id:
        errors.append("Spotify Client ID is required")
    
    if not config.spotify_client_secret:
        errors.append("Spotify Client Secret is required")
    
    if not config.spotify_redirect_uri:
        errors.append("Spotify Redirect URI is required")
    
    if config.web_ui_port < 1 or config.web_ui_port > 65535:
        errors.append("Web UI port must be between 1 and 65535")
    
    return errors


def get_config() -> OCDifyConfig:
    """Get the current configuration (main entry point)"""
    return load_config()


if __name__ == "__main__":
    # Allow running this module directly for setup
    config = load_config()
    
    print("Current OCDify Configuration:")
    print(f"  Spotify Client ID: {config.spotify_client_id[:8]}..." if config.spotify_client_id else "  Spotify Client ID: Not set")
    print(f"  Redirect URI: {config.spotify_redirect_uri}")
    print(f"  Web UI: {config.web_ui_host}:{config.web_ui_port}")
    print(f"  Debug Mode: {config.debug_mode}")
    print(f"  Database: {config.database_path}")
    print(f"  Log Level: {config.log_level}")