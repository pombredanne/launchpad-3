# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions to build PO templates on the build slave."""

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
    """Check if the files listed in the POTFILES.in file exist.

    Running 'intltool-update -m' will perform this check and also take a
    possible POTFILES.skip into account. It stores details about 'missing'
    (files that should be in POTFILES.in) and 'notexist'ing files (files
    that are listed in POTFILES.in but don't exist) in files which are
    named accordingly. These files are removed before the run.

    We don't care about files missing from POTFILES.in but want to know if
    all listed files exist. The presence of the 'notexist' file tells us
    that.

    :param path: The directory where POTFILES.in resides.
    :returns: False if the directory does not exist, if an error occurred
        when executing intltool-update or if files are missing from
        POTFILES.in. True if all went fine and all files in POTFILES.in
        actually exist.  
    """
    current_path = os.getcwd()

    try:
        os.chdir(path)
    except OSError, e:
        # Abort nicely if the directory does not exist.
        if e.errno == errno.ENOENT:
            return False
        raise
    try:
        # Remove stale files from a previous run of intltool-update -m.
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
        # An error occurred when executing intltool-update.
        return False

    notexist = os.path.join(path, "notexist")
    return not os.access(notexist, os.R_OK)


def find_intltool_dirs():
    """Search for directories with intltool structure.

    The current directory and its subdiretories are searched. An 'intltool
    structure' is a directory that contains a POFILES.in file and where all
    files listed in that POTFILES.in do actually exist. The latter
    condition makes sure that the file is not stale.

    :returns: A list of directory names.
    """
    return sorted(filter(check_potfiles_in, find_potfiles_in()))


def _get_AC_PACKAGE_NAME(config_file):
    """Get the value of AC_PACKAGE_NAME from function parameters.

    The value of AC_PACKAGE_NAME is either the first or the fourth
    parameter of the AC_INIT call if it is called with at least two
    parameters.
    """
    params = config_file.getFunctionParams("AC_INIT")
    if params is None or len(params) < 2:
        return None
    if len(params) < 4:
        return params[0]
    else:
        return params[3]


def _try_substitution(config_files, varname, substitution):
    """Try to find a substitution in the config files.

    :returns: The completed substitution or None if none was found.
    """
    subst_value = None
    if varname == substitution.name:
        # Do not look for the same name in the current file.
        config_files = config_files[:-1]
    for config_file in reversed(config_files):
        subst_value = config_file.getVariable(substitution.name)
        if subst_value is not None:
            # Substitution found.
            break
    else:
        # No substitution found.
        return None
    return substitution.replace(subst_value)


def get_translation_domain(dirname):
    """Get the translation domain for this PO directory.

    Imitates some of the behavior of intltool-update to find out which
    translation domain the build environment provides. The domain is usually
    defined in the GETTEXT_PACKAGE variable in one of the build files. Another
    variant is DOMAIN in the Makevars file. This function goes through the
    ordered list of these possible locations, top to bottom, and tries to
    find a valid value. Since the same variable name may be defined in
    multiple files (usually configure.ac and Makefile.in.in), it needs to
    keep trying with the next file, until it finds the most specific
    definition.

    If the found value contains a substitution, either autoconf style (@...@)
    or make style ($(...)), the search is continued in the same file and back
    up the list of files, now searching for the substitution. Multiple
    substitutions or multi-level substitutions are not supported.
    """
    locations = [
        ('../configure.ac', 'GETTEXT_PACKAGE', True),
        ('../configure.in', 'GETTEXT_PACKAGE', True),
        ('Makefile.in.in', 'GETTEXT_PACKAGE', False),
        ('Makevars', 'DOMAIN', False),
    ]
    value = None
    substitution = None
    config_files = []
    for filename, varname, keep_trying in locations:
        path = os.path.join(dirname, filename)
        if not os.access(path, os.R_OK):
            # Skip non-existent files.
            continue
        config_files.append(ConfigFile(path))
        new_value = config_files[-1].getVariable(varname)
        if new_value is not None:
            value = new_value
            if value == "AC_PACKAGE_NAME":
                value = _get_AC_PACKAGE_NAME(config_files[-1])
            else:
                # Check if the value needs a substitution.
                substitution = Substitution.get(value)
                if substitution is not None:
                    # Try to substitute with value.
                    value = _try_substitution(
                        config_files, varname, substitution)
                    if value is None:
                        # No substitution found; the setup is broken.
                        break
        if value is not None and not keep_trying:
            # A value has been found.
            break
    return value


@contextmanager
def chdir(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


def generate_pot(podir, domain):
    """Generate one PO template using intltool.

    Although 'intltool-update -p' can try to find out the translation domain
    we trust our own code more on this one and simply specify the domain.
    Also, the man page for 'intltool-update' states that the '-g' option
    "has an additional effect: the name of current working directory is no
    more  limited  to 'po' or 'po-*'." We don't want that limit either.

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

    def _stripQuotes(self, identifier):
        """Strip surrounding quotes from `identifier`, if present.

        :param identifier: a string, possibly surrounded by matching
            'single,' "double," or [bracket] quotes.
        :return: `identifier` but with the outer pair of matching quotes
            removed, if they were there.
        """
        if len(identifier) < 2:
            return identifier

        quote_pairs = [
            ('"', '"'),
            ("'", "'"),
            ("[", "]"),
            ]
        for (left, right) in quote_pairs:
            if identifier.startswith(left) and identifier.endswith(right):
                return identifier[1:-1]

        return identifier

    def getVariable(self, name):
        """Search the file for a variable definition with this name."""
        pattern = re.compile(
            "^%s[ \t]*=[ \t]*([^\s]*)" % re.escape(name), re.M)
        result = pattern.search(self.content)
        if result is None:
            return None
        return self._stripQuotes(result.group(1))

    def getFunctionParams(self, name):
        """Search file for a function call with this name, return parameters.
        """
        pattern = re.compile("^%s\(([^)]*)\)" % re.escape(name), re.M)
        result = pattern.search(self.content)
        if result is None:
            return None
        else:
            return [
                self._stripQuotes(param.strip())
                for param in result.group(1).split(',')
                ]


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
