# Copyright 2008 Canonical Ltd.  All rights reserved.
# Pylint doesn't grok zope interfaces.
# pylint: disable-msg=E0211,E0213

"""Interfaces for utility classes that operate on Zope fields."""

__metaclass__ = type
__all__ = [
    'IFieldMarshaller',
    ]

from zope.interface import Interface


class IFieldMarshaller(Interface):
    """A class capable of turning a value for a field into an object."""

    def marshall(value):
        """Transform the given value into an object."""

    def unmarshall(context, field_name, value):
        """Transform an object into a representation name and string value."""
