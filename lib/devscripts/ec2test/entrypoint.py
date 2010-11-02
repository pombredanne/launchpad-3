# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The entry point for the 'ec2' utility."""

__metaclass__ = type
__all__ = [
    'main',
    ]

import readline
import rlcompleter
import sys

import bzrlib
from bzrlib.errors import BzrCommandError

from devscripts.ec2test import builtins
from devscripts.ec2test.controller import (
    CommandRegistry, CommandExecutionMixin)

# Shut up pyflakes.
rlcompleter

readline.parse_and_bind('tab: complete')

class EC2CommandController(CommandRegistry, CommandExecutionMixin):
    """The 'ec2' utility registers and executes commands."""


def main():
    """The entry point for the 'ec2' script.

    We run the specified command, or give help if none was specified.
    """
    with bzrlib.initialize():
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
