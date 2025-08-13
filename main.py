import time

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from lrclib import LrcLibAPI

from internal.secrets import CLIENT_SECRET, CLIENT_ID

api = LrcLibAPI(user_agent="my-app/0.0.1")

# todo: fine grain the scopes needed
#https://developer.spotify.com/documentation/web-api/concepts/scopes
scopes = [
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-read-playback-state"
]


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri = "https://arieluchka.com",
    scope = scopes
))
# print(sp.currently_playing())
current_song = sp.currently_playing()
track_name = current_song["item"]["name"]
album_name = current_song["item"]["album"]["name"]
artist_name = current_song["item"]["artists"][0]["name"]
duration = current_song["item"]["duration_ms"] // 1000

lyric=api.get_lyrics(
    track_name=track_name,
    artist_name=artist_name,
    album_name=album_name,
    duration = duration
)

BUFFER_MS = 1000
BAD_LINE_MS = 149160
START_OF_NEW_LINE = 151950

while True:
    print("waiting for 1sec")
    time.sleep(1)
    current_song = sp.currently_playing()
    duration = current_song["progress_ms"]
    print(f"duration is {duration}")
    if (BAD_LINE_MS - BUFFER_MS) < duration < START_OF_NEW_LINE:
        sp.seek_track(position_ms=START_OF_NEW_LINE)
        print("skipped!")

# [02:29.16] Done running, come up with Josh Dun, wanted dead or alive
# [02:31.95]

# print(sp.volume(10))
# results = sp.current_user_saved_tracks()
# for idx, item in enumerate(results['items']):
#     track = item['track']
#     print(idx, track['artists'][0]['name'], " – ", track['name'])

if __name__ == '__main__':
    ...