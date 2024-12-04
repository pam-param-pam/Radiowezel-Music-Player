from enum import Enum
from typing import Union

from Song import Song
from guard import canPlay


class StateType(Enum):
    UNKNOWN = 0
    PAUSED = 1
    FORCE_PAUSED = 2
    FORCE_STOPPED = 3
    # DING_DONG = 4
    # MICROPHONE_ON = 5
    PLAYING = 6
    FETCHING = 7
    SONG_FINISHED = 8
    IDLE = 9


class ActiveType(Enum):
    PLAYER = 1
    MICROPHONE = 2
    DING_DONG = 3


class StateManager:

    def __init__(self):
        self.currentSong: Union[Song, None] = None
        self._state: Union[StateType, None] = StateType.IDLE
        self._active: ActiveType = ActiveType.PLAYER
        self.repeat: bool = False
        self.song_position: Union[int, None] = None
        self.volume: Union[int, None] = None
        self.speed: Union[int, None] = None

    def __str__(self) -> str:
        return self.getStateMessage()

    def __repr__(self):
        return self.getStateMessage()

    def can_play(self):
        return canPlay() and self._state not in (StateType.FORCE_PAUSED, StateType.FORCE_STOPPED) and self._active == ActiveType.PLAYER

    def can(self):
        return False

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

    def set_active(self, active):
        self._active = active

    def get_active(self):
        return self._active

