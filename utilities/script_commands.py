import inspect


class UserError(Exception):
    pass


class Command:
    """Base class for subcommands."""

    commands = {}

    @classmethod
    def parse_args(cls, args):
        if len(args) != 0:
            raise UserError('Too many arguments.')
        return {}

    @classmethod
    def set_defaults(cls, parser):
        args, ignored, ignored, defaults = inspect.getargspec(cls.run)
        if defaults is None:
            return
        defaults_dict = dict(zip(args, defaults))
        option_defaults = dict(
            (key, value) for key, value in defaults_dict.items()
            if parser.defaults.get(key, '') is None)
        parser.set_defaults(**option_defaults)

    @classmethod
    def run_from_args(cls, cmd_args):
        parser = cls.get_parser()
        cls.set_defaults(parser)
        options, args = parser.parse_args(cmd_args)
        kwargs = cls.parse_args(args)
        kwargs.update(options.__dict__)
        cls.run(**kwargs)

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
        command.run_from_args(argv[1:])
