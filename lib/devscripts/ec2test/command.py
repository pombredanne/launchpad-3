#!/usr/bin/python
# Commandant is a framework for building command-oriented tools.
# Copyright (C) 2009 Jamshed Kakar.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Infrastructure to run C{bzrlib.commands.Command}s and L{HelpTopic}s."""

import sys

from bzrlib.commands import run_bzr, Command


class CommandController(object):
    """C{bzrlib.commands.Command} discovery and execution controller.

    A L{CommandController} is a container for named
    C{bzrlib.commands.Command}s. The L{register_command} method registers
    C{bzrlib.commands.Command}s with the controller.

    A controller is an execution engine for commands.  The L{run} method
    accepts command line arguments, finds a matching command, and runs it.
    """

    def __init__(self):
        self._commands = {}

    def install_bzrlib_hooks(self):
        """
        Register this controller with C{Command.hooks} so that the controller
        can take advantage of Bazaar's command infrastructure.

        L{_list_commands} and L{_get_command} are registered as callbacks for
        the C{list_commands} and C{get_commands} hooks, respectively.
        """
        Command.hooks.install_named_hook(
            "list_commands", self._list_commands, "commandant commands")
        Command.hooks.install_named_hook(
            "get_command", self._get_command, "commandant commands")

    def _list_commands(self, names):
        """Hook to find C{bzrlib.commands.Command} names is called by C{bzrlib}.

        @param names: A set of C{bzrlib.commands.Command} names to update with
            names from this controller.
        """
        names.update(self._commands.iterkeys())
        return names

    def _get_command(self, command, name):
        """
        Hook to get the C{bzrlib.commands.Command} for C{name} is called by
        C{bzrlib}.

        @param command: A C{bzrlib.commands.Command}, or C{None}, to be
            returned if a command matching C{name} can't be found.
        @param name: The name of the C{bzrlib.commands.Command} to retrieve.
        @return: The C{bzrlib.commands.Command} from the index or C{command}
            if one isn't available for C{name}.
        """
        try:
            local_command = self._commands[name]()
        except KeyError:
            return command
        local_command.controller = self
        return local_command

    def register_command(self, name, command_class):
        """Register a C{bzrlib.commands.Command} with this controller.

        @param name: The name to register the command with.
        @param command_class: A type object, typically a subclass of
            C{bzrlib.commands.Command} to use when the command is invoked.
        """
        self._commands[name] = command_class

    def run(self, argv):
        """Run the C{bzrlib.commands.Command} specified in C{argv}.

        @raise BzrCommandError: Raised if a matching command can't be found.
        """
        run_bzr(argv)

