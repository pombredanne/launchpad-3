# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utility classes for parsing Debian tag files."""

__all__ = [
    'TagFile',
    'TagStanza',
    'TagFileParseError',
    'parse_tagfile',
    'parse_tagfile_content'
    ]


import apt_pkg
import re
import tempfile

from lp.services.mail.signedmessage import strip_pgp_signature


class TagFile(object):
    """Provide an iterable interface to the apt_pkg.TagFile object"""

    def __init__(self, f):
        """Initialise apt_pkg and parse the tagfile provided by f"""
        if not isinstance(f, file):
            raise ValueError()
        apt_pkg.init()
        self.stanzas = apt_pkg.ParseTagFile(f)

    def __iter__(self):
        """Iterate across the stanzas in the tagfile"""
        self.stanzas.Jump(0)
        yield TagStanza(self.stanzas.Section)
        while self.stanzas.Step():
            yield TagStanza(self.stanzas.Section)

    def __getitem__(self, item):
        """Implement the [] operator"""
        self.stanzas.Jump(item)
        return TagStanza(self.stanzas.Section)

class TagStanza(object):
    """Provide an iterable interface to apt_pkg.TagStanza"""

    def __init__(self, stanza):
        """Initialise given a stanza (usually from TagFile.__iter__)"""
        self.stanza = stanza

    def __getitem__(self, item):
        """The [] operator"""
        return self.stanza[item]

    def __iter__(self):
        """Iterate across keys"""
        for k in self.stanza.keys():
            yield k

    def keys(self):
        """Expose the .keys() method"""
        return self.stanza.keys()

    def has_key(self, key):
        """Expose a dicty has_key"""
        return key in self.stanza.keys()

    # Enables (foo in bar) functionality.
    __contains__ = has_key

    def items(self):
        """Allows for k,v in foo.items()"""
        return [ (k, self.stanza[k]) for k in self.stanza.keys() ]

class TagFileParseError(Exception):
    """This exception is raised if parse_changes encounters nastiness"""
    pass

re_single_line_field = re.compile(r"^(\S*)\s*:\s*(.*)")
re_multi_line_field = re.compile(r"^(\s.*)")


def parse_tagfile_content(content, filename=None):
    """Parses a tag file and returns a dictionary where each field is a key.

    The mandatory first argument is the contents of the tag file as a
    string.
    """

    with tempfile.TemporaryFile() as f:
        f.write(content)
        f.seek(0)
        stanzas = list(apt_pkg.ParseTagFile(f))
    if len(stanzas) != 1:
        raise TagFileParseError(
            "%s: multiple stanzas where only one is expected" % filename)

    [stanza] = stanzas

    # We can't do this sensibly with dict() or update(), as it has some
    # keys without values.
    trimmed_dict = {}
    for key in stanza.keys():
        try:
            trimmed_dict[key] = stanza[key]
        except KeyError:
            pass
    return trimmed_dict


def parse_tagfile(filename):
    """Parses a tag file and returns a dictionary where each field is a key.

    The mandatory first argument is the filename of the tag file, and
    the contents of that file is passed on to parse_tagfile_content.

    This will also strip any OpenPGP cleartext signature that is present
    before handing the data over.
    """
    changes_in = open(filename, "r")
    content = strip_pgp_signature(changes_in.read())
    changes_in.close()
    if not content:
        raise TagFileParseError("%s: empty file" % filename)
    return parse_tagfile_content(content, filename=filename)
