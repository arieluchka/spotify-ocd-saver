# Spotify OCD Saver - Docker Deployment

This guide explains how to deploy Spotify OCD Saver using Docker for headless operation.

## Prerequisites

- Docker and Docker Compose installed
- Spotify API credentials (Client ID and Client Secret)
- Valid Spotify account with Premium subscription (required for playback control)

## Setup

1. **Clone or copy the project files**

2. **Configure environment variables**
   
   Create a `.env` file in the project root or set environment variables:
   ```bash
   # Spotify API credentials
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   
   # Database and log paths (optional, defaults provided)
   DB_PATH=/app/data/spotify_ocd_saver.db
   LOG_PATH=/app/logs/spotify_ocd_saver.log
   ```

3. **Create necessary directories**
   ```bash
   mkdir -p data logs
   ```

## Building and Running

### Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f spotify-ocd-saver

# Stop the container
docker-compose down
```

### Using Docker directly

```bash
# Build the image
docker build -t spotify-ocd-saver .

# Run the container
docker run -d \
  --name spotify-ocd-saver \
  --network host \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config:ro \
  -e SPOTIFY_CLIENT_ID=your_client_id \
  -e SPOTIFY_CLIENT_SECRET=your_client_secret \
  spotify-ocd-saver
```

## Authentication

When you first run the container, you'll need to authenticate with Spotify:

1. **Check the logs** for the authentication URL:
   ```bash
   docker-compose logs spotify-ocd-saver
   ```

2. **Open the URL** in your browser and authorize the application

3. **Copy the redirect URL** and provide it to the application when prompted

## Data Persistence

The following directories are mounted as volumes for data persistence:

- `./data/` - Contains the SQLite database
- `./logs/` - Contains application logs
- `./config/` - Contains configuration files (read-only)

## Configuration

### Trigger Words

Edit `config/bad_words_list.py` to customize trigger words. The container will need to be restarted after changes.

### Database

The SQLite database is automatically created in the `data/` directory. Database migrations are handled automatically when the container starts.

## Monitoring

### Health Check

The container includes a health check that verifies database connectivity:

```bash
# Check container health
docker-compose ps
```

### Logs

View application logs:

```bash
# Follow logs in real-time
docker-compose logs -f spotify-ocd-saver

# View last 100 lines
docker-compose logs --tail 100 spotify-ocd-saver
```

### Database

Access the database directly:

```bash
# Connect to the container
docker-compose exec spotify-ocd-saver bash

# Use sqlite3 to query the database
sqlite3 /app/data/spotify_ocd_saver.db
```

## Troubleshooting

### Common Issues

1. **Authentication Issues**
   - Ensure your Spotify API credentials are correct
   - Check that the redirect URI matches your Spotify app settings
   - Verify your Spotify account has Premium subscription

2. **Network Issues**
   - The container uses `network_mode: host` to access local Spotify clients
   - Ensure Spotify is running on the same machine

3. **Permission Issues**
   - Check that the `data/` and `logs/` directories are writable
   - Verify file ownership if running on Linux

### Getting Help

Check the application logs for detailed error messages:

```bash
docker-compose logs spotify-ocd-saver | grep ERROR
```

## Updating

To update the application:

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## Security Notes

- Never commit your `.env` file with real credentials
- Consider using Docker secrets for production deployments
- The container runs as a non-root user for security
- Database and logs are stored in mounted volumes for easy backup

## Performance

- The container is optimized for low resource usage
- SQLite database provides good performance for this use case
- Consider monitoring resource usage in production environments