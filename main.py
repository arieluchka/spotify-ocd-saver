import time
from typing import Tuple

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from lrclib import LrcLibAPI
from lrclib.models import Lyrics

from internal.secrets import CLIENT_SECRET, CLIENT_ID
from models import *
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

class SyncLyricsScraper:
    _scraper: LrcLibAPI
    def __init__(self, scrapers_list: list):
        self._scrapers_list = scrapers_list
        self._scraper = scrapers_list[0]


    def find_synced_lyrics_of_song(self, song: Song) -> Lyrics:
        song_lyrics_res = self._scraper.get_lyrics(
            track_name=song.title,
            artist_name=song.artist,
            album_name=song.album,
            duration=song.duration_ms // 1000
        )
        return song_lyrics_res



def process_song_for_trigger_words() -> list[Tuple[int, int]]|None: # list of tuples of start_time_ms and end_time_ms
    """

    :return:
        None: means no trigger words were found
    """
    # make sure to document a line one time at most (if more than 2 trigger words are found in the same line, output it only once)
    #log: add debug log every time a line is matched
    #log: add info for how many lines were found with trigger words
    ...

def spotify_monitoring_thread():
    """
    Will run every second.


    """
    CURRENTLY_PLAYED_SONG_ID = None
    CLEAN_SONG: bool = True
    TRIGGER_TIMESTAMPS_LIST = []
    CLOSEST_TRIGGER_TIMESTAMP = 0
    CLOSEST_SKIP_TIMESTAMP = 0
    BUFFER_MS = 1000

    while True:
        current_song = sp.currently_playing()
        if current_song["item"]["id"] != CURRENTLY_PLAYED_SONG_ID:
            ... # check db if song was scanned before, if not, add to db, find and process lyrics, update db, change song status.
        else:
            if CLEAN_SONG:
                continue
            current_timestamp = current_song["progress_ms"]
            #log: add debug for current song timestamp

            if current_timestamp > CLOSEST_SKIP_TIMESTAMP:
                ... #get the next closest timestamp

            # SKIP IF IN TIMESTAMP
            elif (CLOSEST_TRIGGER_TIMESTAMP - BUFFER_MS) <= current_timestamp < CLOSEST_SKIP_TIMESTAMP:
                sp.seek_track(position_ms=START_OF_NEW_LINE)
                # + update CLOSEST_TIMESTAMPS

# while True:
#     print("waiting for 1sec")
#     time.sleep(1)
#     current_song = sp.currently_playing()
#     duration = current_song["progress_ms"]
#     print(f"duration is {duration}")
#     if (BAD_LINE_MS - BUFFER_MS) < duration < START_OF_NEW_LINE:
#         sp.seek_track(position_ms=START_OF_NEW_LINE)
#         print("skipped!")

# [02:29.16] Done running, come up with Josh Dun, wanted dead or alive
# [02:31.95]

# print(sp.volume(10))
# results = sp.current_user_saved_tracks()
# for idx, item in enumerate(results['items']):
#     track = item['track']
#     print(idx, track['artists'][0]['name'], " – ", track['name'])

if __name__ == '__main__':
    ...