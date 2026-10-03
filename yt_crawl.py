import requests
import re
import json
import argparse
import subprocess
# import pdb, jsontree # When Debugging

api_url = 'https://www.googleapis.com/youtube/v3/'
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


def GetPlaylistItems(api_key, playlist):
    # Yields every item in a playlist, following nextPageToken until the last page.
    params = {
        'key': api_key,
        'playlistId': playlist,
        'part': 'snippet',
        'maxResults': '50'}
    while True:
        response = ApiGet('playlistItems', params)
        yield from response.get('items', [])
        if 'nextPageToken' not in response:
            break
        params['pageToken'] = response['nextPageToken']


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


def run(api_key, git_commit, dataset_output_location="dataset.json"):
    tags = {}
    for tag, playlist in playlists:
        print(f"Grabbing {tag} playlist")
        for item in GetPlaylistItems(api_key, playlist):
            tags[item['snippet']['title']] = tag

    print("Grabbing video list")
    videos = []
    for item in GetPlaylistItems(api_key, GetUploadPlaylist(api_key)):
        snippet = item['snippet']
        title = snippet['title']
        print(title)
        lines = []
        for line in snippet['description'].split('\n'):
            line = line.strip()
            if line:
                lines.append(list(ParseLine(line)))
        videos.append({
            "id": snippet['resourceId']['videoId'],
            "title": title,
            "tag": tags.get(title, ""),
            "lines": lines
        })

    print(f"Writing {len(videos)} videos to {dataset_output_location}")
    with open(dataset_output_location, "w") as ds:
        json.dump(videos, ds, separators=(',', ':'), ensure_ascii=False)

    if git_commit:
        print("Committing to git")
        subprocess.run(["git", "commit", "-m", "Updated dataset", dataset_output_location], check=True)
    else:
        print("Done! Now commit to git")


def parser():
    parser = argparse.ArgumentParser(
        description="Generate the dataset for the web app")
    parser.add_argument(
            '-a', '--api_key',
            help="Your API key from the Youtube API (defaults to the contents of yt.secret)")
    parser.add_argument(
            '--output_file', '-o',
            help="The output path",
            default="dataset.json")
    parser.add_argument(
        '-g', '--git-commit',
        help="Automatically commit the dataset file to git (uses git cli)",
        action='store_true')
    args = parser.parse_args()
    if not args.api_key:
        args.api_key = open('yt.secret').read().strip()

    run(args.api_key, args.git_commit, args.output_file)


if __name__ == "__main__":
    parser()
