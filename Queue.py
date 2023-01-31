import logging
from json import JSONDecodeError

import jsonpickle
from pytube import Search
from pytube import YouTube
from pytube.exceptions import RegexMatchError

from Song import Song
from exceptions import AgeRestrictedVideo, VideoTooLong


class Queue:

    def __init__(self):
        self.songs = []
        try:
            data = open('queue.json').read()
            self.songs = jsonpickle.decode(data).songs
            logging.debug("successfully replicated queue from json")

        except JSONDecodeError:
            logging.warning("queue.json JSONDecodeError possibly empty file")
        except FileNotFoundError:
            logging.warning("No such file or directory: 'queue.json'")

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
            if yt.age_restricted:
                raise AgeRestrictedVideo()

            if yt.length > 600:
                raise VideoTooLong()
            song = Song(yt.video_id, yt.title, yt.author, yt.thumbnail_url, yt.length)
            self.songs.append(song)

        except RegexMatchError:
            pass


    def getFirstId(self):
        song = self.peek(0)
        if song:
            return song.id
        else:
            return None

    def remove_by_index(self, index):
        if index < 0 or index >= len(self.songs):
            return None
        else:
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
        if yt.age_restricted:
            raise AgeRestrictedVideo()

        if yt.length > 600:
            raise VideoTooLong()
        song = Song(yt.video_id, yt.title, yt.author, yt.thumbnail_url, yt.length)
        self.songs.insert(position, song)
