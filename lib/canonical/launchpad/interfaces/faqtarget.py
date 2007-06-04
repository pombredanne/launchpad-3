# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interface for things that can host IFAQ."""

__metaclass__ = type

__all__ = [
    'IFAQTarget',
    ]


from zope.interface import Interface

class IFAQTarget(Interface):
    """An object that can contain a FAQ document."""

