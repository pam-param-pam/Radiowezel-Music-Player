import base64
import json
import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import colorama
import numpy as np
import pyaudio
import websocket
from colorama import Fore, Style
from pydub import AudioSegment
from pydub.utils import make_chunks

from Fun.ArgumentParser import ArgumentParser
from Player import Player
from guard import canPlay

pl = Player()

pl.start()
# logging.basicConfig(filename="mlog.txt", filemode="a", format="%(asctime)s,%(msecs)d %(name)s %(levelname)s $(message)s$", datefmt="%H:%M:%S", level=logging.DEBUG)
logger = logging.getLogger('Main')
logger.setLevel(logging.INFO)
timeBetweenSongs = 0  # seconds

pl.executor = ThreadPoolExecutor(max_workers=5)
p = pyaudio.PyAudio()
SAMPLE_RATE = 16000
CHUNK = 1024
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK)


def process_message(message):
    logger.debug("Processing message: " + message)

    jMessage = json.loads(message)

    taskId = jMessage["taskId"]
    action = jMessage["action"]
    threading.current_thread().setName(str(taskId))
    if jMessage["worker"] == "player":
        if action == "play":
            logger.debug("Matched player play")
            pl.play()
            calculate_pos(True)
        elif action == "stop":
            logger.debug("Matched player stop")
            pl.stop()
            calculate_pos(True)
        elif action == "pause":
            logger.debug("Matched player pause")
            pl.pause()
            calculate_pos(True)
        elif action == "smooth_pause":
            logger.debug("Matched player pause")
            pl.pauseFadeout()
            calculate_pos(True)
        elif action == "resume":
            logger.debug("Matched player resume")
            pl.play()
            calculate_pos(True)
        elif action == "seek":
            logger.debug("Matched player seek")
            pl.seek(jMessage["extras"]["seconds"])
        elif action == "next":
            logger.debug("Matched player next")
            pl.next()
            calculate_pos(True)
        elif action == "set_volume":
            logger.debug("Matched player set volume")
            pl.set_volume(jMessage["extras"]["volume"])
        elif action == "get_volume":
            logger.debug("Matched player get volume")
            pl.get_volume()
        elif action == "toggle_repeat":
            logger.debug("Matched player toggle repeat")
            pl.toggle_repeat()
        elif action == "get_repeat":
            logger.debug("Matched player toggle repeat")
            pl.get_repeat()
        elif action == "ding_dong":
            logger.debug("Matched player ding dong")
            pl.ding_dong()
        elif action == "get_pos":
            logger.debug("Matched player get pos ")
            calculate_pos(True)
        else:
            logger.warning("None player matched")

    elif jMessage["worker"] == "queue":

        if action == "add":
            logger.debug("Matched queue add")
            pl.add_to_queue(jMessage["extras"]["videoId"])
        elif action == "restore":
            logger.debug("Matched queue restore")
            pl.restore_in_queue(jMessage["extras"]["videoId"], jMessage["extras"]["position"])
        elif action == "remove":
            logger.debug("Matched queue remove")
            pl.remove_from_queue(jMessage["extras"]["videoId"])
        elif action == "move":
            logger.debug("Matched queue move")
            pl.move_in_queue(jMessage["extras"]["starting_i"], jMessage["extras"]["ending_i"])
        elif action == "move_by_id":
            logger.debug("Matched queue move by id")
            pl.move_by_id_in_queue(jMessage["extras"]["videoId"], jMessage["extras"]["position"])
        elif action == "empty":
            logger.debug("Matched queue empty")
            pl.empty_queue()
        elif action == "get":
            logger.debug("Matched queue get")
            pl.notifyAboutQueueChange()
        elif action == "spotify":
            logger.debug("Matched queue spotify")
            pl.fetch_songs_from_playlist(jMessage["extras"]["playlist_id"])
        else:
            logger.warning("None queue matched")
            pl.communicateBack("Couldn't match any")

    elif jMessage["worker"] == "microphone":

        if action == "mic_audio":
            logger.debug("Matched microphone mic audio")
            bytes_data = jMessage["extras"]["data"]

            if bytes_data:
                audio_data = base64.b64decode(bytes_data)  # Convert Base64 back to bytes

                # Convert bytes to numpy array (assuming 16-bit audio)
                audio_samples = np.frombuffer(audio_data, dtype=np.int16)

                # Adjust volume (e.g., 0.5 for 50% volume, 1.5 for 150% volume)
                volume_multiplier = 1
                adjusted_samples = (audio_samples * volume_multiplier).astype(np.int16)

                # Convert back to bytes
                adjusted_audio_data = adjusted_samples.tobytes()

                stream.write(adjusted_audio_data)  # Directly play the incoming bytes

    else:
        logger.warning("None worker matched")


def on_message(webSocket, message):
    def run(*args):
        process_message(message)

    future = pl.executor.submit(run)
    exception = future.exception()
    # handle exceptional case
    if exception:
        print("".join(traceback.TracebackException.from_exception(exception).format()))


def on_ping(webSocket, message):
    logger.debug("Got a ping! A pong reply has already been automatically sent.")


def on_pong(webSocket, message):
    logger.debug("Got a pong: %s. No need to respond", message)


def on_open(webSocket):
    logger.debug("ws opened")


def on_close(webSocket, status_code, reason):
    logger.debug("ws closed, status: " + str(status_code) + ", reason: " + reason)


def on_error(webSocket, error):
    logger.error(Fore.RED + "Error happened in ws: %s", error)

ws = websocket.WebSocketApp("ws://192.168.1.14:8000/player", on_message=on_message, on_ping=on_ping, on_pong=on_pong,

# ws = websocket.WebSocketApp("wss://pamparampam.dev/player", on_message=on_message, on_ping=on_ping, on_pong=on_pong,
                            on_close=on_close,
                            on_error=on_error,
                            on_open=on_open, header={"token": 'UlhkaFEzcGhhbXR2ZDNOcllRPT0==='})


def calculate_pos(flag=False):
    length = pl.get_length()
    if pl.currentSong and length:

        FormattedPos = pl.formatSeconds(round(pl.VLCPlayer.get_time() / 1000))
        FormattedLength = pl.formatSeconds(length / 1000)
        b = round((pl.VLCPlayer.get_time() * 10000) / length)
        if pl.VLCPlayer.is_playing():

            pl.communicateBack(
                {"worker": "player", "pos": b, "title": pl.currentSong.title, "taskId": 100_000,
                 "length": FormattedLength, "seconds": FormattedPos}, False)

        else:
            if pl.stopped or pl.force_stopped:
                if flag:
                    pl.communicateBack(
                        {"worker": "player", "pos": b, "title": "Stopped(" + pl.currentSong.title + ")",
                         "taskId": 100_000,
                         "length": FormattedLength, "seconds": FormattedPos}, False)

    else:
        if flag:
            pl.communicateBack(
                {"worker": "player", "pos": 0, "status": "success", "title": "Nothing is playing", "taskId": 100_000,
                 "length": "00:00", "seconds": "00:00"}, False)


def send_pos():
    while True:
        try:
            calculate_pos()
        except Exception as e:
            logger.error(Fore.RED + "Error happened in send_pos:\n %s", str(e))
        time.sleep(1)


def run_for_eternity():
    pl.comms = ws
    ws.run_forever(
        reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly


def wait_for_input():
    colorama.init(autoreset=True)

    parser = ArgumentParser(pl)

    while True:
        try:
            a = input()
            parser.parse_arguments(a)
        except Exception as e:
            logger.error(Style.BRIGHT + Fore.RED + "Error happened in wait for input:\n %s", str(e))


wst = threading.Thread(target=run_for_eternity, name='websocket')
wst.start()

time.sleep(1)

sp = threading.Thread(target=send_pos, name='send position')
sp.start()

wfi = threading.Thread(target=wait_for_input, name='interactive input')
wfi.start()

while True:
    try:
        time.sleep(10)
        logger.debug("10 seconds passed")

        if not canPlay() and not pl.force_stopped:
            logger.info("Break is over! Stopping music...")
            pl.pauseFadeout(False)
            pl.force_stopped = True

        if canPlay() and not pl.stopped and not pl.VLCPlayer.is_playing() and not pl.fetching:
            if pl.queue.is_empty():
                logger.debug("No music to start")
            elif pl.repeat and not pl.force_stopped:
                logger.debug("Repeating music")
                pl.play()
            elif not pl.repeat and not pl.force_stopped:
                logger.debug("Playing next song")
                pl.play()
            else:
                logger.info("Break started! Starting music...")
                pl.force_stopped = False
                pl.play()
    except Exception as e:
        logger.error(Fore.RED + "Error happened in while TRUE:\n %s", str(e))
        pl.fetching = False
