

import os, sys
import logging
import requests
import urllib
import json

from .exception import RadioServiceException


class RadioService(object):
    """docstring for AudioService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        self.config = config
        self.db = db
        self.dbtables = dbtables

    @staticmethod
    def init(config, db, dbtables):
        if not AudioService._instance:
            AudioService._instance = AudioService(config, db, dbtables)
        return AudioService._instance

    def getVideoInfo(self, videoId):
        """
        given the video Id of a youtube video return metadata about the video

        response include:
            - thumbnail url and dimensions
            - audio stream url and duration
            - title

        This API is subject to frequently change
        """

        url = "https://www.youtube.com/get_video_info?video_id=" + videoId

        response = requests.get(url)

        if response.status_code != 200:
            raise RadioServiceException("video not found for: %s" % videoId)

        text = response.text

        obj = {}
        for item in text.split('&'):
            lhs, rhs = item.split("=")
            obj[urllib.parse.unquote_plus(lhs)] = urllib.parse.unquote_plus(rhs)

        obj = json.loads(obj['player_response'])

        details = obj['videoDetails']

        # there are multiple thumbnails grab the biggest one which
        # won't need to be scaled down too much
        thumbnail = None
        for thumb in details['thumbnail']['thumbnails']:
            if not thumbnail or (thumb['width'] > thumbnail['width'] and thumb['width'] < 256):
                thumbnail = thumb

        # there are multiple streams grab one which seems reasonable

        stream = None
        if 'streamingData' in obj:
            formats = obj['streamingData']['formats'] + obj['streamingData']['adaptiveFormats']
            for format in formats:
                if format['mimeType'].startswith("audio/"):

                    new_stream = {
                        "url": format["url"],
                        "mimeType": format["mimeType"],
                        "quality": format["quality"],
                    }

                    if stream is None or 'webm' in format["mimeType"]:
                        stream = new_stream
        else:
            print(json.dumps(obj, indent=2))

        video = {
            "id": videoId,
            "title": details['title'],
            "duration": details['lengthSeconds'],
            "thumbnail": thumbnail,
            "rating": details['averageRating'] / 5.0,
            "stream": stream
        }

        return video



def main():

    service = RadioService(None, None, None)

    obj = service.getVideoInfo("3r_Z5AYJJd4")
    print(json.dumps(obj, indent=2))
if __name__ == '__main__':
    main()
