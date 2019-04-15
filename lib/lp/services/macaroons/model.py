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
from lp.services.scripts import log


class MacaroonIssuerBase:
    """See `IMacaroonIssuer`."""

    issuable_via_authserver = False

    # A mapping of caveat names to "checker" callables that verify the
    # corresponding caveat text.  The signature of each checker is
    # (caveat_value, context, **kwargs) -> bool, where caveat_value is the
    # text of the caveat with the caveat name removed, context is the
    # issuer-specific context to check, and kwargs is any other keyword
    # arguments that were given to verifyMacaroon; it should return True if
    # the caveat is allowed, otherwise False.
    #
    # The context passed in may be None, in which case the checker may
    # choose to only verify that the caveat could be valid for some context,
    # or may simply return False if this is unsupported.  This is useful for
    # issuers that support APIs with separate authentication and
    # authorisation phases.
    #
    # The "primary context caveat" added to all macaroons issued by this
    # base class does not need to be listed here; it is handled by the
    # verifyContextCaveat method.
    checkers = {}

    # Caveat names in this set may appear more than once (in which case they
    # have the usual subtractive semantics, so the union of all the
    # constraints they express applies).  Any other caveats may only appear
    # once.
    allow_multiple = set()

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

    def checkIssuingContext(self, context):
        """Check that the issuing context is suitable.

        Concrete implementations may implement this method to check that the
        context of a macaroon issuance is suitable.  The returned
        context is passed to individual caveat checkers, and may be the same
        context that was passed in or an adapted one.

        :param context: The context to check.
        :raises ValueError: if the context is unsuitable.
        :return: The context to pass to individual caveat checkers.
        """
        return context

    def issueMacaroon(self, context):
        """See `IMacaroonIssuer`."""
        context = self.checkIssuingContext(context)
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname,
            identifier=self.identifier, key=self._root_secret)
        macaroon.add_first_party_caveat(
            "%s %s" % (self.primary_caveat_name, context))
        return macaroon

    def checkVerificationContext(self, context, **kwargs):
        """Check that the verification context is suitable.

        Concrete implementations may implement this method to check that the
        context of a macaroon verification is suitable.  The returned
        context is passed to individual caveat checkers, and may be the same
        context that was passed in or an adapted one.

        :param context: The context to check.
        :param kwargs: Additional arguments that issuers may require to
            verify a macaroon.
        :raises ValueError: if the context is unsuitable.
        :return: The context to pass to individual caveat checkers.
        """
        return context

    def verifyPrimaryCaveat(self, caveat_value, context, **kwargs):
        """Verify the primary context caveat on one of this issuer's macaroons.

        :param caveat_value: The text of the caveat with the caveat name
            removed.
        :param context: The context to check.
        :param kwargs: Additional arguments that issuers may require to
            verify a macaroon.
        :return: True if this caveat is allowed, otherwise False.
        """
        raise NotImplementedError

    def verifyMacaroon(self, macaroon, context, require_context=True,
                       **kwargs):
        """See `IMacaroonIssuer`."""
        if macaroon.location != config.vhost.mainsite.hostname:
            log.info("Macaroon has unknown location '%s'." % macaroon.location)
            return False
        if require_context and context is None:
            log.info("Expected macaroon verification context but got None.")
            return False
        if context is not None:
            try:
                context = self.checkVerificationContext(context)
            except ValueError as e:
                log.info(str(e))
                return False
        seen = set()

        # XXX cjwatson 2019-04-11: Once we're on Python 3, we should use
        # "nonlocal" instead of this hack.
        class VerificationState:
            logged_caveat_error = False

        state = VerificationState()

        def verify(caveat):
            try:
                caveat_name, caveat_value = caveat.split(" ", 1)
            except ValueError:
                log.info("Cannot parse caveat '%s'." % caveat)
                state.logged_caveat_error = True
                return False
            if caveat_name not in self.allow_multiple and caveat_name in seen:
                log.info(
                    "Multiple '%s' caveats are not allowed." % caveat_name)
                state.logged_caveat_error = True
                return False
            seen.add(caveat_name)
            if caveat_name == self.primary_caveat_name:
                checker = self.verifyPrimaryCaveat
            else:
                checker = self.checkers.get(caveat_name)
                if checker is None:
                    log.info("Unhandled caveat name '%s'." % caveat_name)
                    state.logged_caveat_error = True
                    return False
            if not checker(caveat_value, context, **kwargs):
                log.info("Caveat check for '%s' failed." % caveat)
                state.logged_caveat_error = True
                return False
            return True

        try:
            verifier = Verifier()
            verifier.satisfy_general(verify)
            return verifier.verify(macaroon, self._root_secret)
        except MacaroonVerificationFailedException as e:
            if not state.logged_caveat_error:
                log.info(str(e))
            return False
        except Exception:
            log.exception("Unhandled exception while verifying macaroon.")
            return False
