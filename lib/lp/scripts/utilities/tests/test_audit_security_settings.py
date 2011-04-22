
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests the security.cfg auditor."""

__metaclass__ = type

import os

from canonical.testing.layers import BaseLayer
from lp.scripts.utilities.settingsauditor import SettingsAuditor
from lp.testing import TestCase


class TestAuditSecuitySettings(TestCase):

    layer = BaseLayer

    def test_duplicate_parsing(self):
        test_settings = """
            [good]
            public.foo = SELECT
            public.bar = SELECT, INSERT
            public.baz = SELECT

            [bad]
            public.foo = SELECT
            public.bar = SELECT, INSERT
            public.bar = SELECT
            public.baz = SELECT
            """.split('\n')
        sa = SettingsAuditor()
        sa.audit(test_settings)
        expected = '[bad]\n\tDuplicate setting found: public.bar'
        self.assertTrue(expected in sa.error_data)
