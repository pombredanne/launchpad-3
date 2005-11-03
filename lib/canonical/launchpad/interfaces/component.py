# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Component interfaces."""

__metaclass__ = type

__all__ = [
    'IComponent',
    ]

from zope.interface import Interface, Attribute

class IComponent(Interface):
    id = Attribute("The ID")
    name = Attribute("The Component Name")

