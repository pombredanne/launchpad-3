# Copyright 2008 Canonical Ltd.  All rights reserved.
# Pylint doesn't grok zope interfaces.
# pylint: disable-msg=E0211,E0213

"""Interfaces for utility classes that operate on Zope fields."""

__metaclass__ = type
__all__ = [
    'IFieldMarshaller',
    ]

from zope.interface import Interface, Attribute


class IFieldMarshaller(Interface):
    """A mapper between schema fields and their representation on the wire."""

    represention_name = Attribute(
        'The name to use for this field within the representation.')

    def marshall_from_json(value):
        """Transform the given data value into an object.

        This is used in PATCH/PUT requests when modifying the field, to get
        the actual value to use from the data submitted via JSON.

        :param value: A value obtained by deserializing a string into
            a JSON data structure.
        """

    def marshall_from_request(value):
        """Return the value to use based on the request submitted value.

        This is used by operation where the data comes from either the
        query string or the POST data.
        :param value: The value submitted as part of the request.
        """

    def unmarshall(entry, field_name, value):
        """Transform an object value into a value suitable for JSON.

        :param entry: The entry whose field this is.
        :value: The object value of the field.

        :return: The string value to give when representing the field
                 in a JSON hash.
        """
