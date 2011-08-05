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
    """Generate an OptionParser for a function.

    Defaults come from the parameter defaults.
    For every permitted to provide as an option, the type must be specified,
    using the types decorator.
    Help may be specified using the helps decorator.
    """
    parser = OptionParser()
    args, ignore, ignored, defaults = inspect.getargspec(function)
    if defaults is not None:
        defaults_dict = dict(zip(args, defaults))
    else:
        defaults_dict = {}
    arg_types = getattr(function, '_types', {})
    for arg in args:
        arg_type = arg_types.get(arg)
        if arg_type is None:
            arg_type = defaults_dict.get(arg)
            if arg_type is None:
                continue
            arg_type = type(arg_type)
        arg_help = getattr(function, '_helps', {}).get(arg)
        if arg_help is not None:
            arg_help += ' Default: %default.'
        parser.add_option('--%s' % arg, type=arg_type, help=arg_help)
    option_defaults = dict(
        (key, value) for key, value in defaults_dict.items()
        if parser.defaults.get(key, '') is None)
    parser.set_defaults(**option_defaults)
    return parser


def parse_args(command, args):
    """Return the positional arguments as a dict."""
    # TODO: implement!
    if len(args) != 0:
        raise UserError('Too many arguments.')
    return {}


def run_from_args(command, cmd_args):
    """Run a command function using the specified commandline arguments."""
    parser = get_function_parser(command)
    options, args = parser.parse_args(cmd_args)
    kwargs = parse_args(command, args)
    kwargs.update(options.__dict__)
    command(**kwargs)


def run_subcommand(subcommands, argv):
    """Run a subcommand as specified by argv."""
    if len(argv) < 1:
        raise UserError('Must supply a command: %s.' %
                        ', '.join(subcommands.keys()))
    try:
        command = subcommands[argv[0]]
    except KeyError:
        raise UserError('%s invalid.  Valid commands: %s.' %
                        (argv[0], ', '.join(subcommands.keys())))
    run_from_args(command, argv[1:])
