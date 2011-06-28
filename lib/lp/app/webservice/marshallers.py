# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad-specific field marshallers for the web service."""

__metaclass__ = type

__all__ = [
    'TextFieldMarshaller',
    ]


from zope.app.security.interfaces import IUnauthenticatedPrincipal

from lazr.restful.marshallers import (
    TextFieldMarshaller as LazrTextFieldMarshaller,
    )


class TextFieldMarshaller(LazrTextFieldMarshaller):
    """Do not expose email addresses for anonymous users."""

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`.

        Return the value as is.
        """
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            return u"<email address hidden>"
        return value
