import readline
import rlcompleter
import sys

from bzrlib.builtins import cmd_help
from bzrlib.errors import BzrCommandError

from devscripts.ec2test import builtins
from devscripts.ec2test.controller import (
    CommandRegistry, CommandExecutionMixin)

# Shut up pyflakes.
rlcompleter

readline.parse_and_bind('tab: complete')

class EC2CommandController(CommandRegistry, CommandExecutionMixin):
    def __init__(self):
        CommandRegistry.__init__(self)


def main():
    controller = EC2CommandController()
    controller.install_bzrlib_hooks()
    controller.load_module(builtins)

    if len(sys.argv) < 2:
        command_names = controller._commands.iterkeys()
        sys.exit(
            "You must supply a command, one of: %s."
            % ', '.join(sorted(command_names)))
    try:
        controller.run(sys.argv[1:])
    except BzrCommandError, e:
        sys.exit('ec2: ERROR: ' + str(e))
