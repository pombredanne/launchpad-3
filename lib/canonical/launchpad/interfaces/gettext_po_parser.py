# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = [
    'IPOParser'
    ]


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
