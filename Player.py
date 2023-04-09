import json
import logging
import os
import threading
import time
from threading import Thread

import jsonpickle
import pafy
import spotipy
import vlc
from colorama import Fore, Style
from spotipy import SpotifyClientCredentials, SpotifyException
from websocket import WebSocketConnectionClosedException

import guard
from SongsQueue import SongsQueue
from exceptions import AgeRestrictedVideo, VideoTooLong
from guard import canPlay

logger = logging.getLogger('Main')


class Player(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.repeat = False
        self.force_stopped = False
        self.comms = None
        self.stopped = False
        self.queue = SongsQueue()
        self.currentSong = None
        self.musicPos = 0
        self.instance = vlc.Instance("prefer-insecure")
        self.fetching = False
        self.VLCPlayer = None
        self.vlc_events = None
        self.VLCPlayer = self.instance.media_player_new()

        self.vlc_events = self.VLCPlayer.event_manager()
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerEndReached, self.song_finished_callback)

    def run(self):
        logger.info("Hello from Player")

    def song_finished_callback(self, data):

        logger.debug("Song finished")
        if self.repeat:
            logger.debug("Song finished repeat")
            self.restore_in_queue(self.currentSong.id, 0)

        logger.debug("Song finished next")

        self.currentSong = None

    def communicateBack(self, message, addTaskId=True):
        if threading.current_thread().getName() == "CONSOLE" and addTaskId:
            m = Style.BRIGHT + Fore.MAGENTA + message["info"]
            if message["status"] == "info":
                m += Fore.LIGHTBLUE_EX
            elif message["status"] == "success":
                m += Fore.MAGENTA
            elif message["status"] == "warning":
                m += Fore.YELLOW
            else:
                m += Fore.LIGHTWHITE_EX

            print(m)

        else:
            if addTaskId:
                message["taskId"] = threading.current_thread().getName()
            try:
                if self.comms:

                    self.comms.send(json.dumps(message))
                else:
                    logger.fatal("Comms is None")
                logger.debug("Sent back %s", message)
            except WebSocketConnectionClosedException:
                if guard.isInternet():
                    logger.warning("Socket is closed, cannot communicate back")
                else:
                    logger.debug("Socket is closed due to no internet")

    def fetch_songs_from_playlist(self, playlistId):
        client_secret = "3240593b7dbc4a40b351b5e61aca2322"
        client_id = "a64b981256e14d09a2cfa51f631b20d7"
        try:

            client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            self.communicateBack(
                {"worker": "player", "action": "spotify", "cookie": "rewrite", "status": "info", "info": "Fetching..."})
            total = sp.playlist_items(playlistId)["total"]
            for track in sp.playlist_items(playlistId)["items"]:
                name = track["track"]["name"]

                artist = track["track"]["artists"][0]["name"]
                total -= 1
                try:
                    self.queue.name_add(name + " " + artist)
                except AgeRestrictedVideo:
                    self.communicateBack(
                        {"worker": "queue", "action": "spotify", "cookie": "rewrite", "status": "warning",
                         "info": "Age restricted video"})

                except VideoTooLong:
                    self.communicateBack(
                        {"worker": "queue", "action": "spotify", "cookie": "rewrite", "status": "warning",
                         "info": "Video too long"})

                self.communicateBack(
                    {"worker": "player", "action": "spotify", "cookie": "rewrite", "status": "success",
                     "info": "Added " + name + "\nLeft " + str(total)})
                self.notifyAboutQueueChange()
        except SpotifyException:
            self.communicateBack(
                {"worker": "player", "action": "spotify", "cookie": "rewrite", "status": "error",
                 "info": "Playlist Id is wrong!"})

    def formatSeconds(self, time):
        minutes = int(time / 60)
        seconds = int(time % 60)

        if minutes <= 9:
            minutes = "0" + str(minutes)

        if seconds <= 9:
            seconds = "0" + str(seconds)

        return str(minutes) + ":" + str(seconds)

    def set_speed(self, speed):
        if speed == 0.5:
            self.VLCPlayer.set_rate(0.7)
        elif speed == 0.25:
            self.VLCPlayer.set_rate(0.4)
        elif speed == 2:
            self.VLCPlayer.set_rate(1.7)
        elif speed == 1.5:
            self.VLCPlayer.set_rate(1.4)
        else:
            self.VLCPlayer.set_rate(1)

    def resume(self):
        logger.debug("Resume request acknowledged")

        if canPlay():
            self.VLCPlayer.set_pause(False)
            self.stopped = False

    def play(self, isNext=False):
        logger.debug("Play request acknowledged")
        self.fetching = True
        if canPlay():
            isPlaying = self.VLCPlayer.is_playing()
            if isPlaying and not isNext:
                self.communicateBack(
                    {"worker": "player", "action": "play", "cookie": "rewrite", "status": "warning",
                     "info": "Already playing"})

            else:
                if self.stopped and not isNext:  # nie gra bo zatrzymane
                    self.resume()
                    self.communicateBack(
                        {"worker": "player", "action": "play", "cookie": "rewrite", "status": "success",
                         "info": "Resuming"})

                else:  # nie gra bo nigdy nie gralo
                    if not self.queue.is_empty():
                        song = self.queue.peek(0)
                        if song:

                            self.communicateBack(
                                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "info",
                                 "info": "Fetching..."})
                            logger.debug("1 in player")
                            video = pafy.new("https://www.youtube.com/watch?v=" + song.id)
                            logger.debug("2 in player")
                            best = video.getbestaudio()
                            logger.debug("3 in player")
                            url = best.url
                            logger.debug("4 in player")
                            media = self.instance.media_new(url)
                            logger.debug("5 in player")
                            media.get_mrl()
                            logger.debug("6 in player")
                            self.VLCPlayer.set_media(media)
                            logger.debug("7 in player")
                            self.VLCPlayer.play()
                            logger.debug("8 in player")

                            self.currentSong = song

                            while not self.VLCPlayer.is_playing:
                                pass
                            self.queue.remove_by_index(0)
                            self.notifyAboutQueueChange()
                            if isNext:
                                self.communicateBack(
                                    {"worker": "player", "cookie": "rewrite", "action": "next", "status": "success",
                                     "info": "Playing next song"})
                            else:
                                self.communicateBack(
                                    {"worker": "player", "action": "play", "cookie": "rewrite", "status": "success",
                                     "info": "Playing"})

                    else:
                        self.communicateBack(
                            {"worker": "player", "action": "play", "cookie": "rewrite", "status": "warning",
                             "info": "Queue is empty"})
        else:
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "error",
                 "info": "Cannot play now"})
        self.fetching = False

    def next(self):
        self.play(True)

    def toggle_repeat(self):
        logger.debug("Toggle repeat request acknowledged")

        self.repeat = not self.repeat
        self.communicateBack(
            {"worker": "player", "action": "toggle_repeat", "cookie": "rewrite", "status": "success", "info": "Toggled"})

    def rewind(self):
        logger.debug("Rewind request acknowledged")

        self.VLCPlayer.set_time(0)

    def pauseFadeout(self, pause=True):
        logger.debug("Pause fadeout request acknowledged")
        if self.VLCPlayer.is_playing():
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "info", "info": "Pausing..."})

            volume = self.VLCPlayer.audio_get_volume()

            for x in range(100):
                self.VLCPlayer.audio_set_volume(int(volume - (volume / 100) * x))
                time.sleep(0.03)

            self.VLCPlayer.set_pause(True)
            if pause:
                self.stopped = True
            self.VLCPlayer.audio_set_volume(volume)
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "success", "info": "Paused"})

        else:
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "warning",
                 "info": "Nothing is playing"})

    def pause(self):
        logger.debug("Pause request acknowledged")

        if self.VLCPlayer.is_playing():
            self.VLCPlayer.set_pause(True)
            self.stopped = True
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "success", "info": "Paused"})

        else:
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "warning",
                 "info": "Nothing is playing"})

    def seek_functionality(self, slideValue):
        if 0 <= slideValue <= 10000:
            x = slideValue * round(self.get_length() / 1000) / 10000
            self.VLCPlayer.set_time(int(x * 1000))
            return x
        return 0

    def seek(self, slideValue):
        logger.debug("Seek request acknowledged")
        x = self.seek_functionality(slideValue)

        self.communicateBack(
            {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "success",
             "info": "Sought to " + str(self.formatSeconds(x))})

    def set_volume(self, volume):
        logger.debug("Set volume request acknowledged")
        try:
            if 0 <= volume <= 100:
                self.VLCPlayer.audio_set_volume(volume)
                self.communicateBack(
                    {"worker": "player", "action": "set_volume", "cookie": "rewrite", "status": "success",
                     "info": "Set volume to " + str(volume)})
        except TypeError:
            pass

    def get_volume(self):
        logger.debug("Get volume request acknowledged")
        self.communicateBack(
            {"worker": "player", "action": "set_volume", "cookie": "rewrite", "status": "success",
             "volume": round(self.VLCPlayer.audio_get_volume())})

    def get_repeat(self):
        self.communicateBack(
            {"worker": "queue", "action": "get_repeat", "cookie": "rewrite", "status": "success", "state": self.repeat})

    def add_to_queue(self, videoId):
        logger.debug("Add to queue request acknowledged")
        try:
            self.queue.add(videoId)
            song = self.queue.get_by_id(videoId)
            self.communicateBack(
                {"worker": "queue", "action": "add", "cookie": "rewrite", "status": "success",
                 "info": "Added " + song.title})
            self.notifyAboutQueueChange()
        except AgeRestrictedVideo:
            self.communicateBack(
                {"worker": "queue", "action": "add", "cookie": "rewrite", "status": "warning",
                 "info": "Age restricted video"})

        except VideoTooLong:
            self.communicateBack(
                {"worker": "queue", "action": "add", "cookie": "rewrite", "status": "warning", "info": "Video too long"})

    def notifyAboutQueueChange(self):

        logger.debug("Notify about queue change request acknowledged")

        jsonString = jsonpickle.encode(self.queue)
        try:
            with open(os.getcwd() + '/queue.json', 'w') as f:
                f.write(jsonString)
                logger.debug("wrote %s", jsonString)

        except FileNotFoundError:
            logging.warning("No such file or directory: 'queue.json'")
        except PermissionError:
            logging.warning("Permission denied: 'queue.json'")

        json_str = [ob.__dict__ for ob in self.queue.songs]
        var = {"taskId": 100_000, "status": "success", "info": "all working fine", "queue": json_str}

        self.communicateBack(var, False)

    def remove_from_queue(self, videoId):
        logger.debug("Remove from queue request acknowledged")
        try:
            song = self.queue.get_by_id(videoId)
            if song:
                self.queue.remove_by_id(videoId)

            self.communicateBack(
                {"worker": "queue", "action": "remove", "cookie": "rewrite", "status": "success",
                 "info": "Removed " + song.title})
            self.notifyAboutQueueChange()
        except ValueError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error", "info": "Wrong videoId"})

    def move_by_id_in_queue(self, videoId, position):
        logger.debug("Move by id in queue  request acknowledged")
        try:
            self.queue.move_by_id(videoId, position)
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "success", "info": "Moved"})
            self.notifyAboutQueueChange()
        except KeyError:
            pass
        except TypeError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error", "info": "Type Error"})
        except ValueError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error",
                 "info": "List index out of range"})

    def move_in_queue(self, starting_i, ending_i):

        logger.debug("Move in queue request acknowledged")
        try:
            self.queue.move(starting_i, ending_i)
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "success", "info": "Moved"})
            self.notifyAboutQueueChange()

        except TypeError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error", "info": "Type Error"})
        except ValueError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error",
                 "info": "List index out of range"})

    def empty_queue(self):
        logger.debug("Empty queue request acknowledged")

        self.queue.empty()
        self.communicateBack(
            {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "success", "info": "Emptied queue"})
        self.notifyAboutQueueChange()

    def get_length(self):

        return self.VLCPlayer.get_length()

    def restore_in_queue(self, videoId, position):
        logger.debug("Restore in queue request acknowledged")
        try:
            self.queue.restore(videoId, position)
            song = self.queue.peek(position)
            self.communicateBack(
                {"worker": "queue", "action": "restore", "cookie": "rewrite", "status": "success",
                 "info": "Added " + song.title})
            self.notifyAboutQueueChange()
        except AgeRestrictedVideo:
            self.communicateBack(
                {"worker": "queue", "action": "restore", "cookie": "rewrite", "status": "warning",
                 "info": "Age restricted video"})

        except VideoTooLong:
            self.communicateBack(
                {"worker": "queue", "action": "restore", "cookie": "rewrite", "status": "warning",
                 "info": "Video too long"})
