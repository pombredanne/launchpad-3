# Copyright 2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type
__all__ = ('IPOSelection', )

class IPOSelection(Interface):
    """The selection of a translation in a PO file (published) or in Rosetta
    (active)."""

    pomsgset = Attribute("The PO message set for which is this sighting.")
    pluralform = Attribute("The # of pluralform that we are sighting.")
    activesubmission = Attribute("The submission that made this active.")
    publishedsubmission = Attribute("The submission where this was "
        "published in the public pofile for the first time.")
