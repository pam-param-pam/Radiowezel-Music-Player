from colorama import Fore

from Fun.ArgumentException import IncorrectArgument
from Fun.Commands import HelpCommand, RepeatCommand, SeekCommand, MoveCommand, VolumeCommand, QueueCommand, \
    RemoveCommand, InfoCommand, PauseCommand, PlayCommand, AddCommand, DebugCommand, NextCommand


class ArgumentParser:
    def __init__(self, pl):
        self.commands = []
        self.register_command_class(PlayCommand(pl, ("play",)))
        self.register_command_class(NextCommand(pl, ("next",)))
        self.register_command_class(PauseCommand(pl, ("pause", "stop")))
        self.register_command_class(InfoCommand(pl, ("info", )))
        self.register_command_class(AddCommand(pl, ("add", )))
        self.register_command_class(RemoveCommand(pl, ("remove", "rem", )))
        self.register_command_class(QueueCommand(pl, ("queue", )))
        self.register_command_class(VolumeCommand(pl, ("volume", )))
        self.register_command_class(MoveCommand(pl, ("move", )))
        self.register_command_class(SeekCommand(pl, ("seek", )))
        self.register_command_class(RepeatCommand(pl, ("repeat",)))
        self.register_command_class(DebugCommand(pl, ("debug",)))

        self.register_command_class(HelpCommand(pl, self.commands, ("help", )))

    def get_commands(self):
        return self.commands

    def register_command_class(self, command):
        self.commands.append(command)

    def parse_arguments(self, input_str):
        try:
            input_list = input_str.split()

            prefix = input_list[0].lower()
            for command in self.commands:

                if prefix in command.getNames():
                    args = input_list[1:]
                    try:
                        command.execute(args)
                        return
                    except IncorrectArgument as e:
                        print(Fore.RED + str(e))
                        return
            print(Fore.RED + "Command not found")
        except IndexError:
            print(Fore.RED + "command not found")
