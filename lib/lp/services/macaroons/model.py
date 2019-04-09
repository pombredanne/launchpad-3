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
    def primary_caveat_name(self):
        """The name of the primary context caveat issued by this issuer."""
        return "lp.%s" % self.identifier

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
        macaroon.add_first_party_caveat(
            "%s %s" % (self.primary_caveat_name, context))
        return macaroon

    def checkMacaroonIssuer(self, macaroon):
        """See `IMacaroonIssuer`."""
        if macaroon.location != config.vhost.mainsite.hostname:
            return False
        try:
            verifier = Verifier()
            verifier.satisfy_general(
                lambda caveat: caveat.startswith(
                    self.primary_caveat_name + " "))
            return verifier.verify(macaroon, self._root_secret)
        except Exception:
            return False

    def verifyPrimaryCaveat(self, caveat_value, context):
        """Verify the primary context caveat on one of this issuer's macaroons.

        :param caveat_value: The text of the caveat, with this issuer's
            prefix removed.
        :param context: The context to check.
        :return: True if this caveat is allowed, otherwise False.
        """
        raise NotImplementedError

    def verifyMacaroon(self, macaroon, context):
        """See `IMacaroonIssuer`.

        Concrete implementations should normally wrap this with some
        additional checks of the context, and must implement
        `verifyPrimaryCaveat`.
        """
        if not self.checkMacaroonIssuer(macaroon):
            return False

        def verify(caveat):
            try:
                caveat_name, caveat_value = caveat.split(" ", 1)
            except ValueError:
                return False
            if caveat_name == self.primary_caveat_name:
                checker = self.verifyPrimaryCaveat
            else:
                # XXX cjwatson 2019-04-09: For now we just fail closed if
                # there are any other caveats, which is good enough for
                # internal use.
                return False
            return checker(caveat_value, context)

        try:
            verifier = Verifier()
            verifier.satisfy_general(verify)
            return verifier.verify(macaroon, self._root_secret)
        except Exception:
            return False
