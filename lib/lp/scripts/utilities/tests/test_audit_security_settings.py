
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests the security.cfg auditor."""

__metaclass__ = type

import os

from canonical.config import config
from canonical.testing.layers import BaseLayer
from lp.testing import TestCase


class TestAuditSecuitySettings(TestCase):

    layer = BaseLayer

    def test_duplicate_parsing(self):
        utility = os.path.join(
            config.root, 'utilities', 'audit-security-settings.py')
        cmd = '%s smoketest' % utility
        error_msg = os.popen(cmd).read()
        expected = '[bad]\n\tDuplicate setting found: public.bar\n'
        self.assertTrue(expected in error_msg)
