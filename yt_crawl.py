import requests
import re
import json
#import pdb, jsontree # When Debugging

api_key = '' # ADD YOUR YOUTUBE API KEY HERE
api_url = 'https://www.googleapis.com/youtube/v3/'
channel_id = 'UCa6eh7gCkpPo5XXUDfygQQA'

def GetUploadPlaylist():
    # YouTube API will only return a list of videos in a playlist, not channel.
    # This will get the playlist that contains all videos.
    data = { 'id':channel_id,
        'key':api_key,
        'part':'contentDetails'}
    r = requests.get(f'{api_url}channels', params=data)
    response = json.loads(r.text)
    # ToDo: There's gotta be a better way to do this...
    upload_id = response.get('items')[0].get('contentDetails').get('relatedPlaylists').get('uploads')
    return upload_id

def GetTotalVideosInPlaylist():
    # Get the total number of videos, so our playlist crawler knows how many videos to grab.
    # Probably is not needed, had created this before investigating how YouTube returns pages
    # in a query.
    data = { 
        'key':api_key,
        'playlistId':GetUploadPlaylist(),
        'part':'snippet',
        'maxResults':'2'}
    r = requests.get(f'{api_url}playlistItems', params=data)
    response = json.loads(r.text)
    total_videos = response.get('pageInfo').get('totalResults')
    return total_videos


def GetVideosInPlaylist():
    # Gets all the videos in a playlist, hardcoded to the Uploaded Playlist
    #https://www.googleapis.com/youtube/v3/playlistItems?playlistId={"uploads" Id}&key={API key}&part=snippet&maxResults=50
    output = []
    next_page_token = ''
    page = 1
    total_videos = GetTotalVideosInPlaylist()
    # This logic probably can be replaced by doing checks against the nextPageToken.
    while total_videos > 0:
        page +=1
        total_videos = total_videos - 50
        data = { 
            'key':api_key,
            'playlistId':GetUploadPlaylist(),
            'part':'snippet',
            'maxResults':'50'}
        if next_page_token:
            data.update( {'pageToken':next_page_token} )
        r = requests.get(f'{api_url}playlistItems', params=data)
        videos = json.loads(r.text)
        next_page_token = videos.get('nextPageToken')
        for video in videos.get('items'):
            vId = video.get('snippet').get('resourceId').get('videoId')
            date = video.get('snippet').get('publishedAt')
            title = video.get('snippet').get('title')
            description = video.get('snippet').get('description')
            output.append([date,vId,title,description])
    return output
            
output = GetVideosInPlaylist()
for video in output:
    description = video[3].split('\n')
    for line in description:
        if "HackTheBox" in video[2] or "VulnHub" in video[2]:
            title = video[2].split()[2]
        if line != "":
            if not re.search('[\d]*:[\d]', line):
                line = '00:01 - ' + line
            print(f'{title} | {video[1]} ^ {line}')

