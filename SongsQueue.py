import logging
from json import JSONDecodeError

import jsonpickle
from pytube import Search
from pytube import YouTube
from pytube.exceptions import RegexMatchError

from Song import Song
from exceptions import AgeRestrictedVideo, VideoTooLong


class SongsQueue:

    def __init__(self):
        self.songs = []
        try:
            f = open('queue.json')
            self.songs = jsonpickle.decode(f.read()).songs
            logging.debug("successfully replicated queue from json")

        except JSONDecodeError:
            logging.warning("queue.json JSONDecodeError possibly empty file")
        except FileNotFoundError:
            logging.warning("No such file or directory: 'queue.json'")
        except PermissionError:
            logging.warning("Permission denied: 'queue.json'")

    def __str__(self):
        return str(self.songs)

    def is_empty(self):
        return self.songs == []

    def name_add(self, name):
        s = Search(name)
        self.add(s.results[0].video_id)

    def add(self, videoId):
        try:
            yt = YouTube("https://www.youtube.com/watch?v=" + videoId)
            try:
                if yt.age_restricted:
                    raise AgeRestrictedVideo()

                if yt.length > 600:
                    raise VideoTooLong()

                song = Song(yt.video_id, yt.title, yt.author, yt.thumbnail_url, yt.length)
                self.songs.append(song)
            except TypeError:
                logging.warning("TypeError int(self.vid_info.get('videoDetails', {}).get('lengthSeconds'))")
                self.add(videoId)

        except RegexMatchError:
            pass

    def getFirstId(self):
        return self.peek(0).id

    def remove_by_index(self, index):
        if index > 0 or index <= len(self.songs):
            self.songs.pop(index)

    def remove_by_id(self, videoId):
        for song in self.songs:
            if song.id == videoId:
                self.songs.remove(song)
                break

    def get_by_id(self, videoId):
        for song in self.songs:
            if song.id == videoId:
                return song

    def size(self):
        return len(self.songs)

    def peek(self, index):
        if index < 0 or index >= len(self.songs):
            return None
        else:
            return self.songs[index]

    def move(self, start, end):
        if start < 0 or start >= len(self.songs) or end < 0 or end >= len(self.songs):
            raise ValueError
        else:
            self.songs.insert(end, self.songs.pop(start))

    def empty(self):
        self.songs = []

    def restore(self, videoId, position):
        yt = YouTube("https://www.youtube.com/watch?v=" + videoId)
        try:
            if yt.age_restricted:
                raise AgeRestrictedVideo()

            if yt.length > 600:
                raise VideoTooLong()
            song = Song(yt.video_id, yt.title, yt.author, yt.thumbnail_url, yt.length)
            self.songs.insert(position, song)
        except TypeError:
            logging.warning("TypeError int(self.vid_info.get('videoDetails', {}).get('lengthSeconds'))")
            self.restore(videoId, position)
