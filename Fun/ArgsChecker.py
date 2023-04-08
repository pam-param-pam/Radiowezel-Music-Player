from Fun.ArgumentException import IncorrectArgument


def requireExactly(param, args):
    if len(args) != param:
        raise IncorrectArgument("Incorrect number of arguments. Expected " + str(param) + " but got " + str(len(args)))


def requireAtLeast(param, args):
    if len(args) < param:
        raise IncorrectArgument("Incorrect number of arguments. Expected at least " + str(param) + " but got " + str(len(args)))


def requireNoMoreThan(param, args):
    if len(args) > param:
        raise IncorrectArgument("Incorrect number of arguments. Expected no more than " + str(param) + " but got " + str(len(args)))