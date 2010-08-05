# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the cronscript_enabled function in scripts/base.py."""

__metaclass__ = type

from cStringIO import StringIO
from logging import DEBUG
from tempfile import NamedTemporaryFile
from textwrap import dedent
import unittest

from lp.services.scripts.base import cronscript_enabled
from lp.testing import TestCase
from lp.testing.logger import MockLogger


class TestCronscriptEnabled(TestCase):
    def setUp(self):
        super(TestCronscriptEnabled, self).setUp()
        self.log_output = StringIO()
        self.log = MockLogger(self.log_output)
        self.log.setLevel(DEBUG)

    def makeConfig(self, body):
        tempfile = NamedTemporaryFile(suffix='.ini')
        tempfile.write(body)
        tempfile.flush()
        # Ensure a reference is kept until the test is over.
        # tempfile will then clean itself up.
        self.addCleanup(lambda x: None, tempfile)
        return tempfile.name

    def test_noconfig(self):
        """Ensure cronscripts enabled if cronscript.ini exists."""
        enabled = cronscript_enabled('/idontexist.ini', 'foo', self.log)
        self.assertIs(True, enabled)

    def test_emptyconfig(self):
        """Ensure cronscripts are enabled if cronscript.ini is empty."""
        config = self.makeConfig('')
        enabled = cronscript_enabled(config, 'foo', self.log)
        self.assertIs(True, enabled)

    def test_default_true(self):
        config = self.makeConfig(dedent("""\
            [DEFAULT]
            enabled: True
            """))
        enabled = cronscript_enabled(config, 'foo', self.log)
        self.assertIs(True, enabled)

    def test_default_false(self):
        config = self.makeConfig(dedent("""\
            [DEFAULT]
            enabled: False
            """))
        enabled = cronscript_enabled(config, 'foo', self.log)
        self.assertIs(False, enabled)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
