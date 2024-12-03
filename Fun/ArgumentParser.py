import threading
import traceback

from colorama import Fore, Style

from Fun.Commands import HelpCommand, RepeatCommand, SeekCommand, MoveCommand, VolumeCommand, QueueCommand, \
    RemoveCommand, InfoCommand, PauseCommand, PlayCommand, AddCommand, NextCommand, SpeedCommand, ClearCommand, EvalCommand, DingDongCommand, LogCommand, AuthorCommand, \
    FakeMicrophoneCommand


class ArgumentParser:
    def __init__(self, pl):
        self.commands = []
        self.pl = pl
        self.thread = None
        self.last_command = None
        self.register_command_class(PlayCommand(pl, ("play", "resume")))
        self.register_command_class(NextCommand(pl, ("next",)))
        self.register_command_class(PauseCommand(pl, ("pause", "stop")))
        self.register_command_class(InfoCommand(pl, ("info",)))
        self.register_command_class(AddCommand(pl, ("add",)))
        self.register_command_class(RemoveCommand(pl, ("remove", "rm",)))
        self.register_command_class(QueueCommand(pl, ("queue",)))
        self.register_command_class(VolumeCommand(pl, ("volume",)))
        self.register_command_class(MoveCommand(pl, ("move",)))
        self.register_command_class(SeekCommand(pl, ("seek",)))
        self.register_command_class(RepeatCommand(pl, ("repeat",)))
        self.register_command_class(LogCommand(pl, ("log",)))
        self.register_command_class(SpeedCommand(pl, ("speed",)))
        self.register_command_class(ClearCommand(pl, ("clear",)))
        self.register_command_class(EvalCommand(pl, ("eval",)))
        self.register_command_class(DingDongCommand(pl, ("ding",)))
        self.register_command_class(FakeMicrophoneCommand(pl, ("mc",)))
        self.register_command_class(AuthorCommand(pl, ("author",)))

        self.register_command_class(HelpCommand(pl, self.commands, ("help",)))

    def get_commands(self):
        return self.commands

    def register_command_class(self, command):
        self.commands.append(command)

    def parse_arguments(self, input_str):

        try:
            if self.last_command:
                self.last_command.on_control_end()
                self.last_command = None
            input_list = input_str.split()

            prefix = input_list[0].lower()
            for command in self.commands:

                if prefix in command.getNames():

                    self.last_command = command
                    args = input_list[1:]

                    def run():
                        try:
                            threading.current_thread().setName("CONSOLE")
                            command.execute(args)
                            return
                        except Exception as e:
                            print("".join(traceback.TracebackException.from_exception(e).format()))
                            # print(Style.BRIGHT + Fore.RED + str(e))
                            return
                    self.pl.executor.submit(run)
                    return
            else:
                print(Style.BRIGHT + Fore.RED + "Command not found\nUse 'help' for help")
        except IndexError:
            print(Style.BRIGHT + Fore.RED + "command not found")
