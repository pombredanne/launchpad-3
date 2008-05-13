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

    def unmarshall(entry, field_name, value):
        """Transform an value into a representation name and string value.

        :param context: The entry whose field this is.
        :param field_name: The name of the field within the entry.
        :value: The object value of the field.

        :return: A 2-tuple (representation_name, string_value).
        'representation_name' is the name to use as a key in a
        JSON hash, and 'string_value' is the value to associate with that
        key.
"""
