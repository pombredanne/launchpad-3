#! /usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions to detect if intltool can be used to generate a POT file for the
package in the current directory."""

__metaclass__ = type
__all__ = [
    'check_potfiles_in',
    'get_translation_domain',
    'find_intltool_dirs',
    'find_potfiles_in',
    ]

import errno
import os.path
import re
from subprocess import call


def find_potfiles_in():
    """Search the current directory and its subdirectories for POTFILES.in.

    :returns: A list of names of directories that contain a file POTFILES.in.
    """
    result_dirs = []
    for dirpath, dirnames, dirfiles in os.walk("."):
        if "POTFILES.in" in dirfiles:
            result_dirs.append(dirpath)
    return result_dirs


def check_potfiles_in(path):
    """Check if the files listed in the POTFILES.in file exist."""
    current_path = os.getcwd()

    try:
        os.chdir(path)
    except OSError, e:
        # Abort nicely if directory does not exist.
        if e.errno == errno.ENOENT:
            return False
        raise
    try:
        for unlink_name in ['missing', 'notexist']:
            try:
                os.unlink(unlink_name)
            except OSError, e:
                # It's ok if the files are missing.
                if e.errno != errno.ENOENT:
                    raise
        devnull = open("/dev/null", "w")
        returncode = call(
            ["/usr/bin/intltool-update", "-m"],
            stdout=devnull, stderr=devnull)
        devnull.close()
    finally:
        os.chdir(current_path)

    if returncode != 0:
        return False

    notexist = os.path.join(path, "notexist")
    return not os.access(notexist, os.R_OK)


def find_intltool_dirs():
    """Search the current directory and its subdiretories for intltool
    structure.
    """
    return sorted(filter(check_potfiles_in, find_potfiles_in()))


def get_translation_domain(dirname):
    """Get the translation domain for this PO directory.

    Imitates some of the behavior of intltool-update to find out which
    translation domain the build environment provides. The domain is usually
    defined in the GETTEXT_PACKAGE variable in one of the build files. Another
    variant is DOMAIN in the Makevars file. This function goes through the
    ordered list of these possible locations, the order having been copied
    from intltool-update, and tries to find a valid value.

    If the found value contains a substitution, either autoconf style (@...@)
    or make style ($(...)), the search is continued in the same file and down
    the list of files, now searching for the substitution. Multiple
    substitutions or multi-level substitutions are not supported.
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
            substitution = Substitution.get(value)
            if substitution is None:
                # The value has been found, no substitution needed.
                break
            if substitution.name == varname:
                # Do not search the current file for the substitution because
                # the name is identical and we'd get a recursion.
                continue
        # This part is only reached if a value has been found but still needs
        # a substitution.
        subst_value = ConfigFile(path).getVariable(substitution.name)
        if subst_value is not None:
            value = substitution.replace(subst_value)
            break
    if substitution is not None and not substitution.replaced:
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


class Substitution(object):
    """Find and replace substitutions.

    Handles a single substitution per variable text.
    """

    autoconf_pattern = re.compile("@([^@]+)@")
    makefile_pattern = re.compile("\$\(?([^ \t\n\)]+)\)?")

    @staticmethod
    def get(variabletext):
        """Factory method. Check if a substitution is present in the value.

        :param variabletext: A variable value with possible substitution.
        :returns: A Substitution object or None if no substitution was found.
        """
        subst = Substitution(variabletext)
        if subst.name is not None:
            return subst
        return None

    def __init__(self, variabletext):
        """Extract substitution name from variable text."""
        self.text = variabletext
        self.replaced = False
        result = self.autoconf_pattern.search(self.text)
        if result is None:
            result = self.makefile_pattern.search(self.text)
        if result is None:
            self._replacement = None
            self.name = None
        else:
            self._replacement = result.group(0)
            self.name = result.group(1)

    def replace(self, value):
        """Return a copy of the variable text with the substitution resolved.
        """
        self.replaced = True
        return self.text.replace(self._replacement, value)
