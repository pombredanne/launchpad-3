# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface to a policy for issuing and verifying macaroons."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IMacaroonIssuer',
    ]

from zope.interface import Interface


class IMacaroonIssuerPublic(Interface):
    """Public interface to a policy for verifying macaroons."""

    def checkMacaroonIssuer(macaroon):
        """Check that `macaroon` was issued by this issuer.

        This does not verify that the macaroon is valid for a given context,
        only that it could be valid for some context.  Use this in the
        authentication part of an authentication/authorisation API.
        """

    def verifyMacaroon(macaroon, context):
        """Verify that `macaroon` is valid for `context`.

        :param macaroon: A `Macaroon`.
        :param context: The context to check.
        :return: True if `macaroon` is valid for `context`, otherwise False.
        """


class IMacaroonIssuer(IMacaroonIssuerPublic):
    """Interface to a policy for issuing and verifying macaroons."""

    def issueMacaroon(context):
        """Issue a macaroon for `context`.

        :param context: The context that the returned macaroon should relate
            to.
        :return: A macaroon.
        """
