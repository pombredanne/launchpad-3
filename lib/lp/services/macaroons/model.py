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
from pymacaroons.exceptions import MacaroonVerificationFailedException

from lp.services.config import config
from lp.services.macaroons.interfaces import BadMacaroonContext


class MacaroonIssuerBase:
    """See `IMacaroonIssuer`."""

    issuable_via_authserver = False

    @property
    def identifier(self):
        """An identifying name for this issuer."""
        raise NotImplementedError

    @property
    def _primary_caveat_name(self):
        """The name of the primary context caveat issued by this issuer."""
        return "lp.%s" % self.identifier

    @property
    def _root_secret(self):
        secret = config.launchpad.internal_macaroon_secret_key
        if not secret:
            raise RuntimeError(
                "launchpad.internal_macaroon_secret_key not configured.")
        return secret

    def checkIssuingContext(self, context):
        """Check that the issuing context is suitable.

        Concrete implementations may implement this method to check that the
        context of a macaroon issuance is suitable.  The returned context is
        used to create the primary caveat, and may be the same context that
        was passed in or an adapted one.

        :param context: The context to check.
        :raises BadMacaroonContext: if the context is unsuitable.
        :return: The context to use to create the primary caveat.
        """
        return context

    def issueMacaroon(self, context):
        """See `IMacaroonIssuer`.

        Concrete implementations should normally wrap this with some
        additional checks of and/or changes to the context.
        """
        context = self.checkIssuingContext(context)
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname,
            identifier=self.identifier, key=self._root_secret)
        macaroon.add_first_party_caveat(
            "%s %s" % (self._primary_caveat_name, context))
        return macaroon

    def checkVerificationContext(self, context):
        """Check that the verification context is suitable.

        Concrete implementations may implement this method to check that the
        context of a macaroon verification is suitable.  The returned
        context is passed to individual caveat checkers, and may be the same
        context that was passed in or an adapted one.

        :param context: The context to check.
        :raises BadMacaroonContext: if the context is unsuitable.
        :return: The context to pass to individual caveat checkers.
        """
        return context

    def verifyPrimaryCaveat(self, caveat_value, context):
        """Verify the primary context caveat on one of this issuer's macaroons.

        :param caveat_value: The text of the caveat, with this issuer's
            prefix removed.
        :param context: The context to check.
        :return: True if this caveat is allowed, otherwise False.
        """
        raise NotImplementedError

    def verifyMacaroon(self, macaroon, context, require_context=True,
                       errors=None):
        """See `IMacaroonIssuer`."""
        if macaroon.location != config.vhost.mainsite.hostname:
            if errors is not None:
                errors.append(
                    "Macaroon has unknown location '%s'." % macaroon.location)
            return False
        if require_context and context is None:
            if errors is not None:
                errors.append(
                    "Expected macaroon verification context but got None.")
            return False
        if context is not None:
            try:
                context = self.checkVerificationContext(context)
            except BadMacaroonContext as e:
                if errors is not None:
                    errors.append(str(e))
                return False

        def verify(caveat):
            try:
                caveat_name, caveat_value = caveat.split(" ", 1)
            except ValueError:
                if errors is not None:
                    errors.append("Cannot parse caveat '%s'." % caveat)
                return False
            if caveat_name == self._primary_caveat_name:
                checker = self.verifyPrimaryCaveat
            else:
                # XXX cjwatson 2019-04-09: For now we just fail closed if
                # there are any other caveats, which is good enough for
                # internal use.
                if errors is not None:
                    errors.append("Unhandled caveat name '%s'." % caveat_name)
                return False
            if not checker(caveat_value, context):
                if errors is not None:
                    errors.append("Caveat check for '%s' failed." % caveat)
                return False
            return True

        try:
            verifier = Verifier()
            verifier.satisfy_general(verify)
            return verifier.verify(macaroon, self._root_secret)
        # XXX cjwatson 2019-04-24: This can currently raise a number of
        # other exceptions in the presence of non-well-formed input data,
        # but most of them are too broad to reasonably catch so we let them
        # turn into OOPSes for now.  Revisit this once
        # https://github.com/ecordell/pymacaroons/issues/51 is fixed.
        except MacaroonVerificationFailedException as e:
            if errors is not None and not errors:
                errors.append(str(e))
            return False
