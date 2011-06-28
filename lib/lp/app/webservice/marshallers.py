# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad-specific field marshallers for the web service."""

__metaclass__ = type

__all__ = [
    'TextFieldMarshaller',
    ]

from lazr.restful.marshallers import (
    TextFieldMarhaller as LazrTextFieldMarshaller,
    )


class TextFieldMarhaller(LazrTextFieldMarshaller):
    """Do not expose email addresses for anonymous users."""

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`.

        Return the value as is.
        """
        return value
