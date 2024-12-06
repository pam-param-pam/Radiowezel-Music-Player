from Fun.ArgumentException import IncorrectArgument


def requireExactly(param: int, args: list):
    if len(args) != param:
        raise IncorrectArgument(f"Incorrect number of arguments. Expected {str(param)} but got {str(len(args))}")

def requireAtLeast(param: int, args: list):
    if len(args) < param:
        raise IncorrectArgument(f"Incorrect number of arguments. Expected at least {str(param)} but got {str(len(args))}")


def requireNoMoreThan(param: int, args: list):
    if len(args) > param:
        raise IncorrectArgument(f"Incorrect number of arguments. Expected no more than {str(param)} but got {str(len(args))}")

def parseBool(arg):
    if arg == "0" or arg.lower() == "false":
        return False
    elif arg == "1" or arg.lower() == "true":
        return True
    else:
        raise ValueError

def getTypes(types: list, args: list):
    """This function does not enforce args size, if there are not enough arguments supplied, it will simply be ignored."""
    new_args = []
    for index, arg_type in enumerate(types):
        try:
            old_arg = args[index]
            if arg_type == bool:
                new_arg = parseBool(old_arg)
            else:
                new_arg = arg_type(old_arg)
            new_args.append(new_arg)
        except ValueError:
            raise IncorrectArgument(f"Incorrect type of argument at position {index}. Expected {arg_type.__name__} but got '{str(args[index])}'")
        except IndexError:
            pass
    return new_args

