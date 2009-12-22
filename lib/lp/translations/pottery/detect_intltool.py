#! /usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions to detect if intltool can be used to generate a POT file for the
package in the current directory."""

__metaclass__ = type
__all__ = [
    'find_potfiles_in',
    'check_potfiles_in',
    'find_intltool_dirs',
    ]

import errno
import os
import os.path
import re
from subprocess import Popen, PIPE

POTFILES_in = "POTFILES.in"


def run_shell_command(cmd, env=None, input_data=None, raise_on_error=False):
    """Run a shell command and return the output and status."""
    stdin = None
    if input_data:
        stdin = PIPE
    if env:
        os.environ.update(env)
        env = os.environ
    pipe = Popen(cmd, shell=True, env=env, stdin=stdin, stdout=PIPE, stderr=PIPE)
    if input_data:
        try:
            pipe.stdin.write(input_data)
        except IOError, e:
            if e.errno != errno.EPIPE:
                raise
    (output, errout) = pipe.communicate()
    status = pipe.returncode
    if raise_on_error and status != STATUS_OK:
        raise OSError(status, errout)

    return (status, output, errout)


def find_potfiles_in():
    """ Search the current directory and its subdirectories for POTFILES.in.

    :returns: A list of names of directories that contain a file POTFILES.in.
    """
    result_dirs = []
    for dirpath, dirnames, dirfiles in os.walk("."):
        if POTFILES_in in dirfiles:
            result_dirs.append(dirpath)
    return result_dirs


def check_potfiles_in(path):
    """Check if the files listed in the POTFILES.in file exist."""
    command = ("cd \"%(dir)s\" && rm -f missing notexist && "
               "intltool-update -m" % { "dir" : path, })
    (status, output, errs) = run_shell_command(command)

    if status != 0:
        return False

    notexist = os.path.join(path, "notexist")
    return not os.access(notexist, os.R_OK)


def find_intltool_dirs():
    """Search the current directory and its subdiretories for intltool
    structure.
    """
    return filter(check_potfiles_in, find_potfiles_in())


substitution_pattern = re.compile("@([^@]+)@")

def get_substitution(variabletext):
    """Get possible substitution from a variable test."""
    result = substitution_pattern.search(variabletext)
    if result is not None:
        return result.group(1)
    return None


def get_translation_domain(dirname):
    """Determine the translation domain by parsing various files.

    Goes through a list of file names and possible variable names to find
    the translation domains. If the found value contains a substitution, it
    continues to search for the substitution to return a completed value.
    """
    locations = [
        ('Makefile.in.in', 'GETTEXT_PACKAGE'),
        ('../configure.ac', 'GETTEXT_PACKAGE'),
        ('../configure.in', 'GETTEXT_PACKAGE'),
        ('Makevars', 'DOMAIN'),
    ]
    value = None
    substitution = None
    for filename, varname in locations:
        path = os.path.join(dirname, filename)
        if not os.access(path, os.R_OK):
            continue
        if value is None:
            value = ConfigFile(path).getVariable(varname)
            if value is None:
                # No value found, try next file.
                continue
            substitution = get_substitution(value)
            if substitution is None:
                # The value has been found, no substitution needed.
                break
            if substitution == varname:
                # Do not search the current file for the substitution because
                # the name is identical and we'd get a recursion.
                continue
        # This part is only reached if a value has been found but still needs
        # a substitution.
        subst_value = ConfigFile(path).getVariable(substitution)
        if subst_value is not None:
            value = value.replace("@%s@" % substitution, subst_value)
            break
    if get_substitution(value) is not None:
        # Substitution failed.
        return None
    return value


class ConfigFile(object):
    """Represent a config file and return variables defined in it."""

    def __init__(self, file_or_name):
        if isinstance(file_or_name, basestring):
            conf_file = file(file_or_name)
        else:
            conf_file = file_or_name
        self.content_lines = conf_file.readlines()

    def getVariable(self, name):
        """Search the file for a variable definition with this name."""
        pattern = re.compile("^%s[ \t]*=[ \t]*([^ \t\n]*)" % re.escape(name))
        variable = None
        for line in self.content_lines:
            result = pattern.match(line)
            if result is not None:
                variable = result.group(1)
        return variable
