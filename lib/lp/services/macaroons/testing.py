# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Macaroon testing helpers."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'find_caveats_by_name',
    'MacaroonTestMixin',
    ]

from fixtures import FakeLogger
from testtools.content import text_content


def find_caveats_by_name(macaroon, caveat_name):
    return [
        caveat for caveat in macaroon.caveats
        if caveat.caveat_id.startswith(caveat_name + " ")]


class MacaroonTestMixin:

    def assertMacaroonVerifies(self, issuer, macaroon, context, **kwargs):
        with FakeLogger() as logger:
            try:
                self.assertTrue(issuer.verifyMacaroon(
                    macaroon, context, **kwargs))
            except Exception:
                self.addDetail("log", text_content(logger.output))
                raise

    def assertMacaroonDoesNotVerify(self, expected_log_lines, issuer, macaroon,
                                    context, **kwargs):
        with FakeLogger() as logger:
            self.assertFalse(issuer.verifyMacaroon(
                macaroon, context, **kwargs))
            self.assertEqual(expected_log_lines, logger.output.splitlines())
