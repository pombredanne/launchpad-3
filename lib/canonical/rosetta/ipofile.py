from zope.interface import Interface, Attribute
from zope.interface.common.mapping import IMapping

class IPOMessage(Interface):
    """Represents a logic set of msgid/msgstr items that refer to a same message"""
    msgid = Attribute(
        "The msgid of the message (as an unicode).")
    msgidPlural = Attribute(
        "The plural msgid of the message (as an unicode), if present.")
    msgstr = Attribute(
        "The msgstr of the message (as an unicode).")
    msgstrPlurals = Attribute(
        "The msgstr's of the message, if more than one (as a list of unicodes).")
    commentText = Attribute(
        "The human-written comments ('# foo') of the message (as an unicode).")
    sourceComment = Attribute(
        "The parser-generated comments ('#. foo') of the message (as an unicode).")
    fileReferences = Attribute(
        "The references ('#: foo') of the message (as an unicode).")
    flags = Attribute(
        "The flags of the message (a Set of strings).")
    obsolete = Attribute(
        """True if this message is obsolete (#~ msgid "foo"\\n#~ msgstr "bar").""")
    nplurals = Attribute(
        """The number of plural forms for this language, as used in this file.
        None means the header does not have a Plural-Forms entry.""")
    pluralExpr = Attribute(
        """The expression used to get a plural form from a number.""")

    def flagsText(flags=None):
        """The flags of the message, as an unicode; or, if a sequence
        or set is passed in, pretend these are the messages flags and
        return an unicode representing them"""

class IPOHeader(IMapping):
    """Represents a PO header; items from the header can be fetched using the
    Mapping interface."""

    def finish():
        """If the IPOHeader instance implements the IPOMessage interface,
        you can call finish() to parse the msgstr and fill in the fields
        from there.  You should probably no longer modify the msgstr after
        that."""

    messages = Attribute(
        "A reference to the sequence of IPOMessages this header refers to")

class IPOParser(Interface):
    def write(string):
        """Parse string as a PO file fragment."""

    def finish():
        """Indicate that the PO data has come to an end.
        Throws an exception if the parser was in the
        middle of a message. (Can also throw normal syntax
        exceptions as it parses anything that was pending)."""

    messages = Attribute(
        """The messages parsed by the parser. Only valid
        after finish() has been called.""")
    header = Attribute(
        "A reference to the IPOHeader object for this POFile.")
