# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test the mailing list administration script."""

import os
import subprocess
import unittest

from zope.component import getUtility
from canonical.launchpad.interfaces import IMailingListSet
from canonical.launchpad.ftests.mailinglists_helper import new_team
from canonical.testing import LaunchpadZopelessLayer

import canonical
scripts_dir = os.path.abspath(os.path.join(
    os.path.dirname(canonical.__file__),
    '../../scripts'))


class TestMailingListAdminScript(unittest.TestCase):
    """Test the mailing list admin script."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create several teams and their mailing lists."""
        self.team_one = new_team('team-one')
        self.team_two = new_team('team-two')
        list_set = getUtility(IMailingListSet)
        self.list_one = list_set.new(self.team_one)
        self.list_two = list_set.new(self.team_two)
        self.layer.txn.commit()

    def _run_command(self, command_string):
        command = command_string.split()
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=scripts_dir)
        stdout, stderr = proc.communicate()
        self.assertEqual(stderr, '')
        self.assertEqual(proc.returncode, 0)
        return stdout

    def test_list_command(self):
        """Test the 'mlist-admin.py list' command."""
        stdout = self._run_command('./mlist-admin.py list')
        self.assertEqual(stdout.splitlines(), ['team-one', 'team-two'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
