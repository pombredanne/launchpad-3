# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Archive uploader utilities."""

__metaclass__ = type

__all__ = [
    're_taint_free',
    're_isadeb',
    're_issource',
    're_no_epoch',
    're_no_revision',
    're_valid_version',
    're_valid_pkg_name',
    're_changes_file_name',
    're_extract_src_version',
    'prefix_multi_line_string',
    'safe_fix_maintainer',
    'ParseMaintError',
    ]


import email.Header
import re

from canonical.archiveuploader.tagfiles import TagFileParseError
from canonical.encoding import guess as guess_encoding, ascii_smash


re_taint_free = re.compile(r"^[-+~/\.\w]+$")

re_isadeb = re.compile(r"(.+?)_(.+?)_(.+)\.(u?deb)$")
re_issource = re.compile(r"(.+)_(.+?)\.(orig\.tar\.gz|diff\.gz|tar\.gz|dsc)$")

re_no_epoch = re.compile(r"^\d+\:")
re_no_revision = re.compile(r"-[^-]+$")

re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+~:]+$")
re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")
re_changes_file_name = re.compile(r"([^_]+)_([^_]+)_([^\.]+).changes")
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

re_parse_maintainer = re.compile(r"^\s*(\S.*\S)\s*\<([^\>]+)\>");


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


def extract_component_from_section(section, default_component = "main"):
    component = ""
    if section.find("/") != -1:
        component, section = section.split("/")
    else:
        component = default_component

    return (section,component)


def build_file_list(tagfile, is_dsc = False, default_component = "main" ):
    files = {}

    if "files" not in tagfile:
        raise ValueError("No Files section in supplied tagfile")

    format = tagfile["format"]

    format = float(format)

    if not is_dsc and (format < 1.5 or format > 2.0):
        raise ValueError("Unsupported format '%s'" % tagfile["format"])

    for line in tagfile["files"].split("\n"):
        if not line:
            break

        tokens = line.split()

        section = priority = ""

        try:
            if is_dsc:
                (md5, size, name) = tokens
            else:
                (md5, size, section, priority, name) = tokens
        except ValueError:
            raise TagFileParseError(line)

        if section == "":
            section = "-"
        if priority == "":
            priority = "-"

        (section, component) = extract_component_from_section(
            section, default_component)

        files[name] = {
            "md5sum": md5,
            "size": size,
            "section": section,
            "priority": priority,
            "component": component
            }

    return files


def force_to_utf8(s):
    """Forces a string to UTF-8.

    If the string isn't already UTF-8, it's assumed to be ISO-8859-1.
    """
    try:
        unicode(s, 'utf-8')
        return s
    except UnicodeError:
        latin1_s = unicode(s,'iso8859-1')
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
        self.args = message,;
        self.message = message;


def fix_maintainer (maintainer, field_name = "Maintainer" ):
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
    before call ascii_smash(). Then we can safelly call fix_maintainer().
    """
    if type(content) != unicode:
        content = guess_encoding(content)

    content = ascii_smash(content)

    return fix_maintainer(content, fieldname)

