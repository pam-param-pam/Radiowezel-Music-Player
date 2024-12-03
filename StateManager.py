from enum import Enum
from typing import Union

from Song import Song


class StateType(Enum):
    UNKNOWN = 0
    PAUSED = 1
    FORCE_PAUSED = 2
    FORCE_STOPPED = 3
    DING_DONG = 4
    MICROPHONE_ON = 5
    PLAYING = 6
    FETCHING = 7
    SONG_FINISHED = 8
    IDLE = 9


class StateManager:

    def __init__(self):
        self.currentSong: Union[Song, None] = None
        self._state: Union[StateType, None] = StateType.IDLE
        self.repeat: bool = False
        self.song_position: Union[int, None] = None
        self.volume: Union[int, None] = None
        self.speed: Union[int, None] = None

    def __str__(self) -> str:
        return self.getStateMessage()

    def __repr__(self):
        return self.getStateMessage()

    def getStateMessage(self) -> str:
        if self._state == StateType.PLAYING:
            return self.currentSong.title
        if self._state.PAUSED:
            return f"({self.getHumanState()}) {self.currentSong.title}"

        else:
            return self.getHumanState()

    def getHumanState(self) -> str:
        return self._state.name.replace("_", " ").capitalize()

    def set_state(self, state: StateType):
        self._state = state

    def get_state(self):
        return self._state

