import optparse


class UserError(Exception):
    pass


class OptionParser(optparse.OptionParser):

    UNSPECIFIED = object()

    def add_option(self, *args, **kwargs):
        """Add an option, with the default that it not be included."""
        kwargs['default'] = kwargs.get('default', self.UNSPECIFIED)
        optparse.OptionParser.add_option(self, *args, **kwargs)

    def parse_args_dict(self, cmd_args):
        """Return a dict of specified options.

        Unspecified options with no explicit default are not included in the
        dict."""
        options, args = self.parse_args(cmd_args)
        option_dict = dict(
            item for item in options.__dict__.items()
            if item[1] is not self.UNSPECIFIED)
        return args, option_dict


class Command:
    """Base class for subcommands."""

    commands = {}

    @classmethod
    def parse_args(cls, args):
        if len(args) != 0:
            raise UserError('Too many arguments.')
        return {}

    @classmethod
    def run_from_args(cls, cmd_args):
        args, kwargs = cls.get_parser().parse_args_dict(cmd_args)
        kwargs.update(cls.parse_args(args))
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
