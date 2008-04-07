# Copyright 2008 Canonical Ltd.  All rights reserved.
# Pylint doesn't grok zope interfaces.
# pylint: disable-msg=E0211,E0213

"""Interfaces for utility classes that operate on Zope fields."""

__metaclass__ = type
__all__ = [
    'IFieldDeserializer',
]

from zope.interface import Interface

class IFieldDeserializer(Interface):
    """A class capable of turning a value for a field into an object."""

    def __init__(field, request):
        """Initialize with a field and a request."""

    def deserialize(value):
        """Transform the given value into an object."""
