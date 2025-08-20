# OCDify Configuration Guide

OCDify supports multiple ways to configure the application. This document provides a comprehensive guide to all available configuration options and how to set them up.

## Configuration Sources

OCDify loads configuration from multiple sources in the following priority order (highest to lowest):

1. **Environment Variables**
2. **Configuration File** (`web_config.py`)
3. **Default Values**

## Configuration Options

### Spotify OAuth Configuration

These settings are required for Spotify authentication and API access.

| Option | Environment Variable | Type | Default | Description |
|--------|---------------------|------|---------|-------------|
| `spotify_client_id` | `SPOTIFY_CLIENT_ID` | string | `""` | Your Spotify app's Client ID from the Spotify Developer Dashboard |
| `spotify_client_secret` | `SPOTIFY_CLIENT_SECRET` | string | `""` | Your Spotify app's Client Secret from the Spotify Developer Dashboard |
| `spotify_redirect_uri` | `SPOTIFY_REDIRECT_URI` | string | `"http://127.0.0.1:5000/callback"` | OAuth redirect URI (must match what's configured in your Spotify app) |
| `spotify_scopes` | `SPOTIFY_SCOPES` | list | See below | List of Spotify API scopes required by the application |

**Default Spotify Scopes:**
```python
[
    "user-read-private",
    "user-read-email", 
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-read-playback-state"
]
```

### Web UI Configuration

These settings control the web interface behavior.

| Option | Environment Variable | Type | Default | Description |
|--------|---------------------|------|---------|-------------|
| `web_ui_host` | `WEB_UI_HOST` | string | `"0.0.0.0"` | Host address for the web server (0.0.0.0 allows external connections) |
| `web_ui_port` | `WEB_UI_PORT` | integer | `5000` | Port number for the web server |
| `debug_mode` | `DEBUG_MODE` | boolean | `False` | Enable Flask debug mode (more verbose logging, auto-reload) |

### Database Configuration

Settings for the SQLite database used to store application data.

| Option | Environment Variable | Type | Default | Description |
|--------|---------------------|------|---------|-------------|
| `database_path` | `DATABASE_PATH` | string | `"spotify_ocd_saver.db"` | Path to the SQLite database file |

### Logging Configuration

Settings for application logging.

| Option | Environment Variable | Type | Default | Description |
|--------|---------------------|------|---------|-------------|
| `log_level` | `LOG_LEVEL` | string | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `log_file` | `LOG_FILE` | string | `"spotify_ocd_saver.log"` | Path to the log file |

## Setup Methods

### Method 1: Environment Variables

Set environment variables in your shell or system:

**Windows (PowerShell):**
```powershell
$env:SPOTIFY_CLIENT_ID = "your_client_id_here"
$env:SPOTIFY_CLIENT_SECRET = "your_client_secret_here"
$env:WEB_UI_PORT = "5000"
$env:DEBUG_MODE = "false"
```

**Linux/macOS (Bash):**
```bash
export SPOTIFY_CLIENT_ID="your_client_id_here"
export SPOTIFY_CLIENT_SECRET="your_client_secret_here"
export WEB_UI_PORT="5000"
export DEBUG_MODE="false"
```

### Method 2: Configuration File (`web_config.py`)

Create a `web_config.py` file in the project root:

```python
"""
Web UI Configuration for OCDify
"""

# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID = "your_client_id_here"
SPOTIFY_CLIENT_SECRET = "your_client_secret_here"
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
WEB_UI_HOST = "0.0.0.0"
WEB_UI_PORT = 5000
DEBUG_MODE = False

# Database Configuration
DATABASE_PATH = "spotify_ocd_saver.db"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "spotify_ocd_saver.log"
```

### Method 3: .env File

Create a `.env` file in the project root:

```env
# OCDify Configuration

# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
SPOTIFY_SCOPES=user-read-private,user-read-email,user-modify-playback-state,user-read-currently-playing,user-read-playback-state

# Web UI Configuration
WEB_UI_HOST=0.0.0.0
WEB_UI_PORT=5000
DEBUG_MODE=false

# Database Configuration
DATABASE_PATH=spotify_ocd_saver.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=spotify_ocd_saver.log
```

## Spotify App Setup

To get your Spotify credentials:

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the app details:
   - **App Name**: OCDify (or your preferred name)
   - **App Description**: Spotify OCD Saver Application
   - **Redirect URI**: `http://127.0.0.1:5000/callback`
   - **API/SDK**: Check "Web API"
5. Click "Save"
6. On the app page, note your **Client ID**
7. Click "Show Client Secret" to reveal your **Client Secret**
8. Make sure the redirect URI `http://127.0.0.1:5000/callback` is listed in the "Redirect URIs" section

**Important Notes:**
- Use `127.0.0.1` instead of `localhost` in the redirect URI as Spotify no longer accepts localhost
- Keep your Client Secret secure and never commit it to version control
- The redirect URI in your Spotify app settings must exactly match the one in your configuration

## Validation

The application validates the following configuration requirements:

- **Spotify Client ID** is required (cannot be empty)
- **Spotify Client Secret** is required (cannot be empty)  
- **Spotify Redirect URI** is required (cannot be empty)
- **Web UI Port** must be between 1 and 65535

If any validation fails, the application will exit with an error message indicating which configuration values need to be fixed.

## Testing Configuration

You can test your configuration by running:

```bash
python config/config.py
```

This will display your current configuration (with sensitive values partially masked) and validate that all required settings are present.

## Security Considerations

- Never commit your `web_config.py` or `.env` file to version control if it contains real credentials
- Add these files to your `.gitignore`:
  ```
  web_config.py
  .env
  ```
- Consider using environment variables in production environments
- The Spotify Client Secret should be treated as a password and kept secure

## Troubleshooting

### Common Issues

1. **"Spotify Client ID is required"**
   - Ensure you've set `SPOTIFY_CLIENT_ID` in your environment or configuration file

2. **"INVALID_CLIENT" error during OAuth**
   - Check that your Client ID and Client Secret are correct
   - Verify the redirect URI in your Spotify app matches your configuration
   - Ensure you're using `127.0.0.1` instead of `localhost`

3. **"Port already in use"**
   - Change the `WEB_UI_PORT` to a different port number
   - Check if another application is using port 5000

4. **Configuration not loading**
   - Check file permissions on `web_config.py` or `.env`
   - Ensure files are in the project root directory
   - Verify syntax in configuration files (no typos, proper quotes, etc.)

## Example Complete Setup

Here's a complete example using the configuration file method:

1. Create `web_config.py`:
```python
SPOTIFY_CLIENT_ID = "abcd1234efgh5678"
SPOTIFY_CLIENT_SECRET = "xyz789abc123def456"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/callback"
```

2. Start the application:
```bash
python api.py
```

3. Open your browser to `http://127.0.0.1:5000`

4. Click "Login with Spotify" to authenticate

That's it! Your OCDify application should now be fully configured and ready to use.