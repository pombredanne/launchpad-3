# (c) Canonical Software Ltd. 2004, all rights reserved.
#

import apt_pkg, re

__all__ = [
    'TagFile', 'TagStanza', 'TagFileParseError',
    'parse_tagfile', 'parse_tagfile_lines']

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

    """Enables (foo in bar) functionality"""
    __contains__ = has_key

    def items(self):
        """Allows for k,v in foo.items()"""
        return [ (k,self.stanza[k]) for k in self.stanza.keys() ]

class TagFileParseError(Exception):
    """This exception is raised if parse_changes encounters nastiness"""
    pass

re_single_line_field = re.compile(r"^(\S*)\s*:\s*(.*)");
re_multi_line_field = re.compile(r"^\s(.*)");


def parse_tagfile_lines(lines, dsc_whitespace_rules=0, allow_unsigned=False,
                        filename=None):
    """Parses a tag file and returns a dictionary where each field is a key.

    The mandatory first argument is the contents of the tag file as a
    list of lines.

    dsc_whitespace_rules is an optional boolean argument which defaults
    to off.  If true, it turns on strict format checking to avoid
    allowing in source packages which are unextracable by the
    inappropriately fragile dpkg-source.

    The rules are:

    o The PGP header consists of '-----BEGIN PGP SIGNED MESSAGE-----'
      followed by any PGP header data and must end with a blank line.

    o The data section must end with a blank line and must be followed by
      '-----BEGIN PGP SIGNATURE-----'.
    """
    error = ""
    changes = {}

    # Reindex by line number so we can easily verify the format of
    # .dsc files...
    index = 0
    indexed_lines = {}
    for line in lines:
        index += 1
        indexed_lines[index] = line[:-1]

    inside_signature = 0

    num_of_lines = len(indexed_lines.keys())
    index = 0
    first = -1
    while index < num_of_lines:
        index += 1
        line = indexed_lines[index]

        # If the line is empty and we're not strictly enforcing whitespace
        # rules, then just continue.
        # If we're enforcing the rules, then check those rules, and maybe
        # complain.
        if line == "":
            if dsc_whitespace_rules:
                index += 1
                if index > num_of_lines:
                    raise TagFileParseError("%s: invalid .dsc file at line %d" % (filename, index))
                line = indexed_lines[index]
                if not line.startswith("-----BEGIN PGP SIGNATURE"):
                    raise TagFileParseError("%s: invalid .dsc file at line %d -- "
                        "expected PGP signature; got '%s'" % (filename, index,line))
                inside_signature = 0
                break
            else:
                continue
        if line.startswith("-----BEGIN PGP SIGNATURE"):
            break

        # If we're at the start of a signed section, then consume the signature
        # information, and remember that we're inside the signed data.
        if line.startswith("-----BEGIN PGP SIGNED MESSAGE"):
            inside_signature = 1
            if dsc_whitespace_rules:
                while index < num_of_lines and line != "":
                    index += 1
                    line = indexed_lines[index]
            continue
        # If we're not inside the signed data, don't process anything, unless
        # we've decided to allow unsigned files.
        if not (inside_signature or allow_unsigned):
            continue
        slf = re_single_line_field.match(line)
        if slf:
            field = slf.groups()[0].lower()
            changes[field] = slf.groups()[1]
            first = 1
            continue
        if line == " .":
            changes[field] += '\n'
            continue
        mlf = re_multi_line_field.match(line)
        if mlf:
            if first == -1:
                raise TagFileParseError("%s: could not parse .changes file "
                "line %d: '%s'\n [Multi-line field continuing on from nothing?]"
                % (filename, index,line))
            if first == 1 and changes[field] != "":
                changes[field] += '\n'
            first = 0
            changes[field] += mlf.groups()[0] + '\n'
            continue
        error += line

    if dsc_whitespace_rules and inside_signature:
        raise TagFileParseError("%s: invalid .dsc format at line %d" % (filename, index))

    changes["filecontents"] = "".join(lines)

    if error:
        raise TagFileParseError("%s: unable to parse .changes file: %s" % (filename, error))

    return changes


def parse_tagfile(filename, dsc_whitespace_rules=0, allow_unsigned=False):
    """Parses a tag file and returns a dictionary where each field is a key.

    The mandatory first argument is the filename of the tag file, and
    the contents of that file is passed on to parse_tagfile_lines.

    See parse_tagfile_lines's docstring for description of the
    dsc_whitespace_rules and allow_unsigned arguments.
    """
    changes_in = open(filename, "r")
    lines = changes_in.readlines()
    changes_in.close()
    if not lines:
        raise TagFileParseError( "%s: empty file" % filename )
    return parse_tagfile_lines(
        lines, dsc_whitespace_rules=dsc_whitespace_rules,
        allow_unsigned=allow_unsigned, filename=filename)

