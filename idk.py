import json
import logging
import threading
import time
from json import JSONDecodeError

import websocket

from Player import Player
from guard import canPlay

pl = Player()

pl.start()
"""
logger.basicConfig(filename="logs.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logger.DEBUG)
"""
logger = logging.getLogger('Main')
logger.setLevel(logging.WARNING)
timeBetweenSongs = 0  # seconds


def process_message(message):
    logger.debug("Processing message: " + message)
    try:
        jMessage = json.loads(message)
        taskId = jMessage["taskId"]
        pl.taskId = taskId
        action = jMessage["action"]

        if jMessage["worker"] == "player":
            if action == "play":
                logger.debug("Matched player play")
                pl.play()
                pl.taskId = None
            elif action == "stop":
                logger.debug("Matched player stop")
                pl.stop()
                pl.taskId = None
            elif action == "pause":
                logger.debug("Matched player pause")
                pl.pause()
                pl.taskId = None
            elif action == "smooth_pause":
                logger.debug("Matched player pause")
                pl.pauseFadeout()
                pl.taskId = None
            elif action == "resume":
                logger.debug("Matched player resume")
                pl.play()
                pl.taskId = None
            elif action == "seek":
                logger.debug("Matched player seek")
                pl.seek(jMessage["extras"]["seconds"])
                pl.taskId = None
            elif action == "next":
                logger.debug("Matched player next")
                pl.next()
                pl.taskId = None
            elif action == "set_volume":
                logger.debug("Matched player set volume")
                pl.set_volume(jMessage["extras"]["volume"])
                pl.taskId = None
            elif action == "get_volume":
                logger.debug("Matched player get volume")
                pl.get_volume()
                pl.taskId = None
            elif action == "toggle_repeat":
                logger.debug("Matched player toggle repeat")
                pl.toggle_repeat()
                pl.taskId = None
            elif action == "get_repeat":
                logger.debug("Matched player toggle repeat")
                pl.get_repeat()
                pl.taskId = None
            elif action == "ding-dong":
                logger.debug("Matched player ding-dong")
                pl.dingDong()
                pl.taskId = None
            else:
                logger.warning("None matched")

        elif jMessage["worker"] == "queue":

            if action == "add":
                logger.debug("Matched queue add")
                pl.add_to_queue(jMessage["extras"]["videoId"])
                pl.taskId = None
            elif action == "restore":
                logger.debug("Matched queue restore")
                pl.restore_in_queue(jMessage["extras"]["videoId"], jMessage["extras"]["position"])
                pl.taskId = None
            elif action == "remove":
                logger.debug("Matched queue remove")
                pl.remove_from_queue(jMessage["extras"]["videoId"])
                pl.taskId = None
            elif action == "move":
                logger.debug("Matched queue move")
                pl.move_in_queue(jMessage["extras"]["starting_i"], jMessage["extras"]["ending_i"])
                pl.taskId = None
            elif action == "empty":
                pl.empty_queue()
                pl.taskId = None
            elif action == "get":
                pl.notifyAboutQueueChange()
                pl.taskId = None
            elif action == "spotify":
                pl.fetch_songs_from_playlist(jMessage["extras"]["playlist_id"])
                pl.taskId = None
            else:
                logger.warning("None matched")
                pl.communicateBack("Couldn't match any")
        else:
            logger.warning("None matched")
    except (KeyError, JSONDecodeError):
        logger.warning("None matched")


def on_message(webSocket, message):
    def run(*args):
        logger.info("Got a message: " + message)
        process_message(message)

    threading.Thread(target=run).start()


def on_ping(webSocket, message):
    logger.debug("Got a ping! A pong reply has already been automatically sent.")


def on_pong(webSocket, message):
    logger.debug("Got a pong: " + message + ". No need to respond")


def on_open(webSocket):
    logger.debug("ws opened")


def on_close(webSocket, status_code, reason):
    logger.debug("ws closed, status: " + status_code + ", reason: " + reason)


def on_error(webSocket, error):
    logger.error("Error happened in ws:\n" + str(error))


ws = websocket.WebSocketApp("wss://pamparampam.dev/player", on_message=on_message, on_ping=on_ping, on_pong=on_pong,
                            on_close=on_close,
                            on_error=on_error,
                            on_open=on_open, header={"token": 'RXdhQ3phamtvd3NrYQ=='})


def send_pos():
    a = 0
    while True:
        try:
            if pl.currentSong:

                pos = pl.formatSeconds(round(pl.musicPos))
                length = pl.formatSeconds(pl.get_length())
                b = round((pl.musicPos * 10000) / pl.get_length())
                if pl.VLCPlayer.is_playing():

                    if a != b:
                        pl.communicateBack(
                            {"worker": "player", "pos": b, "title": pl.currentSong.title, "taskId": 100_000,
                             "length": length, "seconds": pos}, False)
                        a = b
                else:
                    if pl.stopped or pl.force_stopped:
                        pl.communicateBack(
                            {"worker": "player", "pos": b, "title": "Stopped(" + pl.currentSong.title + ")",
                             "taskId": 100_000,
                             "length": length, "seconds": pos}, False)
            else:
                pl.communicateBack(
                    {"worker": "player", "pos": 0, "title": "Nothing is playing", "taskId": 100_000,
                     "length": "00:00", "seconds": "00:00"}, False)

        except Exception as e:
            logger.error("Error happened in send_pos:\n" + str(e))
        time.sleep(1)


def run_for_eternity():
    pl.comms = ws
    ws.run_forever(
        reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly


def listener():
    while True:
        try:

            if not pl.VLCPlayer.is_playing():

                if not pl.stopped or not pl.force_stopped:
                    time.sleep(timeBetweenSongs)
                    if pl.repeat:
                        pl.restore_in_queue(pl.currentSong.id, 0)
                        pl.play()
                    else:
                        pl.currentSong = None
                        pl.play()
        except Exception as e:
            logger.error("Error happened in listener:\n" + str(e))

        time.sleep(1)


wst = threading.Thread(target=run_for_eternity)
wst.start()

lst = threading.Thread(target=listener)
lst.start()

time.sleep(1)

sp = threading.Thread(target=send_pos)
sp.start()

pl.add_to_queue('DtVBCG6ThDk')

pl.play()

while True:
    time.sleep(10)
    logger.debug("10 seconds passed")

    if not canPlay() and not pl.force_stopped:
        logger.info("Break is over! Stopping music...")
        pl.pauseFadeout()
        pl.force_stopped = True

    if canPlay() and not pl.stopped and not pl.VLCPlayer.is_playing():
        if pl.queue.is_empty():
            logger.debug("Break started! No music to start")

        else:
            logger.info("Break started! Starting music")
            pl.force_stopped = False
            pl.play()
