from abc import ABC, abstractmethod


class Command(ABC):

    def __init__(self, names):
        self.names = names

    @property
    @abstractmethod
    def longDesc(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def shortDesc(self):
        raise NotImplementedError

    @abstractmethod
    def execute(self, args):
        raise NotImplementedError

    def getNames(self):
        return self.names

    def getLongDesc(self):
        return self.longDesc

    def getShortDesc(self):
        return self.shortDesc
