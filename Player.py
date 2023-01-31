import json
import logging
import os
import time
from threading import Thread
import jsonpickle
import pafy
import spotipy
from spotipy import SpotifyClientCredentials, SpotifyException
from websocket import WebSocketConnectionClosedException
import vlc
import guard
from Queue import Queue
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
        self.queue = Queue()
        self.currentSong = None
        self.taskId = None
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
        self.VLCPlayer.release()
        self.play()

    def communicateBack(self, message, removeTaskId=True):

        try:
            self.comms.send(json.dumps(message))
            # if removeTaskId:
            #   self.taskId = None
            logger.debug("Sent back \n " + str(message))
        except WebSocketConnectionClosedException:
            if guard.isInternet():
                logger.warning("Socket is closed, cannot communicate back")
            else:
                logger.debug("Socket is closed due to no internet")

    def fetch_songs_from_playlist(self, playlistId):
        client_secret = os.environ['SPOTIFY_SECRET']
        client_id = os.environ['SPOTIFY_ID']
        try:

            client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            self.communicateBack(
                {"worker": "player", "action": "spotify", "cookie": "rewrite", "status": "info", "info": "Fetching...",
                 "taskId": self.taskId}, False)
            total = sp.playlist_items(playlistId)["total"]
            for track in sp.playlist_items(playlistId)["items"]:
                name = track["track"]["name"]
                total -= 1
                try:
                    self.queue.name_add(name)
                except AgeRestrictedVideo:
                    self.communicateBack(
                        {"worker": "queue", "action": "spotify", "cookie": "rewrite", "status": "warning",
                         "info": "Age restricted video",
                         "taskId": self.taskId})

                except VideoTooLong:
                    self.communicateBack(
                        {"worker": "queue", "action": "spotify", "cookie": "rewrite", "status": "warning",
                         "info": "Video too long",
                         "taskId": self.taskId})

                self.communicateBack(
                    {"worker": "player", "action": "spotify", "cookie": "rewrite", "status": "success",
                     "info": f"Added " + name + "\nLeft " + str(total),
                     "taskId": self.taskId}, False)
                self.notifyAboutQueueChange()
        except SpotifyException:
            self.communicateBack(
                {"worker": "player", "action": "spotify", "cookie": "rewrite", "status": "error",
                 "info": f"Playlist Id is wrong!",
                 "taskId": self.taskId}, False)

    def formatSeconds(self, time):
        minutes = int(time / 60)
        seconds = int(time % 60)

        if minutes <= 9:
            minutes = "0" + str(minutes)

        if seconds <= 9:
            seconds = "0" + str(seconds)

        return str(minutes) + ":" + str(seconds)

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
                     "info": "Already playing",
                     "taskId": self.taskId})

            else:
                if self.stopped and not isNext:  # nie gra bo zatrzymane
                    self.resume()
                    self.communicateBack(
                        {"worker": "player", "action": "play", "cookie": "rewrite", "status": "success",
                         "info": "Resuming",
                         "taskId": self.taskId})

                else:  # nie gra bo nigdy nie gralo
                    if not self.queue.is_empty():
                        song = self.queue.peek(0)
                        if song:

                            self.communicateBack(
                                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "info",
                                 "info": "Fetching...",
                                 "taskId": self.taskId})

                            self.VLCPlayer = self.instance.media_player_new()

                            self.vlc_events = self.VLCPlayer.event_manager()
                            self.vlc_events.event_attach(vlc.EventType.MediaPlayerEndReached,
                                                         self.song_finished_callback)

                            video = pafy.new("https://www.youtube.com/watch?v=" + song.id)
                            best = video.getbestaudio()

                            url = best.url

                            media = self.instance.media_new(url)

                            media.get_mrl()

                            self.VLCPlayer.set_media(media)

                            self.VLCPlayer.play()
                            self.currentSong = song
                            while not self.VLCPlayer.is_playing:
                                pass
                            self.queue.remove_by_index(0)
                            self.notifyAboutQueueChange()
                            if isNext:
                                self.communicateBack(
                                    {"worker": "player", "cookie": "rewrite", "action": "next", "status": "success",
                                     "info": "Playing next song",
                                     "taskId": self.taskId})
                            else:
                                self.communicateBack(
                                    {"worker": "player", "action": "play", "cookie": "rewrite", "status": "success",
                                     "info": "Playing",
                                     "taskId": self.taskId})

                    else:
                        self.communicateBack(
                            {"worker": "player", "action": "play", "cookie": "rewrite", "status": "warning",
                             "info": "Queue is empty",
                             "taskId": self.taskId})
        else:
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "error",
                 "info": "Cannot play now",
                 "taskId": self.taskId})
        self.fetching = False

    def next(self):
        x = self.seek_functionality(10000)
        if x:
            self.communicateBack(
                {"worker": "player", "cookie": "rewrite", "action": "next", "status": "success",
                 "info": "Playing next song",
                 "taskId": self.taskId})

    def toggle_repeat(self):
        logger.debug("Toggle repeat request acknowledged")

        self.repeat = not self.repeat
        self.communicateBack(
            {"worker": "player", "action": "toggle_repeat", "cookie": "rewrite", "status": "success", "info": "Toggled",
             "taskId": self.taskId})

    def rewind(self):
        logger.debug("Rewind request acknowledged")

        self.VLCPlayer.set_time(0)

    def pauseFadeout(self):
        logger.debug("Pause fadeout request acknowledged")
        if self.VLCPlayer.is_playing():
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "info", "info": "Pausing...",
                 "taskId": self.taskId},
                False)

            volume = self.VLCPlayer.audio_get_volume()

            for x in range(100):
                self.VLCPlayer.audio_set_volume(int(volume - (volume / 100) * x))
                time.sleep(0.03)

            self.VLCPlayer.set_pause(True)
            self.stopped = True
            self.VLCPlayer.audio_set_volume(volume)
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "success", "info": "Paused",
                 "taskId": self.taskId})

        else:
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "warning",
                 "info": "Nothing is playing",
                 "taskId": self.taskId})

    def pause(self):
        logger.debug("Pause request acknowledged")

        if self.VLCPlayer.is_playing():
            self.VLCPlayer.set_pause(True)
            self.stopped = True
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "success", "info": "Paused",
                 "taskId": self.taskId})

        else:
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "warning",
                 "info": "Nothing is playing",
                 "taskId": self.taskId})

    def seek_functionality(self, slideValue):
        if 0 <= slideValue <= 10000:
            x = slideValue * round(self.get_length() / 1000) / 10000
            self.VLCPlayer.set_time(int(x * 1000))
            return x

    def seek(self, slideValue):
        logger.debug("Seek request acknowledged")
        x = self.seek_functionality(slideValue)
        if x:
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "success",
                 "info": "Sought to " + str(self.formatSeconds(x)),
                 "taskId": self.taskId})

    def set_volume(self, volume):
        logger.debug("Set volume request acknowledged")

        if 0 <= volume <= 100:
            self.VLCPlayer.audio_set_volume(volume)
            self.communicateBack(
                {"worker": "player", "action": "set_volume", "cookie": "rewrite", "status": "success",
                 "info": "Set volume to " + str(volume),
                 "taskId": self.taskId})

    def get_volume(self):
        logger.debug("Get volume request acknowledged")
        self.communicateBack(
            {"worker": "player", "action": "set_volume", "cookie": "rewrite", "status": "success",
             "volume": round(self.VLCPlayer.audio_get_volume()),
             "taskId": self.taskId})

    def get_repeat(self):
        self.communicateBack(
            {"worker": "queue", "action": "get_repeat", "cookie": "rewrite", "status": "success", "state": self.repeat,
             "taskId": self.taskId})

    def add_to_queue(self, videoId):
        logger.debug("Add to queue request acknowledged")
        try:
            self.queue.add(videoId)
            song = self.queue.get_by_id(videoId)
            self.communicateBack(
                {"worker": "queue", "action": "add", "cookie": "rewrite", "status": "success",
                 "info": "Added " + song.title,
                 "taskId": self.taskId})
            self.notifyAboutQueueChange()
        except AgeRestrictedVideo:
            self.communicateBack(
                {"worker": "queue", "action": "add", "cookie": "rewrite", "status": "warning",
                 "info": "Age restricted video",
                 "taskId": self.taskId})

        except VideoTooLong:
            self.communicateBack(
                {"worker": "queue", "action": "add", "cookie": "rewrite", "status": "warning", "info": "Video too long",
                 "taskId": self.taskId})

    def notifyAboutQueueChange(self):

        logger.debug("Notify about queue change request acknowledged")

        jsonString = jsonpickle.encode(self.queue)

        with open('queue.json', 'w') as f:
            f.write(jsonString)
            logger.debug("wrote " + jsonString)

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
                 "info": "Removed " + song.title,
                 "taskId": self.taskId})
            self.notifyAboutQueueChange()
        except ValueError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error", "info": "Wrong videoId",
                 "taskId": self.taskId})

    def move_in_queue(self, starting_i, ending_i):

        logger.debug("Move in queue request acknowledged")
        try:
            self.queue.move(starting_i, ending_i)
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "success", "info": "Moved",
                 "taskId": self.taskId})
            self.notifyAboutQueueChange()

        except TypeError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error", "info": "Type Error",
                 "taskId": self.taskId})
        except ValueError:
            self.communicateBack(
                {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "error",
                 "info": "List index out of range"})

    def empty_queue(self):
        logger.debug("Empty queue request acknowledged")

        self.queue.empty()
        self.communicateBack(
            {"worker": "queue", "action": "move", "cookie": "rewrite", "status": "success", "info": "Emptied queue",
             "taskId": self.taskId})
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
                 "info": "Added " + song.title,
                 "taskId": self.taskId})
            self.notifyAboutQueueChange()
        except AgeRestrictedVideo:
            self.communicateBack(
                {"worker": "queue", "action": "restore", "cookie": "rewrite", "status": "warning",
                 "info": "Age restricted video",
                 "taskId": self.taskId})

        except VideoTooLong:
            self.communicateBack(
                {"worker": "queue", "action": "restore", "cookie": "rewrite", "status": "warning",
                 "info": "Video too long",
                 "taskId": self.taskId})
