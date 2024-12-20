import json
import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import colorama
import websocket
from colorama import Fore, Style

from Fun.ArgumentParser import ArgumentParser
from Player import Player
from StateManager import StateType
from guard import canPlay

pl = Player()

pl.start()
# logging.basicConfig(filename="mlog.txt", filemode="a", format="%(asctime)s,%(msecs)d %(name)s %(levelname)s $(message)s$", datefmt="%H:%M:%S", level=logging.DEBUG)
logger = logging.getLogger('Main')
logger.setLevel(logging.INFO)
timeBetweenSongs = 0  # seconds

pl.executor = ThreadPoolExecutor(max_workers=5)


def process_message(message):
    logger.debug("Processing message: " + message)

    jMessage = json.loads(message)

    taskId = jMessage["taskId"]
    action = jMessage["action"]
    threading.current_thread().name = str(taskId)
    if jMessage["worker"] == "player":
        if action == "play":
            logger.debug("Matched player play")
            pl.play()
            pl.send_state()
        elif action == "stop":
            logger.debug("Matched player stop")
            pl.stop()
            pl.send_state()
        elif action == "pause":
            logger.debug("Matched player pause")
            pl.pause()
            pl.send_state()
        elif action == "smooth_pause":
            logger.debug("Matched player pause")
            pl.pauseFadeout()
            pl.send_state()
        elif action == "resume":
            logger.debug("Matched player resume")
            pl.play()
            pl.send_state()
        elif action == "seek":
            logger.debug("Matched player seek")
            pl.seek(jMessage["extras"]["seconds"])
            pl.send_state()
        elif action == "next":
            logger.debug("Matched player next")
            pl.next()
            pl.send_state()
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
        elif action == "get_state":
            logger.debug("Matched player get state ")
            pl.send_state()
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
        if action == "start":
            logger.debug("Matched microphone start")
            pl.start_microphone()
            pl.send_state()

        elif action == "mic_audio":
            logger.debug("Matched microphone mic audio")
            bytes_data = jMessage["extras"]["data"]
            pl.process_microphone(bytes_data)

        elif action == "stop":
            logger.debug("Matched microphone stop")
            pl.stop_microphone()
            pl.send_state()

    else:
        logger.warning("None worker matched")


def on_message(webSocket, message):
    def run(*args):
        process_message(message)

    future = pl.executor.submit(run)
    exception = future.exception()
    # handle exceptional case
    if exception:
        tb = "".join(traceback.TracebackException.from_exception(exception).format())
        print(tb)
        pl.communicateBack(
            {"worker": "unknown", "action": "unknown", "cookie": "rewrite", "status": "error", "info": tb, "taskId": 100_000}, addTaskId=False)

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


# ws = websocket.WebSocketApp("ws://192.168.1.14:8000/player", on_message=on_message, on_ping=on_ping, on_pong=on_pong,

ws = websocket.WebSocketApp("wss://pamparampam.dev/player", on_message=on_message, on_ping=on_ping, on_pong=on_pong,
                            on_close=on_close,
                            on_error=on_error,
                            on_open=on_open, header={"token": 'UlhkaFEzcGhhbXR2ZDNOcllRPT0==='})

def send_pos():
    while True:
        try:
            if pl.state.get_state() != StateType.PLAYING:
                continue
            pl.send_state()
        except Exception as e:
            logger.error(Fore.RED + "Error happened in send_pos:\n %s", str(e))
        time.sleep(0.9)


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

        if not canPlay() and pl.state.get_state() != StateType.FORCE_STOPPED:
            logger.info("Break is over! Stopping music...")
            pl.pauseFadeout()
            pl.state.set_state(StateType.FORCE_STOPPED)

        if pl.state.canBreakStartMusic() and not pl.VLCPlayer.is_playing():
            if pl.queue.is_empty():
                logger.debug("No music to start")
            else:
                logger.info("Break started! Starting music...")
                pl.state.set_state(StateType.FETCHING)
                pl.play()

    except Exception as e:
        logger.error(Fore.RED + "Error happened in while TRUE:\n %s", str(e))
