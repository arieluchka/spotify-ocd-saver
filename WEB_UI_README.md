# OCDify Web UI Setup Guide

This guide will help you set up the web interface for OCDify.

## Prerequisites

1. Python 3.8+ installed
2. A Spotify Developer account
3. All dependencies installed: `pip install -r requirements.txt`

## Step 1: Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create an App"
3. Fill in the app details:
   - **App name**: OCDify (or any name you prefer)
   - **Description**: Spotify OCD Saver Web Interface
4. Click "Create"
5. Once created, click on your app to open settings
6. Click "Edit Settings"
7. Add the following Redirect URI:
   ```
   http://127.0.0.1:5000/callback
   ```
8. Save the settings
9. Note down your **Client ID** and **Client Secret**

## Step 2: Configure OCDify

Run the setup script to configure your Spotify credentials:

```bash
python setup_web_ui.py
```

This will prompt you for your Spotify Client ID and Client Secret, and automatically configure the application.

## Step 3: Start the Application

Start the FastAPI server:

```bash
python api.py
```

The server will start on `http://127.0.0.1:5000`

## Step 4: Access the Web Interface

1. Open your browser and go to `http://127.0.0.1:5000`
2. Click "Login with Spotify"
3. Authorize the application when prompted
4. You'll be redirected back to the OCDify dashboard

## Features

### 🎵 **Spotify Authentication**
- Secure OAuth2 login with Spotify
- No additional passwords needed
- Automatic user creation/login

### 📊 **Dashboard**
- Real-time monitoring status
- Statistics on songs and triggers
- Quick overview of your settings

### 🎯 **Trigger Categories**
- Create custom trigger word categories
- Edit and manage your trigger words
- Activate/deactivate categories

### 🎧 **Monitoring Control**
- Start/stop Spotify monitoring
- Real-time status indicators
- Thread health monitoring

### 🎼 **Song Management**
- View contaminated songs
- Search through your song library
- See trigger counts per song

### 🔍 **Lyrics Scanner**
- Test lyrics for trigger words
- Instant feedback on triggers found
- Line-by-line trigger detection

## Security Features

- **Token Encryption**: All Spotify tokens are encrypted before storage
- **Secure OAuth**: Client secrets are kept on the backend only
- **Session Management**: Secure user session handling

## Troubleshooting

### Authentication Issues
- Make sure your Spotify app redirect URI is exactly: `http://127.0.0.1:5000/callback`
- Check that your Client ID and Secret are correctly configured
- Clear browser localStorage and try again

### API Connection Issues
- Ensure the FastAPI server is running on port 5000
- Check that all dependencies are installed
- Look for error messages in the browser console

### Monitoring Not Working
- Make sure you have the correct Spotify scopes enabled
- Check that your tokens haven't expired
- Verify Spotify is playing music and accessible

## API Documentation

With the server running, visit:
- **Swagger UI**: `http://127.0.0.1:5000/docs`
- **ReDoc**: `http://127.0.0.1:5000/redoc`

## Development

The web UI consists of:
- `static/index.html` - Main HTML structure
- `static/css/style.css` - Styling and responsive design
- `static/js/app.js` - JavaScript application logic
- `api.py` - FastAPI backend with web UI endpoints

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Support

If you encounter issues:
1. Check the browser console for JavaScript errors
2. Check the FastAPI server logs
3. Ensure all environment variables are set correctly
4. Verify your Spotify app configuration

---

Enjoy using OCDify! 🎵✨