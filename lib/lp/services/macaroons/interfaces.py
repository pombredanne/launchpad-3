# Copyright 2016-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface to a policy for issuing and verifying macaroons."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BadMacaroonContext',
    'IMacaroonIssuer',
    ]

from zope.interface import Interface
from zope.schema import Bool


class BadMacaroonContext(Exception):
    """The requested context is unsuitable."""

    def __init__(self, context, message=None):
        if message is None:
            message = "Cannot handle context %r." % context
        super(BadMacaroonContext, self).__init__(message)
        self.context = context


class IMacaroonIssuerPublic(Interface):
    """Public interface to a policy for verifying macaroons."""

    issuable_via_authserver = Bool(
        "Does this issuer allow issuing macaroons via the authserver?")

    def verifyMacaroon(macaroon, context, require_context=True, errors=None,
                       **kwargs):
        """Verify that `macaroon` is valid for `context`.

        :param macaroon: A `Macaroon`.
        :param context: The context to check.
        :param require_context: If True (the default), fail verification if
            the context is None.  If False and the context is None, only
            verify that the macaroon could be valid for some context.  Use
            this in the authentication part of an
            authentication/authorisation API.
        :param errors: If non-None, any verification error messages will be
            appended to this list.
        :param kwargs: Additional arguments that issuers may require to
            verify a macaroon.
        :return: True if `macaroon` is valid for `context`, otherwise False.
        """


class IMacaroonIssuer(IMacaroonIssuerPublic):
    """Interface to a policy for issuing and verifying macaroons."""

    def issueMacaroon(context, **kwargs):
        """Issue a macaroon for `context`.

        :param context: The context that the returned macaroon should relate
            to.
        :param kwargs: Additional arguments that issuers may require to
            issue a macaroon.
        :raises BadMacaroonContext: if the context is unsuitable.
        :return: A macaroon.
        """
