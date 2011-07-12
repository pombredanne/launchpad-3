# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Archive uploader utilities."""

__metaclass__ = type

__all__ = [
    'DpkgSourceError',
    'extract_dpkg_source',
    're_taint_free',
    're_isadeb',
    're_issource',
    're_is_component_orig_tar_ext',
    're_no_epoch',
    're_no_revision',
    're_valid_version',
    're_valid_pkg_name',
    're_changes_file_name',
    're_extract_src_version',
    'get_source_file_extension',
    'determine_binary_file_type',
    'determine_source_file_type',
    'prefix_multi_line_string',
    'safe_fix_maintainer',
    'ParseMaintError',
    ]


import email.Header
import re
import signal
import subprocess

from lp.services.encoding import (
    ascii_smash,
    guess as guess_encoding,
    )
from lp.soyuz.enums import BinaryPackageFileType


class DpkgSourceError(Exception):

    _fmt = "Unable to unpack source package (%(result)s): %(output)s"

    def __init__(self, command, output, result):
        super(DpkgSourceError, self).__init__(
            self._fmt % {
                "output": output, "result": result, "command": command})
        self.output = output
        self.result = result
        self.command = command


re_taint_free = re.compile(r"^[-+~/\.\w]+$")

re_isadeb = re.compile(r"(.+?)_(.+?)_(.+)\.(u?d?deb)$")

source_file_exts = [
    'orig(?:-.+)?\.tar\.(?:gz|bz2|xz)', 'diff.gz',
    '(?:debian\.)?tar\.(?:gz|bz2|xz)', 'dsc']
re_issource = re.compile(
    r"([^_]+)_(.+?)\.(%s)" % "|".join(ext for ext in source_file_exts))
re_is_component_orig_tar_ext = re.compile(r"^orig-(.+).tar.(?:gz|bz2|xz)$")
re_is_orig_tar_ext = re.compile(r"^orig.tar.(?:gz|bz2|xz)$")
re_is_debian_tar_ext = re.compile(r"^debian.tar.(?:gz|bz2|xz)$")
re_is_native_tar_ext = re.compile(r"^tar.(?:gz|bz2|xz)$")

re_no_epoch = re.compile(r"^\d+\:")
re_no_revision = re.compile(r"-[^-]+$")

re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+~:]+$")
re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")
re_changes_file_name = re.compile(r"([^_]+)_([^_]+)_([^\.]+).changes")
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

re_parse_maintainer = re.compile(r"^\s*(\S.*\S)\s*\<([^\>]+)\>")


def get_source_file_extension(filename):
    """Get the extension part of a source file name."""
    match = re_issource.match(filename)
    if match is None:
        return None
    return match.group(3)


def determine_source_file_type(filename):
    """Determine the SourcePackageFileType of the given filename."""
    # Avoid circular imports.
    from lp.registry.interfaces.sourcepackage import SourcePackageFileType

    extension = get_source_file_extension(filename)
    if extension is None:
        return None
    elif extension == "dsc":
        return SourcePackageFileType.DSC
    elif extension == "diff.gz":
        return SourcePackageFileType.DIFF
    elif re_is_orig_tar_ext.match(extension):
        return SourcePackageFileType.ORIG_TARBALL
    elif re_is_component_orig_tar_ext.match(extension):
        return SourcePackageFileType.COMPONENT_ORIG_TARBALL
    elif re_is_debian_tar_ext.match(extension):
        return SourcePackageFileType.DEBIAN_TARBALL
    elif re_is_native_tar_ext.match(extension):
        return SourcePackageFileType.NATIVE_TARBALL
    else:
        return None


def determine_binary_file_type(filename):
    """Determine the BinaryPackageFileType of the given filename."""
    if filename.endswith(".deb"):
        return BinaryPackageFileType.DEB
    elif filename.endswith(".udeb"):
        return BinaryPackageFileType.UDEB
    elif filename.endswith(".ddeb"):
        return BinaryPackageFileType.DDEB
    else:
        return None


def prefix_multi_line_string(str, prefix, include_blank_lines=0):
    """Utility function to split an input string and prefix,

    Each line with a token or tag. Can be used for quoting text etc.
    """
    out = ""
    for line in str.split('\n'):
        line = line.strip()
        if line or include_blank_lines:
            out += "%s%s\n" % (prefix, line)
    # Strip trailing new line
    if out:
        out = out[:-1]
    return out


def extract_component_from_section(section, default_component="main"):
    component = ""
    if section.find("/") != -1:
        component, section = section.split("/")
    else:
        component = default_component

    return (section, component)


def force_to_utf8(s):
    """Forces a string to UTF-8.

    If the string isn't already UTF-8, it's assumed to be ISO-8859-1.
    """
    try:
        unicode(s, 'utf-8')
        return s
    except UnicodeError:
        latin1_s = unicode(s, 'iso8859-1')
        return latin1_s.encode('utf-8')


def rfc2047_encode(s):
    """Encodes a (header) string per RFC2047 if necessary.

    If the string is neither ASCII nor UTF-8, it's assumed to be ISO-8859-1.
    """
    if not s:
        return ''
    try:
        s.decode('us-ascii')
        #encodings.ascii.Codec().decode(s)
        return s
    except UnicodeError:
        pass
    try:
        s.decode('utf8')
        #encodings.utf_8.Codec().decode(s)
        h = email.Header.Header(s, 'utf-8', 998)
        return str(h)
    except UnicodeError:
        h = email.Header.Header(s, 'iso-8859-1', 998)
        return str(h)


class ParseMaintError(Exception):
    """Exception raised for errors in parsing a maintainer field.

    Attributes:
       message -- explanation of the error
    """

    def __init__(self, message):
        Exception.__init__(self)
        self.args = (message, )
        self.message = message


def fix_maintainer(maintainer, field_name="Maintainer"):
    """Parses a Maintainer or Changed-By field and returns:

    (1) an RFC822 compatible version,
    (2) an RFC2047 compatible version,
    (3) the name
    (4) the email

    The name is forced to UTF-8 for both (1) and (3).  If the name field
    contains '.' or ',', (1) and (2) are switched to 'email (name)' format.
    """
    maintainer = maintainer.strip()
    if not maintainer:
        return ('', '', '', '')

    if maintainer.find("<") == -1:
        email = maintainer
        name = ""
    elif (maintainer[0] == "<" and maintainer[-1:] == ">"):
        email = maintainer[1:-1]
        name = ""
    else:
        m = re_parse_maintainer.match(maintainer)
        if not m:
            raise ParseMaintError(
                "%s: doesn't parse as a valid %s field."
                % (maintainer, field_name))
        name = m.group(1)
        email = m.group(2)
        # Just in case the maintainer ended up with nested angles; check...
        while email.startswith("<"):
            email = email[1:]

    # Get an RFC2047 compliant version of the name
    rfc2047_name = rfc2047_encode(name)

    # Force the name to be UTF-8
    name = force_to_utf8(name)

    # If the maintainer's name contains a full stop then the whole field will
    # not work directly as an email address due to a misfeature in the syntax
    # specified in RFC822; see Debian policy 5.6.2 (Maintainer field syntax)
    # for details.
    if name.find(',') != -1 or name.find('.') != -1:
        rfc822_maint = "%s (%s)" % (email, name)
        rfc2047_maint = "%s (%s)" % (email, rfc2047_name)
    else:
        rfc822_maint = "%s <%s>" % (name, email)
        rfc2047_maint = "%s <%s>" % (rfc2047_name, email)

    if email.find("@") == -1 and email.find("buildd_") != 0:
        raise ParseMaintError(
            "%s: no @ found in email address part." % maintainer)

    return (rfc822_maint, rfc2047_maint, name, email)


def safe_fix_maintainer(content, fieldname):
    """Wrapper for fix_maintainer() to handle unicode and string argument.

    It verifies the content type and transform it in a unicode with guess()
    before call ascii_smash(). Then we can safely call fix_maintainer().
    """
    if type(content) != unicode:
        content = guess_encoding(content)

    content = ascii_smash(content)

    return fix_maintainer(content, fieldname)


def extract_dpkg_source(dsc_filepath, target):
    """Extract a source package by dsc file path.

    :param dsc_filepath: Path of the DSC file
    :param target: Target directory
    """

    def subprocess_setup():
        # Python installs a SIGPIPE handler by default. This is usually not
        # what non-Python subprocesses expect.
        # http://www.chiark.greenend.org.uk/ucgi/~cjwatson/ \
        #   blosxom/2009-07-02-python-sigpipe.html
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = ["dpkg-source", "-sn", "-x", dsc_filepath]
    dpkg_source = subprocess.Popen(
        args, stdout=subprocess.PIPE, cwd=target, stderr=subprocess.PIPE,
        preexec_fn=subprocess_setup)
    output, unused = dpkg_source.communicate()
    result = dpkg_source.wait()
    if result != 0:
        dpkg_output = prefix_multi_line_string(output, "  ")
        raise DpkgSourceError(result=result, output=dpkg_output, command=args)
