#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Description: Sync viewing history with Trakt.tv
initial Author: Joost van Someren
adjustments done by: thobi85

Important!
Make sure `./sync-settings.ini` is writable

Settings:
./sync-settings.ini

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
  Arguments:  --userId {user_id} --contentType {media_type}
              <movie>--imdbId {imdb_id}</movie>
              <episode>--tmdbId {themoviedb_id} --season {season_num} --episode {episode_num}</episode>

  Save
  Close
"""

import os
import sys
import requests
import argparse
import datetime
import json

from configparser import ConfigParser, NoOptionError, NoSectionError

TAUTULLI_ENCODING = os.getenv('TAUTULLI_ENCODING', 'UTF-8')

credential_path = os.path.dirname(os.path.realpath(__file__))
credential_file = 'sync_settings.ini'

config = ConfigParser()
try:
    with open('%s/%s' % (credential_path, credential_file)) as f:
        config.read_file(f)
except IOError:
    print('ERROR: %s/%s not found' % (credential_path, credential_file))
    sys.exit(1)


def arg_decoding(arg):
    """Decode args, encode UTF-8"""
    return arg.decode(TAUTULLI_ENCODING).encode('UTF-8')


def write_settings():
    """Write config back to settings file"""
    try:
        with open('%s/%s' % (credential_path, credential_file), 'w') as f:
            config.write(f)
    except IOError:
        print('ERROR: unable to write to %s/%s' % (credential_path, credential_file))
        sys.exit(1)


def sync_for_user(user_id):
    """Returns wheter or not to sync for the passed user_id"""
    try:
        user_ids = config.get('Plex', 'user_ids')
    except (NoSectionError, NoOptionError):
        print('ERROR: %s not setup - missing user_ids' % credential_file)
        sys.exit(1)

    return str(user_id) in user_ids.split(',')


class Trakt:
    def __init__(self, type, watched_at, id, season_num='', episode_num=''):
        if type == 'movie':
            self.type = 'movie'
            self.watched_at = watched_at
            self.imdb_id = id
        elif type == 'episode':
            self.type = 'episode'
            self.watched_at = watched_at
            self.tmdb_id = id
            self.season_num = season_num
            self.episode_num = episode_num

        try:
            self.client_id = config.get('Trakt', 'client_id')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing client_id' % credential_file)
            sys.exit(1)

        try:
            self.client_secret = config.get('Trakt', 'client_secret')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing client_secret' % credential_file)
            sys.exit(1)

    def get_access_token(self):
        try:
            return config.get('Trakt', 'access_token')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing access_token' % credential_file)
            sys.exit(1)

    def get_refresh_token(self):
        try:
            return config.get('Trakt', 'refresh_token')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing refresh_token' % credential_file)
            sys.exit(1)

    def authenticate(self):
        headers = {
            'Content-Type': 'application/json'
        }

        device_code = self.generate_device_code(headers)
        self.poll_access_token(headers, device_code)

    def generate_device_code(self, headers):
        payload = {
            'client_id': self.client_id
        }

        r = requests.post('https://api.trakt.tv/oauth/device/code', json=payload, headers=headers)
        response = r.json()
        print('Please go to %s and insert the following code: "%s"' % (
            response['verification_url'], response['user_code']))

        i = input('I have authorized the application! Press ENTER to continue:')

        return response['device_code']

    def poll_access_token(self, headers, device_code):
        payload = {
            'code': device_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        r = requests.post('https://api.trakt.tv/oauth/device/token', json=payload, headers=headers)
        if r.status_code == 400:
            i = input('The device hasn\'t been authorized yet, please do so. Press ENTER to continue:')
            return self.poll_access_token(self, headers, device_code)
        elif r.status_code != 200:
            print('Something went wrong, please try again.')
            sys.exit(1)

        response = r.json()
        config.set('Trakt', 'access_token', response['access_token'])
        config.set('Trakt', 'refresh_token', response['refresh_token'])
        write_settings()

        print('Succesfully configured your Trakt.tv sync!')

    def refresh_access_token(self):
        headers = {
            'Content-Type': 'application/json'
        }

        payload = {
            'refresh_token': self.get_refresh_token(),
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token'
        }

        r = requests.post('https://api.trakt.tv/oauth/token', json=payload, headers=headers)
        response = r.json()
        config.set('Trakt', 'access_token', response['access_token'])
        config.set('Trakt', 'refresh_token', response['refresh_token'])
        write_settings()

        print('Refreshed access token succesfully!')

    def get_movie(self):
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }

        r = requests.get('https://api.trakt.tv/search/imdb/' + str(self.imdb_id) + '?type=movie', headers=headers)

        response = r.json()
        return response[0]['movie']

    def get_show(self):
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }

        r = requests.get('https://api.trakt.tv/search/tmdb/' + str(self.tmdb_id) + '?type=show', headers=headers)

        response = r.json()
        return response[0]['show']

    def get_episode(self, show):
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }

        r = requests.get('https://api.trakt.tv/shows/' + str(show['ids']['slug']) + '/seasons/' + str(
            self.season_num) + '/episodes/' + str(self.episode_num), headers=headers)
        response = r.json()
        return response

    def sync_history(self):
        access_token = self.get_access_token()
        if self.watched_at is not None:
            watched_at = self.watched_at
        else:
            watched_at = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + access_token,
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }

        if self.type == 'movie':
            movie = self.get_movie()
            payload = {
              'movies': [
                {
                  'watched_at': watched_at,
                  'title': movie['title'],
                  'year': movie['year'],
                  'ids': {
                    'trakt': movie['ids']['trakt'],
                    'slug': movie['ids']['slug'],
                    'imdb': movie['ids']['imdb'],
                    'tmdb': movie['ids']['tmdb']
                  }
                }
              ]
            }
        elif self.type == 'episode':
            show = self.get_show()
            episode = self.get_episode(show)
            payload = {
                'episodes': [
                    {
                        'watched_at': watched_at,
                        'ids': {
                            'trakt': episode['ids']['trakt'],
                            'tvdb': episode['ids']['tvdb'],
                            'imdb': episode['ids']['imdb'],
                            'tmdb': episode['ids']['tmdb']
                        }
                    }
                ]
            }

        r = requests.post('https://api.trakt.tv/sync/history', json=payload, headers=headers)

class initial:


    def get_tautulli_url(self):
        try:
            return config.get('Tautulli', 'tautulli_url')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing tautulli url' % credential_file)
            sys.exit(1)

    def get_api_key(self):
        try:
            return config.get('Tautulli', 'api_key')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing tautulli api key' % credential_file)
            sys.exit(1)

    def get_max_initial_items(self):
        try:
            return config.get('Tautulli', 'max_initial_item')
        except (NoSectionError, NoOptionError):
            print('ERROR: %s not setup - missing tautulli api key' % credential_file)
            sys.exit(1)

    def initial_load():
        # Set the Tautulli API URL and API key
        tautulli_url = self.get_tautulli_url()
        api_key = self.get_api_key()
        length = self.get_max_initial_items()

        # Define the user ID and get the history data for that user
        user_id = opts.userId
        history_params = {'apikey': api_key, 'cmd': 'get_history', 'user_id': user_id, 'length': length}
        history_response = requests.get(tautulli_url, params=history_params)
        history_data = json.loads(history_response.text)

        trakt = Trakt(None, None, None)
        trakt.refresh_access_token()

        # Loop through the history data and filter the results
        for item in history_data['response']['data']['data']:
            # Get the fields from get_history API
            watched_at = datetime.datetime.fromtimestamp(item['date']).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            media_type = item['media_type']

            if media_type == 'movie':
                rating_key = item['rating_key']
            elif media_type == 'episode':
                rating_key = item['grandparent_rating_key']
            
            episode = item['media_index']
            season = item['parent_media_index']
            percent_complete = item['percent_complete']
    
            # Check if the percentage complete is greater than 90
            if percent_complete > 90:
                # Get the metadata for the rating key
                metadata_params = {'apikey': api_key, 'cmd': 'get_metadata', 'rating_key': rating_key}
                metadata_response = requests.get(tautulli_url, params=metadata_params)
                metadata_data = json.loads(metadata_response.text)

                if len(metadata_data['response']['data']) == 0:
                    print('Error for:', media_type,'rating_key:', rating_key)
                    continue
        
                # Get the guids from the metadata
                for guid in metadata_data['response']['data']['guids']:
                    if media_type == 'movie':
                        if guid.startswith("imdb"):
                            guid_entry = guid.split("//")[1]
                            trakt = Trakt('movie', watched_at, guid_entry)
                            trakt.sync_history()
                        else:
                            continue
                    elif media_type == 'episode':
                        if guid.startswith("tmdb"):
                            guid_entry = guid.split("//")[1]
                            trakt = Trakt('episode', watched_at, guid_entry, season, episode)
                            trakt.sync_history()
                        else:
                            continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Syncing viewing activity to Trakt.tv.")

    parser.add_argument('--userId', required=True, type=int,
                        help='The user_id of the current user.')

    parser.add_argument('--contentType', required=True, type=str,
                        help='The type of content, movie or episode.')

    parser.add_argument('--tmdbId', type=int,
                        help='TMDB ID.')

    parser.add_argument('--season', type=int,
                        help='Season number.')

    parser.add_argument('--episode', type=int,
                        help='Episode number.')

    parser.add_argument('--imdbId', type=str,
                        help='IMDB ID.')

    opts = parser.parse_args()

    if not sync_for_user(opts.userId) and not opts.userId == -1:
        print('We will not sync for this user')
        sys.exit(0)

    if opts.contentType == 'trakt_authenticate':
        trakt = Trakt(None, None, None)
        trakt.authenticate()
    elif opts.contentType == 'trakt_refresh':
        trakt = Trakt(None, None, None)
        trakt.refresh_access_token()
    elif opts.contentType == 'movie':
        trakt = Trakt('movie', None, opts.imdbId)
        trakt.refresh_access_token()
        trakt.sync_history()
    elif opts.contentType == 'episode':
        trakt = Trakt('episode', None, opts.tmdbId, opts.season, opts.episode)
        trakt.refresh_access_token()
        trakt.sync_history()
    elif opts.contentType == 'initial':
        initial.initial_load()
    else:
        print('ERROR: %s not found - invalid contentType' % opts.contentType)
