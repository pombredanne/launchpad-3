# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions to build PO templates on the build slave."""

from __future__ import with_statement

__metaclass__ = type
__all__ = [
    'check_potfiles_in',
    'generate_pot',
    'generate_pots',
    'get_translation_domain',
    'find_intltool_dirs',
    'find_potfiles_in',
    ]

from contextlib import contextmanager
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


def _try_substitution(path, substitution):
    """Try to find a substitution in the given config file.

    :returns: The completed substitution or None if none was found.
    """
    subst_value = ConfigFile(path).getVariable(substitution.name)
    if subst_value is None:
        # No substitution found.
        return None
    return substitution.replace(subst_value)


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
            # Skip non-existent files.
            continue
        if substitution is None:
            value = ConfigFile(path).getVariable(varname)
            if value is not None:
                # Check if the value need a substitution.
                substitution = Substitution.get(value)
                if substitution is not None:
                    # Try to substitute with value from current file but
                    # avoid recursion.
                    if substitution.name != varname:
                        value = _try_substitution(path, substitution)
                    else:
                        # The value has not been found yet but is now stored
                        # in the Substitution instance.
                        value = None
        else:
            value = _try_substitution(path, substitution)
        if value is not None:
            # A value has been found.
            break
    if substitution is not None and not substitution.replaced:
        # Substitution failed.
        return None
    return value


@contextmanager
def chdir(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


def generate_pot(podir, domain):
    """Generate one PO template using intltool.

    :param podir: The PO directory in which to build template.
    :param domain: The translation domain to use as the name of the template.
      If it is None or empty, 'messages.pot' will be used.
    :return: True if generation succeeded.
    """
    if domain is None or domain.strip() == "":
        domain = "messages"
    with chdir(podir):
        with open("/dev/null", "w") as devnull:
            returncode = call(
                ["/usr/bin/intltool-update", "-p", "-g", domain],
                stdout=devnull, stderr=devnull)
    return returncode == 0


def generate_pots(package_dir='.'):
    """Top-level function to generate all PO templates in a package."""
    potpaths = []
    with chdir(package_dir):
        for podir in find_intltool_dirs():
            domain = get_translation_domain(podir)
            if generate_pot(podir, domain):
                potpaths.append(os.path.join(podir, domain + ".pot"))
    return potpaths


class ConfigFile(object):
    """Represent a config file and return variables defined in it."""

    def __init__(self, file_or_name):
        if isinstance(file_or_name, basestring):
            conf_file = file(file_or_name)
        else:
            conf_file = file_or_name
        self.content = conf_file.read()

    def getVariable(self, name):
        """Search the file for a variable definition with this name."""
        pattern = re.compile("^%s[ \t]*=[ \t]*([^\s]*)" % re.escape(name), re.M)
        result = pattern.search(self.content)
        if result is None:
            return None
        else:
            return result.group(1)

    def getFunctionParams(self, function_name):
        """Search file for a function call with this name, return parameters.
        """
        return []


class Substitution(object):
    """Find and replace substitutions.

    Variable texts may contain other variables which should be substituted
    for their value. These are either marked by surrounding @ signs (autoconf
    style) or preceded by a $ sign with optional () (make style).

    This class identifies a single such substitution in a variable text and
    extract the name of the variable who's value is to be inserted. It also
    facilitates the actual replacement so that caller does not have to worry
    about the substitution style that is being used.
    """

    autoconf_pattern = re.compile("@([^@]+)@")
    makefile_pattern = re.compile("\$\(?([^\s\)]+)\)?")

    @staticmethod
    def get(variabletext):
        """Factory method.

        Creates a Substitution instance and checks if it found a substitution.

        :param variabletext: A variable value with possible substitution.
        :returns: A Substitution object or None if no substitution was found.
        """
        subst = Substitution(variabletext)
        if subst.name is not None:
            return subst
        return None

    def _searchForPatterns(self):
        """Search for all the available patterns in variable text."""
        result = self.autoconf_pattern.search(self.text)
        if result is None:
            result = self.makefile_pattern.search(self.text)
        return result

    def __init__(self, variabletext):
        """Extract substitution name from variable text."""
        self.text = variabletext
        self.replaced = False
        result = self._searchForPatterns()
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
