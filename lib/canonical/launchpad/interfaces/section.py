# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Section interfaces."""

__metaclass__ = type

__all__ = [
    'ISection',
    ]

from zope.interface import Interface, Attribute

class ISection(Interface):
    id = Attribute("The ID")
    name = Attribute("The Section Name")

