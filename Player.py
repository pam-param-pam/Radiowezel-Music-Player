import base64
import json
import logging
import math
import os
import threading
import time
from threading import Thread
import matplotlib.pyplot as plt

import jsonpickle
import numpy as np
import pafy
import pyaudio
import requests
import spotipy
import vlc
from colorama import Fore, Style
from spotipy import SpotifyClientCredentials, SpotifyException
from websocket import WebSocketConnectionClosedException

import guard
from Song import Song
from SongsQueue import SongsQueue
from StateManager import StateManager, StateType
from exceptions import AgeRestrictedVideo, VideoTooLong
from guard import canPlay

logger = logging.getLogger('Main')


class Player(Thread):

    def __init__(self):
        Thread.__init__(self)

        self.comms = None
        self.queue = SongsQueue()
        self.instance = vlc.Instance("prefer-insecure")
        self.vlc_events = None
        self.VLCPlayer = self.instance.media_player_new()

        self.vlc_events = self.VLCPlayer.event_manager()
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerEndReached, self.song_finished_callback)

        self.pyAudio = None
        self.stream = None

        self.state = StateManager()

        # self.repeat = False
        # self.force_stopped = False
        # self.fetching = False
        # self.currentSong = None
        # self.musicPos = 0
        # self.stopped = False

    def run(self):
        logger.info("Hello from Player")

    def song_finished_callback(self, data):
        logger.debug("Song finished")
        self.state.set_state(StateType.SONG_FINISHED)
        if self.state.repeat:
            logger.debug("Song finished repeat")
            self.restore_in_queue(self.currentSong.id, 0)

        logger.debug("Song finished next")

        self.state.currentSong = None

    # def calc_volume(self):
    #     if self.currentSong:
    #         response = requests.get(self.state.currentSong.url,
    #                                 stream=True)
    #         val = 10
    #         # Iterate over the chunks of data and write them to a file
    #         rms_list = []
    #         for chunk in response.iter_content(chunk_size=1024):
    #             if chunk:
    #                 data_np = np.frombuffer(chunk, dtype=np.int16)
    #
    #                 rms = np.sqrt(np.mean(np.square(data_np)))
    #                 if not math.isnan(rms):
    #                     rms_list.append(rms)
    #                 if len(rms_list) > 100 * val:
    #                     break
    #                 percentage = round(len(rms_list) / val) + 1
    #                 # if percentage <= 100:
    #                 #    sys.stdout.write(u"\u001b[1000D" + str(round(len(rms_list) / val) + 1) + "%")
    #                 #   sys.stdout.flush()
    #
    #         plt.plot(rms_list)
    #         plt.title(self.currentSong.title)
    #         plt.xlabel('Time (chunks of 1024 samples)')
    #         plt.ylabel('RMS Value')
    #         plt.show()
    #         print(self.currentSong.title)
    #         print(max(rms_list))
    #         print(min(rms_list))
    #         print(sum(rms_list) / len(rms_list))
    #
    #         # Define a step size for the ranges
    #         step = 15
    #
    #         # Create a list of ranges
    #         ranges = [(i, i + step) for i in range(int(min(rms_list)), int(max(rms_list)))]
    #
    #         # Count the number of values in each range
    #         counts = [len([x for x in rms_list if r[0] <= x < r[1]]) for r in ranges]
    #
    #         # Find the index of the range with the highest count
    #         max_count_index = counts.index(max(counts))
    #
    #         # Get the range with the highest count
    #         most_common_range = ranges[max_count_index]
    #
    #         # Print the most common range and its count
    #         print(f"The most common range is {most_common_range} with a count of {max(counts)}")

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
        logger.debug("set speed request acknowledged")

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

        self.state.speed = speed

    def resume(self):
        logger.debug("Resume request acknowledged")

        state = self.state.get_state()
        if canPlay() and state != StateType.FORCE_PAUSED:
            self.VLCPlayer.set_pause(False)
            self.state.set_state(StateType.PLAYING)

    def play(self, isNext=False):
        logger.debug("Play request acknowledged")

        state = self.state.get_state()
        if not canPlay() or state == StateType.FORCE_STOPPED:
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "error",
                 "info": "Cannot play now"})
            return

        if state == StateType.MICROPHONE_ON:
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "error",
                 "info": "Microphone is ON"})
            return

        isPlaying = self.VLCPlayer.is_playing()
        if isPlaying and not isNext:
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "warning",
                 "info": "Already playing"})
            return

        if self.state.get_state() == StateType.PAUSED and not isNext:  # nie gra bo zatrzymane
            self.resume()
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "success",
                 "info": "Resuming"})
            return

        if self.VLCPlayer.get_state() == vlc.State.Opening and not isNext:
            self.communicateBack(
                {"worker": "player", "action": "play", "cookie": "rewrite", "status": "warning",
                 "info": "Already Fetching"})
            return

        else:  # nie gra bo nigdy nie gralo
            self.state.set_state(StateType.FETCHING)
            if not self.queue.is_empty() or True:
                song = self.queue.peek(0)
                song = "aaaaaaaaaaa"
                print(song)
                if song:

                    self.communicateBack(
                        {"worker": "player", "action": "play", "cookie": "rewrite", "status": "info",
                         "info": "Fetching..."})
                    logger.debug("1 in player")
                    # yt = YouTube("https://www.youtube.com/watch?v=" + song.id)
                    url = "https://idrive.pamparampam.dev/api/stream/G6Py2uLZFjBEjh2mh7A5XE:1tIaam:11hnqcm1VLveCeiuiVY0ow2UYKb0lxgivNepmFmQ1ek?inline=True"
                    print(url)

                    logger.debug("2 in player")
                    logger.debug("3 in player")
                    logger.debug("4 in player")
                    media = self.instance.media_new(url)
                    logger.debug("5 in player")
                    media.get_mrl()
                    logger.debug("6 in player")
                    self.VLCPlayer.set_media(media)
                    logger.debug("7 in player")
                    self.VLCPlayer.play()
                    logger.debug("8 in player")

                    self.state.currentSong = Song(author="aa", title="aa", thumbnail="aaa", length=200, id="aaa")

                    self.state.currentSong.url = url
                    while not self.VLCPlayer.is_playing:
                        pass

                    # self.queue.remove_by_index(0)
                    self.notifyAboutQueueChange()
                    self.state.set_state(StateType.PLAYING)

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

    def next(self):
        self.play(True)

    def toggle_repeat(self):
        logger.debug("Toggle repeat request acknowledged")

        self.state.repeat = not self.state.repeat
        self.communicateBack(
            {"worker": "player", "action": "toggle_repeat", "cookie": "rewrite", "status": "success", "info": "Toggled"})

    def rewind(self):
        logger.debug("Rewind request acknowledged")

        self.VLCPlayer.set_time(0)

    def pauseFadeout(self):
        logger.debug("Pause fadeout request acknowledged")
        if self.VLCPlayer.is_playing():
            self.communicateBack(
                {"worker": "player", "action": "stop", "cookie": "rewrite", "status": "info", "info": "Pausing..."})

            volume = self.VLCPlayer.audio_get_volume()

            for x in range(100):
                self.VLCPlayer.audio_set_volume(int(volume - (volume / 100) * x))
                time.sleep(0.03)

            self.VLCPlayer.set_pause(True)
            self.state.set_state(StateType.PAUSED)

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
            self.state.set_state(StateType.PAUSED)
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
            {"worker": "queue", "action": "get_repeat", "cookie": "rewrite", "status": "success", "state": self.state.repeat})

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

    def ding_dong(self):
        self.pause()
        mp3_file_path = "assets/ding-dong.mp3"
        p = vlc.MediaPlayer(mp3_file_path)
        p.play()
        time.sleep(4)
        self.resume()

    def start_microphone(self):
        self.pyAudio = pyaudio.PyAudio()
        SAMPLE_RATE = 16000
        CHUNK = 1024
        self.stream = self.pyAudio.open(format=pyaudio.paInt16,
                                        channels=1,
                                        rate=SAMPLE_RATE,
                                        output=True,
                                        frames_per_buffer=CHUNK)

        self.pause()
        self.state.set_state(StateType.MICROPHONE_ON)
        mp3_file_path = "assets/ding-dong.mp3"
        p = vlc.MediaPlayer(mp3_file_path)
        p.play()
        self.communicateBack(
            {"worker": "microphone", "action": "start", "cookie": "rewrite", "status": "success",
             "info": "Started Microphone"})

    def stop_microphone(self):
        self.pyAudio = None
        self.stream.stop_stream()
        self.stream = None

        # if not self.state.get_state() != StateType.PAUSED:
        #     self.play()
        self.state.set_state(StateType.IDLE)
        self.resume()
        time.sleep(60)

    def process_microphone(self, bytes_data):
        audio_data = base64.b64decode(bytes_data)  # Convert Base64 back to bytes

        # Convert bytes to numpy array (assuming 16-bit audio)
        audio_samples = np.frombuffer(audio_data, dtype=np.int16)

        # Adjust volume (e.g., 0.5 for 50% volume, 1.5 for 150% volume)
        volume_multiplier = self.VLCPlayer.audio_get_volume() / 50
        adjusted_samples = (audio_samples * volume_multiplier).astype(np.int16)

        # Convert back to bytes
        adjusted_audio_data = adjusted_samples.tobytes()

        self.stream.write(adjusted_audio_data)  # Directly play the incoming bytes

