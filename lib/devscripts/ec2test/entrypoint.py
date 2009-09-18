import readline
import rlcompleter
import sys

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

    args = sys.argv[1:]
    if not args:
        args = ['help']
    try:
        controller.run(args)
    except BzrCommandError, e:
        sys.exit('ec2: ERROR: ' + str(e))
