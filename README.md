# Tautulli watched sync
Automatically synchronize watched TV Shows and movies to Trakt.tv
It can also used for the initial load from existing tautulli history to trakt. 

## Setup
Download `trakt_sync.py` and `sync_settings.ini.example` to your Tautulli host.
Rename `sync_settings.ini.example` to `sync_settings.ini` and add the `user_ids`, `client_id`, `client_secret`, `api_key` and `api_secret`. See below for more info on these settings.

**Important!** Make sure `sync-settings.ini` is writable

### Settings
`./sync-settings.ini`

```
  [Plex]
  user_ids: a comma separated list of user ids, only entries for these users will be synced
    The user id for a user can be found in your url in Tautulli when you click on a user.
  
  [Trakt]:
  Update `client_id` with the `client_id` of your registered application, see here:
    https://trakt.tv/oauth/applications > Choose your application

  To set the access code use `urn:ietf:wg:oauth:2.0:oob` as a redirect URI on your application.
  Then execute the script:
  python ./trakt_sync.py --contentType trakt_authenticate --userId -1
  And follow the instructions shown.

  [Tautulli]
  tautulli_url = url to the address from your tautulli server e.g.: http://192.168.0.1:8181/api/v2
  api_key = api key from tautulli can be found under settings in the section web interface from the server
  max_initial_item = maximum amount of movies/episode which will be transferred with the initial load. default value 2000

  Then execute the script for the initial load:
  python ./trakt_sync.py --contentType initial --userId NumberOfTheUserId

```

### Tautulli
```
Adding the script to Tautulli:
Tautulli > Settings > Notification Agents > Add a new notification agent > Script

Configuration:
Tautulli > Settings > Notification Agents > New Script > Configuration:

  Script Folder: /path/to/your/scripts
  Script File: ./trakt_sync.py (Should be selectable in a dropdown list)
  Script Timeout: {timeout}
  Description: Trakt.tv sync
  Save

Triggers:
Tautulli > Settings > Notification Agents > New Script > Triggers:
  
  Check: Watched
  Save
  
Conditions:
Tautulli > Settings > Notification Agents > New Script > Conditions:
  
  Set Conditions: [{condition} | {operator} | {value} ]
  Save
  
Script Arguments:
Tautulli > Settings > Notification Agents > New Script > Script Arguments:
  
  Select: Watched
  Arguments:  --userId {user_id} --contentType {media_type} <movie>--imdbId {imdb_id}</movie><episode>--tmdbId {themoviedb_id} --season {season_num} --episode {episode_num}</episode>

  Save
  Close
```
