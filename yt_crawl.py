import requests
import re
import os
import time
import itertools
import json
import argparse
import subprocess
from datetime import datetime, timezone, timedelta
# import pdb, jsontree # When Debugging

api_url = 'https://www.googleapis.com/youtube/v3/'
htb_api_url = 'https://labs.hackthebox.com/api/v4/'
channel_id = 'UCa6eh7gCkpPo5XXUDfygQQA'
playlists = [
    ['linux easy', 'PLidcsTyj9JXJfpkDrttTdk1MNT6CDwVZF'],
    ['linux medium', 'PLidcsTyj9JXJKC2u55YVa5aMDBRXsawhr'],
    ['linux hard', 'PLidcsTyj9JXJlmHwZScT3He3rO4ni-xwH'],
    ['linux insane', 'PLidcsTyj9JXLI9mAR4MPiL19hq5lpaYNd'],
    ['windows easy', 'PLidcsTyj9JXL4Jv6u9qi8TcUgsNoKKHNn'],
    ['windows medium', 'PLidcsTyj9JXI9E9dT1jgXxvTOi7Pq_2c5'],
    ['windows hard', 'PLidcsTyj9JXK2sdXaK5He4-Z8G0Ra-4u2'],
    ['windows insane', 'PLidcsTyj9JXJSn8KxSr_-9eKEwxJJtf_x']
]

# "1:02:03 - text", "01:23 - text", "01:23 text". The separator dash is optional.
timestamp_re = re.compile(r'^((?:\d+:)?\d+:\d{2})\s*[-–—]?\s*(.*)$')

# Machine videos: "HackTheBox - Lame", "Hack The Box - Flight", "UHC - Union", "HackTheBox   RegistryTwo".
# Group 1 is everything after the prefix.
box_title_re = re.compile(r'^(?:hack\s*the\s*box|uhc)\b\s*[-–—]?\s*(.*)$', re.I)


def ApiGet(endpoint, params):
    r = requests.get(f'{api_url}{endpoint}', params=params)
    r.raise_for_status()
    return r.json()


def GetUploadPlaylist(api_key):
    # YouTube API will only return a list of videos in a playlist, not channel.
    # This will get the playlist that contains all videos.
    response = ApiGet('channels', {
        'id': channel_id,
        'key': api_key,
        'part': 'contentDetails'})
    return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']


def GetPlaylistItems(api_key, playlist, part='snippet'):
    # Yields every item in a playlist, following nextPageToken until the last page.
    params = {
        'key': api_key,
        'playlistId': playlist,
        'part': part,
        'maxResults': '50'}
    while True:
        response = ApiGet('playlistItems', params)
        yield from response.get('items', [])
        if 'nextPageToken' not in response:
            break
        params['pageToken'] = response['nextPageToken']


def PublishedAt(item):
    # Needs part=snippet,contentDetails. videoPublishedAt is when the video went public, which for a
    # scheduled upload is later than snippet.publishedAt.
    stamp = item.get('contentDetails', {}).get('videoPublishedAt') or item['snippet']['publishedAt']
    return datetime.fromisoformat(stamp.replace('Z', '+00:00'))


def ParseLine(line):
    # Returns (seconds, text). Lines without a leading timestamp point at the start of the video.
    match = timestamp_re.match(line)
    if not match:
        return 0, line
    parts = [int(p) for p in match.group(1).split(':')]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds, match.group(2)


def BoxName(title):
    # The HTB machine name from a video title, or None if the title isn't a machine video.
    # "HackTheBox - StreamIO - Manually Enumerating..." -> "StreamIO", "Corporate (FIXED)" -> "Corporate",
    # "Flux Capacitor" -> "FluxCapacitor". HTB names are alphanumeric.
    match = box_title_re.match(title)
    if not match:
        return None
    name = re.split(r'\s+[-–—]\s+', match.group(1))[0]
    name = re.sub(r'\(.*?\)', '', name)
    return re.sub(r'[^A-Za-z0-9]', '', name) or None


def HtbGet(path, htb_key):
    # GET from the HTB v4 API. Returns the JSON, or None on 404. The API allows 30 requests a minute.
    headers = {
        'Authorization': f'Bearer {htb_key}',
        'User-Agent': 'ippsec.rocks dataset crawler (yt_crawl.py)',
        'Accept': 'application/json'}
    for attempt in range(5):
        r = requests.get(f'{htb_api_url}{path}', headers=headers, timeout=30)
        if r.status_code == 404:
            return None
        if r.status_code in (401, 403):
            raise SystemExit(f"HTB API rejected the key (HTTP {r.status_code}). Check htb.secret.")
        if r.status_code == 429:
            wait = int(r.headers.get('Retry-After', 60))
            print(f"HTB rate limit hit, waiting {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise SystemExit("HTB API kept rate limiting, giving up")


def HtbTag(name, htb_key):
    # "linux easy" from the machine's HTB profile, or None if HTB has no machine by that name.
    # The lookup is case-insensitive. Sequels are titled "Rope2" but HTB names them "RopeTwo".
    for candidate in [name] + ([name[:-1] + 'Two'] if name.endswith('2') else []):
        print(f"Looking up {candidate} on HTB")
        response = HtbGet(f'machine/profile/{candidate}', htb_key)
        if response:
            info = response['info']
            return f"{info['os']} {info['difficultyText']}".lower()
    return None


def GetPlaylistTags(api_key):
    # {video title: "linux easy"} from the difficulty playlists, matched by exact title.
    tags = {}
    for tag, playlist in playlists:
        print(f"Grabbing {tag} playlist")
        for item in GetPlaylistItems(api_key, playlist):
            tags[item['snippet']['title']] = tag
    return tags


def ParseVideo(snippet, tag):
    lines = []
    for line in snippet['description'].split('\n'):
        line = line.strip()
        if line:
            lines.append(list(ParseLine(line)))
    return {
        "id": snippet['resourceId']['videoId'],
        "title": snippet['title'],
        "tag": tag,
        "lines": lines
    }


def run(api_key, git_commit, dataset_output_location="dataset.json", htb_key=None,
        latest=None, days=None, retag=False):
    existing = []
    try:
        with open(dataset_output_location) as ds:
            existing = json.load(ds)
    except FileNotFoundError:
        if latest or days:
            raise SystemExit(f"{dataset_output_location} doesn't exist yet, run once without --latest/--days")

    # Tags already in the dataset are kept, so only new or untagged videos cost an HTB request.
    known_tags = {} if retag else {v['id']: v['tag'] for v in existing if v['tag']}
    if not htb_key:
        print("Warning: no HTB API key, new videos will only be tagged from the playlists")
    playlist_tags = None  # Fetched on first use; HTB covers nearly every box, so this is rarely needed.

    def TagFor(snippet):
        nonlocal playlist_tags
        title = snippet['title']
        tag = known_tags.get(snippet['resourceId']['videoId'])
        if tag:
            return tag
        name = BoxName(title)
        if name and htb_key:
            tag = HtbTag(name, htb_key)
        if tag is None:
            # Covers titles HTB can't resolve, e.g. "Granny and Grandpa".
            if playlist_tags is None:
                playlist_tags = GetPlaylistTags(api_key)
            tag = playlist_tags.get(title, "")
        if not tag and name:
            print(f"Warning: no tag for {title!r}")
        return tag

    if latest or days:
        # Refresh only the newest videos and merge them into the existing dataset. Uploads are newest
        # first, as is the dataset, so new videos go to the front; known ones are replaced in place.
        items = GetPlaylistItems(api_key, GetUploadPlaylist(api_key), part='snippet,contentDetails')
        if latest:
            print(f"Grabbing the latest {latest} video(s)")
            items = itertools.islice(items, latest)
        else:
            # Looks at the newest page of 50 uploads, which is far more than a week of videos.
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            print(f"Grabbing videos published since {cutoff:%Y-%m-%d %H:%M} UTC")
            items = [item for item in itertools.islice(items, 50) if PublishedAt(item) >= cutoff]
        videos = existing
        position = {v['id']: i for i, v in enumerate(videos)}
        added = []
        for item in items:
            video = ParseVideo(item['snippet'], TagFor(item['snippet']))
            if video['id'] in position:
                print(f"Updating {video['title']}")
                videos[position[video['id']]] = video
            else:
                print(f"Adding {video['title']}")
                added.append(video)
        if not items:
            print("No videos in that window")
        videos = added + videos
    else:
        print("Grabbing video list")
        videos = []
        for item in GetPlaylistItems(api_key, GetUploadPlaylist(api_key)):
            print(item['snippet']['title'])
            videos.append(ParseVideo(item['snippet'], TagFor(item['snippet'])))

    print(f"Writing {len(videos)} videos to {dataset_output_location}")
    with open(dataset_output_location, "w") as ds:
        json.dump(videos, ds, separators=(',', ':'), ensure_ascii=False)

    if git_commit:
        print("Committing to git")
        subprocess.run(["git", "commit", "-m", "Updated dataset", dataset_output_location], check=True)
    else:
        print("Done! Now commit to git")


def ReadSecret(path):
    if os.path.exists(path):
        return open(path).read().strip()
    return None


def parser():
    parser = argparse.ArgumentParser(
        description="Generate the dataset for the web app")
    parser.add_argument(
            '-a', '--api_key',
            help="Your API key from the Youtube API (defaults to the contents of yt.secret)")
    parser.add_argument(
            '--htb-key',
            help="Your HTB App Token, used to look up each box's OS and difficulty "
                 "(defaults to the contents of htb.secret)")
    parser.add_argument(
            '--output_file', '-o',
            help="The output path",
            default="dataset.json")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
            '--latest', '-l',
            help="Only fetch the newest N uploads (default 1) and merge them into the existing dataset "
                 "instead of recrawling every video",
            nargs='?', const=1, type=int, metavar='N')
    scope.add_argument(
            '--days', '-d',
            help="Only fetch uploads published in the last DAYS days and merge them into the existing dataset",
            type=float, metavar='DAYS')
    parser.add_argument(
            '--retag',
            help="Look every machine up on HTB again instead of keeping the tags already in the dataset "
                 "(about 450 requests at 30 a minute)",
            action='store_true')
    parser.add_argument(
        '-g', '--git-commit',
        help="Automatically commit the dataset file to git (uses git cli)",
        action='store_true')
    args = parser.parse_args()
    if not args.api_key:
        args.api_key = open('yt.secret').read().strip()
    if not args.htb_key:
        args.htb_key = ReadSecret('htb.secret')

    run(args.api_key, args.git_commit, args.output_file, args.htb_key, args.latest, args.days, args.retag)


if __name__ == "__main__":
    parser()
