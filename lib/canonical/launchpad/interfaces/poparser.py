# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.interface.common.mapping import IMapping

__metaclass__ = type

__all__ = ('IPOMessage', 'IPOHeader', 'IPOParser')

class IPOMessage(Interface):
    """A logical set of msgid/msgstr items that refer to a same message"""
    msgid = Attribute(
        "The msgid of the message (as unicode).")
    msgidPlural = Attribute(
        "The plural msgid of the message (as unicode), if present.")
    msgstr = Attribute(
        "The msgstr of the message (as unicode).")
    msgstrPlurals = Attribute(
        "The msgstr's of the message, if more than one (as a list of unicodes).")
    commentText = Attribute(
        "The human-written comments ('# foo') of the message (as unicode).")
    sourceComment = Attribute(
        "The parser-generated comments ('#. foo') of the message (as unicode).")
    fileReferences = Attribute(
        "The references ('#: foo') of the message (as unicode).")
    flags = Attribute(
        "The flags of the message (a Set of strings).")
    obsolete = Attribute(
        """True if message is obsolete (#~ msgid "foo"\\n#~ msgstr "bar").""")
    nplurals = Attribute(
        """The number of plural forms for this language, as used in this file.
        None means the header does not have a Plural-Forms entry.""")
    pluralExpr = Attribute(
        """The expression used to get a plural form from a number.""")

    def flagsText(flags=None):
        """The flags of the message, as unicode; or, if a sequence
        or set is passed in, pretend these are the messages flags and
        return a unicode representing them"""

class IPOHeader(IMapping):
    """Represents a PO header; items from the header can be fetched using the
    Mapping interface."""

    messages = Attribute(
        "A reference to the sequence of IPOMessages this header refers to")

    def finish():
        """If the IPOHeader instance implements the IPOMessage interface,
        you can call finish() to parse the msgstr and fill in the fields
        from there.  You should probably no longer modify the msgstr after
        that."""

    def getPORevisionDate():
        """Gets the string and datetime object for the PO-Revision-Date entry.

        The function will return a tuple of a string and a datetime object
        representing that string. If the date string is not found in the header
        or the date format is not valid, the datetime object is None and
        the string is set with the error.
        This method is 100% code from Canonical.
        """

    def getPluralFormExpression():
        """Returns the plural form expression, if defined in the header.

        Returns the plural form expression (for instance, "n != 1")
        if present in the header; otherwise, return None. Note that the
        plural-forms header may be incomplete or incorrectly defined;
        the function will return None, and the callsite must handle it.
        """


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
