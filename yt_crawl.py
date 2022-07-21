import requests
import re
import json
import argparse
# import pdb, jsontree # When Debugging


class SearchEntry:
    # JSON serializey stuff
    class Timestamp:
        minutes = 0
        seconds = 1
    machine = ""
    videoId = ""
    timestamp = Timestamp()
    tag = ""
    line = ""

    def __init__(self, machine, video, minutes, seconds, tag, line):
        self.machine, self.videoId, self.timestamp.minutes, self.timestamp.seconds, self.tag, self.line = machine, video, minutes, seconds, tag, line

    def AsJsonSerializable(self):
        return {
            "machine": self.machine,
            "videoId": self.videoId,
            "timestamp": {
                "minutes": int(self.timestamp.minutes),
                "seconds": int(self.timestamp.seconds)
            },
            "tag": self.tag,
            "line": self.line
        }

class AcademyEntry:
    # JSON serializey stuff
    machine = ""
    academy = ""
    line = ""
    tag = ""

    def __init__(self, machine, academy, line):
        self.machine, self.academy, self.line = machine, academy, line

    def AsJsonSerializable(self):
        return {
            "machine": self.machine,
            "academy": self.academy,
            "line": self.line,
            "tag": self.tag
        }

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


def GetUploadChannel(api_key):
    # YouTube API will only return a list of videos in a playlist, not channel.
    # This will get the playlist that contains all videos.
    data = {'id': channel_id,
            'key': api_key,
            'part': 'contentDetails'}
    r = requests.get(f'{api_url}channels', params=data)
    response = json.loads(r.text)
    # ToDo: There's gotta be a better way to do this...
    upload_id = response.get('items')[0].get(
        'contentDetails').get('relatedPlaylists').get('uploads')
    return upload_id


def GetTotalVideosInChannel(api_key):
    # Get the total number of videos, so our playlist crawler knows how many videos to grab.
    # Probably is not needed, had created this before investigating how YouTube returns pages
    # in a query.
    data = {
        'key': api_key,
        'playlistId': GetUploadChannel(api_key),
        'part': 'snippet',
        'maxResults': '2'}
    r = requests.get(f'{api_url}playlistItems', params=data)
    response = json.loads(r.text)
    total_videos = response.get('pageInfo').get('totalResults')
    return total_videos


def GetVideosInChannel(api_key):
    # Gets all the videos in a playlist, hardcoded to the Uploaded Playlist
    # https://www.googleapis.com/youtube/v3/playlistItems?playlistId={"uploads" Id}&key={API key}&part=snippet&maxResults=50
    output = []
    next_page_token = ''
    page = 1
    total_videos = GetTotalVideosInChannel(api_key)
    # This logic probably can be replaced by doing checks against the nextPageToken.
    while total_videos > 0:
        page += 1
        total_videos = total_videos - 50
        data = {
            'key': api_key,
            'playlistId': GetUploadChannel(api_key),
            'part': 'snippet',
            'maxResults': '50'}
        if next_page_token:
            data.update({'pageToken': next_page_token})
        r = requests.get(f'{api_url}playlistItems', params=data)
        videos = json.loads(r.text)
        next_page_token = videos.get('nextPageToken')
        for video in videos.get('items'):
            vId = video.get('snippet').get('resourceId').get('videoId')
            date = video.get('snippet').get('publishedAt')
            title = video.get('snippet').get('title')
            description = video.get('snippet').get('description')
            output.append([date, vId, title, description])
    return output

def GetVideosInPlaylist(api_key, playlist):
    # Get the total number of videos, so our playlist crawler knows how many videos to grab.
    # Probably is not needed, had created this before investigating how YouTube returns pages
    # in a query.
    videos = []
    data = {
        'key': api_key,
        'playlistId': playlist,
        'part': 'snippet',
        'maxResults': '50'}
    print(f'{api_url}playlistItems')
    print(data)
    r = requests.get(f'{api_url}playlistItems', params=data)
    response = json.loads(r.text)
    for video in response['items']:
        title = video['snippet']['title']
        videos.append(title)
    old_token = 0
    while "nextPageToken" in response.keys():
        if response['nextPageToken'] == old_token:
            break        
        data = {
            'key': api_key,
            'playlistId': playlist,
            'part': 'snippet',
            'maxResults': '50',
            'nextPageToken': response['nextPageToken']}
        r = requests.get(f'{api_url}playlistItems', params=data)
        response = json.loads(r.text)
        for video in response['items']:
            title = video['snippet']['title']
            videos.append(title)
        old_token = response['nextPageToken']
        


    total_videos = response.get('pageInfo').get('totalResults')
    pages = total_videos//50
    return videos

def parseAcademy():
    output = []
    for line in open('academy.csv').readlines():
        course,course_id,description = line.split(";")
        entry = AcademyEntry(
            course, course_id, description).AsJsonSerializable()
        output.append(entry)
    return output

def run(api_key, gitCommit, datasetOutputLocation="dataset.json"):
    videos = []
    print("Parsing Academy Courses")
    output = parseAcademy()
    for x in output:
        videos.append(x)

    print("Done Parsing Academy Courses")
    tags = {}
    for i in playlists:
        for v in GetVideosInPlaylist(api_key,i[1]):
            print(i[0])
            tags[v] = i[0]
    
    print("Grabbing video list")
    output = GetVideosInChannel(api_key)
    print("Sorting data")
    for video in output:
        tag = ""
        description = video[3].split('\n')
        title = video[2]
        print(title)
        if title in tags.keys():
            tag = tags[title]
        for line in description:
            if line != "":
                if not re.search('^\w[\d]*:[\d]', line):
                    line = '00:01 - ' + line

                temp = line.split("-")

                timestamp = temp[0].strip().split(":")

                seconds = timestamp[-1]
                hours = 0
                try:
                    hours = int(timestamp[-3])
                except:
                    pass
                minutes = int(timestamp[-2]) + int(hours * 60)

                newline = "-".join(temp[1::])

                entry = SearchEntry(
                    title, video[1], minutes, seconds, tag, newline).AsJsonSerializable()

                videos.append(entry)
                #print(f'{title} | {video[1]} ^ {line}')

    print("Serializing dataset")
    dataset = json.dumps(videos)
    print("Writing Dataset dataset...")
    with open(datasetOutputLocation, "w") as ds:
        ds.write(dataset)

    if gitCommit:
        gitDescription = "Updated dataset"
        print(f"Commiting to git, with commit description {gitDescription}")
        from subprocess import call
#        call(["git", "commit", "-m", gitDescription, datasetOutputLocation])
    else:
        print("Done! Now commit to git")


def parser():
    parser = argparse.ArgumentParser(
        description="Generate the dataset for the web app")
    parser.add_argument(
            '-a','--api_key',
            help="Your API key from the Youtube API", 
            default=False)
    parser.add_argument(
            '--output_file', '-o',
            help="The output path", 
            default="dataset.json")
    parser.add_argument(
        '-g', '--git-commit',
        help="Automatically commit the dataset file to git (uses git cli)", 
        default=False, 
        type=bool)
    args = parser.parse_args()
    if not args.api_key:
        args.api_key = open('yt.secret').read()

    run(args.api_key, args.output_file)


if __name__ == "__main__":
    parser()
