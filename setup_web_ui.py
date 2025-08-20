"""
Setup script for OCDify Web UI

This script helps you set up the Spotify OAuth credentials for the web interface.
"""

import os
import json

def setup_spotify_credentials():
    print("=" * 50)
    print("OCDify Web UI Setup")
    print("=" * 50)
    print()
    
    print("1. Go to https://developer.spotify.com/dashboard")
    print("2. Create a new app or select an existing one")
    print("3. Go to 'Settings' and add this redirect URI:")
    print("   http://127.0.0.1:5000/callback")
    print("4. Copy your Client ID and Client Secret")
    print()
    
    client_id = input("Enter your Spotify Client ID: ").strip()
    client_secret = input("Enter your Spotify Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Both Client ID and Client Secret are required!")
        return False
    
    # Update web_config.py
    config_content = f'''"""
Web UI Configuration for OCDify
"""

# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID = "{client_id}"
SPOTIFY_CLIENT_SECRET = "{client_secret}"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/callback"

# Required Spotify Scopes
SPOTIFY_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-read-playback-state"
]

# Web UI Configuration
WEB_UI_PORT = 5000
WEB_UI_HOST = "0.0.0.0"
DEBUG_MODE = True
'''
    
    with open('web_config.py', 'w') as f:
        f.write(config_content)
    
    # Update JavaScript file
    js_file_path = 'static/js/app.js'
    if os.path.exists(js_file_path):
        with open(js_file_path, 'r') as f:
            js_content = f.read()
        
        # Replace the placeholder client ID
        js_content = js_content.replace('YOUR_SPOTIFY_CLIENT_ID', client_id)
        js_content = js_content.replace('YOUR_SPOTIFY_CLIENT_SECRET', client_secret)
        
        with open(js_file_path, 'w') as f:
            f.write(js_content)
    
    print()
    print("✅ Configuration saved successfully!")
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Start the API server: python api.py")
    print("3. Open your browser to: http://127.0.0.1:5000")
    print()
    
    return True

if __name__ == "__main__":
    setup_spotify_credentials()