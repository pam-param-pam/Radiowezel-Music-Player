import logging
import sys
import time
from reprint import output
from colorama import Fore, Style
import sounddevice as sd
import numpy as np
from Fun.ArgsChecker import requireAtLeast, requireExactly, requireNoMoreThan
from Fun.ArgumentException import IncorrectArgument
from Fun.Command import Command


class AddCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Add a song to the queue"
    longDesc = "Add a song to the queue.\nExample:\n `add song Hero` to add a song called 'Hero'"

    def execute(self, args):
        requireAtLeast(1, args)
        try:
            name = ' '.join(args)
            self.pl.queue.name_add(name)
            print(Style.BRIGHT + Fore.MAGENTA + "Added " + str(self.pl.queue.peek(-1)))
            self.pl.notifyAboutQueueChange()
        except IndexError:
            raise IncorrectArgument("no NAME specified")


class HelpCommand(Command):
    def __init__(self, pl, commands, name):
        super().__init__(name)
        self.commands = commands
        self.pl = pl

    shortDesc = "Displays information about available commands"
    longDesc = "The `help` command displays information about available commands.\n If given an argument, it will display the long description of the specified command.\n Otherwise, it will display a list of available commands and their short descriptions."

    def execute(self, args):
        if len(args) > 0:
            for command in self.commands:
                if args[0] in command.getNames():
                    print(Style.BRIGHT + Fore.LIGHTBLUE_EX + command.getLongDesc())
                    return
            IncorrectArgument("Command not found")
        else:
            print(Style.BRIGHT + Fore.CYAN + "Available commands:")
            for command in self.commands:
                print(Style.BRIGHT + " " + Fore.LIGHTMAGENTA_EX + ', '.join(
                    command.getNames()) + ": " + Fore.LIGHTBLUE_EX + command.getShortDesc())


class InfoCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Get current player state"
    longDesc = "Get current player state. Including current song, its position in seconds and whatever player is stopped or playing."

    def get_state(self):
        state = "Unknown..."
        if self.pl.stopped:
            state = "stopped..."
        if self.pl.force_stopped:
            state = "force stopped"
        if self.pl.VLCPlayer.is_playing():
            state = "Playing..."
        return state

    def execute(self, args):
        requireExactly(0, args)

        with output() as op:
            while self.flag:
                a = "{BRIGHT}{LM}Current song: {LB}{song}".format(
                    song=self.pl.currentSong,
                    BRIGHT=Style.BRIGHT,
                    LM=Fore.LIGHTMAGENTA_EX,
                    LB=Fore.LIGHTBLUE_EX)
                b = "{BRIGHT}{LM}position: {LB}{position}".format(
                    position=self.pl.formatSeconds(
                        round(self.pl.VLCPlayer.get_time() / 1000)) + "/" + self.pl.formatSeconds(
                        round(self.pl.currentSong.length) if self.pl.currentSong is not None else 0),
                    BRIGHT=Style.BRIGHT,
                    LM=Fore.LIGHTMAGENTA_EX,
                    LB=Fore.LIGHTBLUE_EX)

                c = "{BRIGHT}{LM}State: {LB}{state}".format(
                    state=self.get_state(),
                    BRIGHT=Style.BRIGHT,
                    LM=Fore.LIGHTMAGENTA_EX,
                    LB=Fore.LIGHTBLUE_EX)
                op.append(a)
                op.append(b)
                op.append(c)
                sys.stdout.write(u"\u001b[3B")  # Move up

                time.sleep(1)
                sys.stdout.write(u"\u001b[3A")  # Move down

                op.remove(a)
                op.remove(b)
                op.remove(c)
            self.flag = True


class MoveCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Move a song in the queue"
    longDesc = "Move a song in the queue.\n To move a song use its index in the queue and position to move to.\nExample:\n `move 1 2` to move the first song to the second position."

    def execute(self, args):
        requireExactly(2, args)
        try:

            song = str(self.pl.queue.peek(int(args[0]) - 1))
            self.pl.queue.move(int(args[0]) - 1, int(args[1]) - 1)
            print(Style.BRIGHT + Fore.MAGENTA + "Moved " + song + " to " + args[1])
            self.pl.notifyAboutQueueChange()
        except (TypeError, ValueError):
            raise IncorrectArgument("INDEX must be an int")
        except IndexError:
            raise IncorrectArgument("INDEX is not correct")


class NextCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Play next song"
    longDesc = "Play next song from queue.\n If there is no next song, nothing will happen."

    def execute(self, args):
        requireExactly(0, args)
        self.pl.play(True)


class PauseCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Pause a song"
    longDesc = "Pause a song.\n If there is no current song, nothing will happen."

    def execute(self, args):
        requireNoMoreThan(1, args)
        if len(args) > 0 and args[0].lower() in ["-f", "--force"]:
            self.pl.VLCPlayer.set_pause(True)
            self.pl.stopped = True
            print(Style.BRIGHT + Fore.MAGENTA + "Force paused")
        else:
            self.pl.pauseFadeout()


class VolumeCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Get or change volume"
    longDesc = "Get or change volume.\n Example:\n `volume` to get current volume\n 'volume 50' to change volume to 50%."

    def execute(self, args):
        requireAtLeast(0, args)
        try:
            self.pl.set_volume(int(args[0]))
        except (TypeError, ValueError):
            raise IncorrectArgument("VOLUME must be an int")

        except IndexError:
            print(Style.BRIGHT + Fore.MAGENTA + str(self.pl.VLCPlayer.audio_get_volume()))


class SeekCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Seek current song"
    longDesc = "Seek current song.\n Example: 'seek 100' to seek to 100th second in the song(1:40)."

    def execute(self, args):
        requireExactly(1, args)
        try:
            pos = int(args[0])
            self.pl.VLCPlayer.set_time(int(pos * 1000))
            FormattedPos = self.pl.formatSeconds(round(self.pl.VLCPlayer.get_time() / 1000))
            print(Style.BRIGHT + Fore.MAGENTA + "Sought to " + FormattedPos)
        except (TypeError, ValueError):
            raise IncorrectArgument("TIME must be an int")
        except IndexError:
            raise IncorrectArgument("no TIME specified")


class RepeatCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Toggle repeat"
    longDesc = "Change whatever music should play on repeat.\nExample:\n'repeat' to toggle it or 'repeat true' to explicitly set it to true."

    def execute(self, args):
        requireAtLeast(0, args)
        try:
            if args[0] == "0" or args[0].lower() == "false":
                self.pl.repeat = False
            elif args[0] == "1" or args[0].lower() == "true":
                self.pl.repeat = True
            print(Style.BRIGHT + Fore.MAGENTA + "Repeat is now " + str(self.pl.repeat))

        except IndexError:
            self.pl.repeat = not self.pl.repeat
            print(Style.BRIGHT + Fore.MAGENTA + "Repeat is now " + str(self.pl.repeat))


class RemoveCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Remove a song from the queue"
    longDesc = "Remove a song from the queue by its index or name.\nExample:\n `remove 1` to remove the first song\n `remove song Hero` to remove a song called 'Hero'."

    def execute(self, args):
        requireAtLeast(1, args)
        try:
            song = self.pl.queue.peek(int(args[0]) - 1)
            self.pl.queue.remove_by_index(int(args[0]) - 1)
            print(Style.BRIGHT + Fore.MAGENTA + "Removed " + str(song))
        except (TypeError, ValueError):
            name = ' '.join(args)
            self.pl.queue.name_remove(name)
            print(Style.BRIGHT + Fore.MAGENTA + "Removed " + name)
            self.pl.notifyAboutQueueChange()
        except IndexError:
            raise IncorrectArgument("no NAME specified")


class QueueCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Get the current queue"
    longDesc = "Get the current queue. Use -v or --verbose to get more information."

    def execute(self, args):
        requireNoMoreThan(1, args)
        if self.pl.queue.is_empty():
            print(Style.BRIGHT + Fore.RED + "Queue is empty")
            return
        if len(args) > 0 and args[0].lower() in ["-v", "--verbose"]:

            for i, song in enumerate(self.pl.queue.songs):
                print(Style.BRIGHT + Fore.LIGHTRED_EX + str(i + 1) + Fore.WHITE + ">> " + Fore.MAGENTA + str(
                    song) + Fore.WHITE + " by " + Fore.LIGHTBLUE_EX + str(
                    song.author) + Fore.WHITE + "(" + Fore.LIGHTCYAN_EX + str(
                    self.pl.formatSeconds(song.length)) + Fore.WHITE + ") --- " + Fore.LIGHTBLACK_EX + song.id)

        else:
            for i, song in enumerate(self.pl.queue.songs):
                print(Style.BRIGHT + Fore.LIGHTRED_EX + str(i + 1) + Fore.WHITE + ">> " + Fore.MAGENTA + str(song))


class PlayCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Play a song"
    longDesc = "Play a song.\n If there is a current song, it will be resumed else a new one will be played from queue."

    def execute(self, args):
        requireExactly(0, args)
        self.pl.play()


class DebugCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Change debug level"
    longDesc = "Change debug level.\n You can pick from 'debug', 'info', 'warning', 'error' and 'critical'."

    def execute(self, args):
        requireExactly(1, args)
        logger = logging.getLogger('Main')
        if args[0] == 'debug':
            logger.setLevel(logging.DEBUG)
            print(Style.BRIGHT + Fore.WHITE + "Good luck stopping it now LOL")
        elif args[0] == 'info':
            logger.setLevel(logging.INFO)
        elif args[0] == 'warning':
            logger.setLevel(logging.WARNING)
        elif args[0] == 'error':
            logger.setLevel(logging.ERROR)
        elif args[0] == 'critical':
            logger.setLevel(logging.CRITICAL)
        else:
            raise IncorrectArgument("Incorrect debug level")
        print(Style.BRIGHT + Fore.MAGENTA + "Set level to " + Fore.LIGHTRED_EX + args[0].upper())


class SpeedCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Change playback speed"
    longDesc = "Change playback speed.\n Accepts '0.25', '0.5', '1', '1.5' and '2'."

    def execute(self, args):
        requireExactly(1, args)
        try:
            self.pl.set_speed(float(args[0]))
            if args[0] in ("0.5", "0.25", "2", "1.5"):
                print(Style.BRIGHT + Fore.MAGENTA + "Set playback speed to " + Fore.LIGHTRED_EX + args[0])
            else:
                print(Style.BRIGHT + Fore.MAGENTA + "Set playback speed to " + Fore.LIGHTRED_EX + "1")

        except (TypeError, ValueError):
            raise IncorrectArgument("SPEED must be a number")


class DecibelsCommand(Command):

    def __init__(self, pl, name):
        super().__init__(name)
        self.pl = pl

    shortDesc = "Check dB level"
    longDesc = "Check dB level."

    def execute(self, args):
        requireExactly(0, args)

        # Define the sample rate and duration for the audio stream
        sample_rate = 44100
        duration = 5.0

        # Open an audio stream from the default input device
        stream = sd.InputStream(samplerate=sample_rate, channels=1)

        # Start the audio stream
        stream.start()

        # Read audio samples from the stream for the specified duration
        samples = stream.read(int(sample_rate * duration))[0]

        # Stop the audio stream
        stream.stop()

        # Compute the root mean square (RMS) of the audio samples
        rms = np.sqrt(np.mean(np.square(samples)))

        # Convert the RMS value to dBFS (decibels relative to full scale)
        dBFS = 20 * np.log10(rms)

        # Print the dBFS value
        print("dBFS:", dBFS)
