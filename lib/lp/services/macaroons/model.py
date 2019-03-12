# Copyright 2016-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Policies for issuing and verifying macaroons."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "MacaroonIssuerBase",
    ]

from pymacaroons import (
    Macaroon,
    Verifier,
    )

from lp.services.config import config


class MacaroonIssuerBase:
    """See `IMacaroonIssuer`."""

    @property
    def identifier(self):
        """An identifying name for this issuer."""
        raise NotImplementedError

    @property
    def prefix(self):
        """Prefix for caveats issued by this issuer."""
        return "lp.%s " % self.identifier

    @property
    def _root_secret(self):
        secret = config.launchpad.internal_macaroon_secret_key
        if not secret:
            raise RuntimeError(
                "launchpad.internal_macaroon_secret_key not configured.")
        return secret

    def issueMacaroon(self, context):
        """See `IMacaroonIssuer`.

        Concrete implementations should normally wrap this with some
        additional checks of and/or changes to the context.
        """
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname,
            identifier=self.identifier, key=self._root_secret)
        macaroon.add_first_party_caveat(self.prefix + str(context))
        return macaroon

    def checkMacaroonIssuer(self, macaroon):
        """See `IMacaroonIssuer`."""
        if macaroon.location != config.vhost.mainsite.hostname:
            return False
        try:
            verifier = Verifier()
            verifier.satisfy_general(
                lambda caveat: caveat.startswith(self.prefix))
            return verifier.verify(macaroon, self._root_secret)
        except Exception:
            return False

    def verifyCaveat(self, caveat_text, context):
        """Verify the sole caveat on macaroons issued by this issuer.

        :param caveat_text: The text of the caveat, with this issuer's
            prefix removed.
        :param context: The context to check.
        :return: True if this caveat is allowed, otherwise False.
        """
        # We will need to change this interface if we ever support macaroons
        # with more than one caveat or macaroons that are issued to users,
        # but this is good enough for internal use.  Any unrecognised
        # caveats will fail closed.
        raise NotImplementedError

    def verifyMacaroon(self, macaroon, context):
        """See `IMacaroonIssuer`.

        Concrete implementations should normally wrap this with some
        additional checks of the context, and must implement `verifyCaveat`.
        """
        if not self.checkMacaroonIssuer(macaroon):
            return False

        def verify(caveat):
            prefix = self.prefix
            if not caveat.startswith(prefix):
                return False
            return self.verifyCaveat(caveat[len(prefix):], context)

        try:
            verifier = Verifier()
            verifier.satisfy_general(verify)
            return verifier.verify(macaroon, self._root_secret)
        except Exception:
            return False
