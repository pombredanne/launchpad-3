import readline
import rlcompleter
import sys

import bzrlib.errors

from devscripts.ec2test.builtins import cmd_demo, cmd_test, cmd_update_image
from devscripts.ec2test.controller import (
    CommandRegistry, HelpTopicRegistry, CommandExecutionMixin)

# Shut up pyflakes.
rlcompleter

readline.parse_and_bind('tab: complete')

class EC2CommandController(CommandRegistry, HelpTopicRegistry,
                           CommandExecutionMixin):
    pass

def main():
    controller = EC2CommandController()
    controller.install_bzrlib_hooks()
    controller.register_command('test', cmd_test)
    controller.register_command('demo', cmd_demo)
    controller.register_command('update-image', cmd_update_image)

    if len(sys.argv) < 2:
        command_names = controller._commands.iterkeys()
        sys.exit(
            "You must supply a command, one of: %s."
            % ', '.join(sorted(command_names)))
    try:
        controller.run(sys.argv[1:])
    except bzrlib.errors.BzrCommandError, e:
        sys.exit('ec2: ERROR: ' + str(e))
