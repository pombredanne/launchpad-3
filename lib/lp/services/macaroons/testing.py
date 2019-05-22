# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Macaroon testing helpers."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'find_caveats_by_name',
    'MacaroonTestMixin',
    ]

from testtools.content import text_content
from testtools.matchers import MatchesStructure


def find_caveats_by_name(macaroon, caveat_name):
    return [
        caveat for caveat in macaroon.caveats
        if caveat.caveat_id.startswith(caveat_name + " ")]


class MacaroonTestMixin:

    def assertMacaroonVerifies(self, issuer, macaroon, context, **kwargs):
        errors = []
        try:
            verified = issuer.verifyMacaroon(
                macaroon, context, errors=errors, **kwargs)
            self.assertIsNotNone(verified)
            self.assertThat(verified, MatchesStructure.byEquality(
                issuer_name=issuer.identifier))
        except Exception:
            if errors:
                self.addDetail("errors", text_content("\n".join(errors)))
            raise

    def assertMacaroonDoesNotVerify(self, expected_errors, issuer, macaroon,
                                    context, **kwargs):
        errors = []
        self.assertIsNone(issuer.verifyMacaroon(
            macaroon, context, errors=errors, **kwargs))
        self.assertEqual(expected_errors, errors)
