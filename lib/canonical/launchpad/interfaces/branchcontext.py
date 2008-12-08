# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'IBranchContext',
    ]

from zope.interface import Interface, Attribute


class IBranchContext(Interface):

    name = Attribute("The name of the context.")
