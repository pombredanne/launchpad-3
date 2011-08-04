import inspect
from optparse import OptionParser


class UserError(Exception):
    pass


def add_dict(name, **kwargs):
    def decorator(func):
        setattr(func, name, kwargs)
        return func
    return decorator


def types(**kwargs):
    return add_dict('_types', **kwargs)

def helps(**kwargs):
    return add_dict('_helps', **kwargs)



def get_function_parser(function):
    parser = OptionParser()
    args, ignore, ignored, defaults = inspect.getargspec(function)
    for arg in args:
        arg_type = function._types.get(arg)
        if arg_type is None:
            continue
        arg_help = getattr(function, '_helps', {}).get(arg)
        if arg_help is not None:
            arg_help +=' Default: %default.'
        parser.add_option('--%s' % arg, type=arg_type, help=arg_help)
    if defaults is not None:
        defaults_dict = dict(zip(args, defaults))
        option_defaults = dict(
            (key, value) for key, value in defaults_dict.items()
            if parser.defaults.get(key, '') is None)
        parser.set_defaults(**option_defaults)
    return parser


class Command:
    """Base class for subcommands."""

    commands = {}

    @classmethod
    def parse_args(cls, command, args):
        if len(args) != 0:
            raise UserError('Too many arguments.')
        return {}

    @classmethod
    def run_from_args(cls, command, cmd_args):
        parser = get_function_parser(command)
        options, args = parser.parse_args(cmd_args)
        kwargs = cls.parse_args(command, args)
        kwargs.update(options.__dict__)
        command(**kwargs)

    @classmethod
    def run_subcommand(cls, argv):
        if len(argv) < 1:
            raise UserError('Must supply a command: %s.' %
                            ', '.join(cls.commands.keys()))
        try:
            command = cls.commands[argv[0]]
        except KeyError:
            raise UserError('%s invalid.  Valid commands: %s.' %
                            (argv[0], ', '.join(cls.commands.keys())))
        cls.run_from_args(command, argv[1:])
