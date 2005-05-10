# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOTranslation', )

class IPOTranslation(Interface):
    """A translation in a PO file."""

    translation = Attribute("A translation string.")
