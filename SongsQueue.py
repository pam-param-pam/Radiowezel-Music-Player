import logging
from json import JSONDecodeError
import os
import jsonpickle
import pafy
from pytube import Search
from pytube import YouTube
from pytube.exceptions import RegexMatchError, PytubeError

from Song import Song
from exceptions import AgeRestrictedVideo, VideoTooLong


class SongsQueue:

    def __init__(self):
        self.songs = []
        try:
            f = open(os.getcwd() + '/queue.json')
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
            video = pafy.new("https://www.youtube.com/watch?v=" + videoId)
            # try:

            song = Song(video.videoid, video.title, video.author, video.getbestthumb(), video.length)
            self.songs.append(song)
            # except TypeError as e:
            #     logging.critical(str(e) + "\nRETRYING...")
            #     self.add(videoId)
            #
            # except PytubeError as e:
            #     logging.critical(str(e) + "\nRETRYING...")
            #     self.add(videoId)

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

    def name_remove(self, name):
        for song in self.songs:
            if song.title == name:
                self.songs.remove(song)
                break

    def get_by_id(self, videoId):
        for song in self.songs:
            if song.id == videoId:
                return song

    def get_by_name(self, name):
        for song in self.songs:
            if song.title == name:
                return song

    def size(self):
        return len(self.songs)

    def peek(self, index):
        try:
            return self.songs[index]
        except IndexError:
            return None

    def move(self, start, end):
        if start < 0 or start >= len(self.songs) or end < 0 or end >= len(self.songs):
            raise ValueError
        self.songs.insert(end, self.songs.pop(start))

    def move_by_id(self, videoId, position):
        if position > len(self.songs) or position < 0:
            raise ValueError
        song = self.get_by_id(videoId)
        curPos = self.songs.index(song)
        if curPos == position:
            raise KeyError
        if song:
            self.songs.remove(song)
            self.songs.insert(position, song)

    def empty(self):
        self.songs = []

    def restore(self, videoId, position):
        yt = YouTube("https://www.youtube.com/watch?v=" + videoId)
        try:

            song = Song(yt.video_id, yt.title, yt.author, yt.thumbnail_url, yt.length)
            self.songs.insert(position, song)

        except TypeError as e:
            logging.critical(str(e) + "\nRETRYING...")
            self.restore(videoId, position)

        except PytubeError as e:
            logging.critical(str(e) + "\nRETRYING...")
            self.restore(videoId, position)
