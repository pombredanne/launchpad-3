# This file is incuded almost verbatim from commandant,
# https://launchpad.net/commandant.  The only changes are removing some code
# we don't use that depends on other parts of commandant.  When Launchpad is
# on Python 2.5 we can include commandant as an egg.


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

import os
import sys

from bzrlib.commands import run_bzr, Command


class CommandRegistry(object):

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
            for cmd in self._commands.itervalues():
                if name in cmd.aliases:
                    local_command = cmd()
                    break
            else:
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

    def load_module(self, module):
        """Load C{bzrlib.commands.Command}s and L{HelpTopic}s from C{module}.

        Objects found in the module with names that start with C{cmd_} are
        treated as C{bzrlib.commands.Command}s and objects with names that
        start with C{topic_} are treated as L{HelpTopic}s.
        """
        for name in module.__dict__:
            if name.startswith("cmd_"):
                sanitized_name = name[4:].replace("_", "-")
                self.register_command(sanitized_name, module.__dict__[name])
            elif name.startswith("topic_"):
                sanitized_name = name[6:].replace("_", "-")
                self.register_help_topic(sanitized_name, module.__dict__[name])


class HelpTopicRegistry(object):

    def __init__(self):
        self._help_topics = {}

    def register_help_topic(self, name, help_topic_class):
        """Register a C{bzrlib.commands.Command} to this controller.

        @param name: The name to register the command with.
        @param command_class: A type object, typically a subclass of
            C{bzrlib.commands.Command} to use when the command is invoked.
        """
        self._help_topics[name] = help_topic_class

    def get_help_topic_names(self):
        """Get a C{set} of help topic names."""
        return set(self._help_topics.iterkeys())

    def get_help_topic(self, name):
        """
        Get the help topic matching C{name} or C{None} if a match isn't found.
        """
        try:
            help_topic = self._help_topics[name]()
        except KeyError:
            return None
        help_topic.controller = self
        return help_topic



class CommandExecutionMixin(object):

    def run(self, argv):
        """Run the C{bzrlib.commands.Command} specified in C{argv}.

        @raise BzrCommandError: Raised if a matching command can't be found.
        """
        run_bzr(argv)



def import_module(filename, file_path, package_path):
    """Import a module and make it a child of C{commandant_command}.

    The module source in C{filename} at C{file_path} is copied to a temporary
    directory, a Python package called C{commandant_command}.

    @param filename: The name of the module file.
    @param file_path: The path to the module file.
    @param package_path: The path for the new C{commandant_command} package.
    @return: The new module.
    """
    module_path = os.path.join(package_path, "commandant_command")
    if not os.path.exists(module_path):
        os.mkdir(module_path)

    init_path = os.path.join(module_path, "__init__.py")
    open(init_path, "w").close()

    source_code = open(file_path, "r").read()
    module_file_path = os.path.join(module_path, filename)
    module_file = open(module_file_path, "w")
    module_file.write(source_code)
    module_file.close()

    name = filename[:-3]
    sys.path.append(package_path)
    try:
        return __import__("commandant_command.%s" % (name,), fromlist=[name])
    finally:
        sys.path.pop()
