The high level plan is to make a script/service that monitors the songs/queue that is listened to in spotify, and will skip/remove from queue songs that have specific triggering words.

[spotify dashboard](https://developer.spotify.com/dashboard/1184e319941f4bde926b43d9304e7d60)



[musixmatch api docs](https://docs.musixmatch.com/lyrics-api/introduction)

[free (?) musicxmatch-api](https://github.com/Strvm/musicxmatch-api)
(getting captcha requests)

alternative to musixmatch:

[lrclib](https://lrclib.net/docs)
[python library](https://github.com/Dr-Blank/lrclibapi)



[spotify-lyrics-api](https://github.com/akashrchandran/spotify-lyrics-api)



1) use sqllite to save triggering song ids into db 


### SQL
- table of trigger words categories
- table of trigger words, of a specific category
- (if a user adds/removes words from category, delete all trigger_timestamps info for this category (so it will be regenerated))

<br>

- Table of songs (id + title+artist+album+duration + Status(0=NOT_SCANNED,1=NO_RESULTS,2=PLAIN_LYRICS,3=SYNC_LYRICS)+ spotify_id + ISRC + LRCLIB_id)

- Table for trigger timestamps (trigger_id + song_id + start_time_ms + end_time_ms + created_at)

<br>

- Table of streaming services (spotify/youtube music/etc)
- Table of lyrics syncing services (musixmatch/LRClib)



## Basic Flow



## Stuff to note
- Handle cases when there are multiple triggering words in one line (make sure no duplicate entries in DB)
- make the ids for streaming service and lyrics service generic (to be adaptable to other services)

## Extra ideas
- have a variable that sets how far from bad word it will query spotify more often (do me more on time for skip)
- keep track of the queue order, and if it changes, trigger a scan of queue items and aggregate them
- (Entirly new thing) - let user create more specific timestamps for bad words (to over write the default line skip)


---

# User features
1) User can choose default behavior on songs with triggering words
    - Skip song if there is any triggering word
    - Skip song parts (timestamps) that have triggering words (can also choose buffer (how much time to skip in advance))
    - Dont skip any song

2) User can choose default behavior on what happens if no synced lyrics was found
    - skip/dont skip songs that no lyrics was found
    - skip/dont skip songs that have bad word in lyrics, but we dont know 