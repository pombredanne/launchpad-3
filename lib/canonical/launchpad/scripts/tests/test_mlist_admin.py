# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test the mailing list administration script."""

import os
import subprocess
import unittest

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IMailingListSet, IPersonSet, MailingListStatus)
from canonical.launchpad.ftests.mailinglists_helper import new_team
from canonical.testing import LaunchpadZopelessLayer

import canonical
scripts_dir = os.path.abspath(os.path.join(
    os.path.dirname(canonical.__file__),
    '../../scripts'))

SPACE = ' '


class TestMailingListAdminScript(unittest.TestCase):
    """Test the mailing list admin script."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create several teams and their mailing lists."""
        team_one = new_team('team-one')
        team_two = new_team('team-two')
        team_three = new_team('team-three')
        self.list_set = getUtility(IMailingListSet)
        list_one = self.list_set.new(team_one)
        list_two = self.list_set.new(team_two)
        # Do not give team-three a mailing list.
        self.layer.txn.commit()

    def _run_command(self, command_string):
        """Run a command in our scripts directory."""
        command = command_string.split()
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=scripts_dir)
        stdout, stderr = proc.communicate()
        self.assertEqual(stderr, '')
        self.assertEqual(proc.returncode, 0)
        return sorted(stdout.splitlines())

    def _run_error_command(self, command_string):
        """Run a command that will produce an error."""
        command = command_string.split()
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=scripts_dir)
        stdout, stderr = proc.communicate()
        self.assertEqual(stdout, '')
        self.assertNotEqual(proc.returncode, 0)
        return stderr.splitlines()

    def test_list_command(self):
        stdout = self._run_command('./mlist-admin.py list')
        self.assertEqual(stdout, ['team-one', 'team-two'])

    def _review(self, approves, declines, reviewer='sabdfl'):
        """Use the admin script to approve and decline mailing lists."""
        # For convenience.
        equal = self.assertEqual
        reviewer_person = getUtility(IPersonSet).getByName(reviewer)
        # Do approvals.
        stdout = self._run_command(
            './mlist-admin.py --reviewer %s approve %s' %
            (reviewer, SPACE.join(approves)))
        expected_output = ['APPROVED: ' + team_name for team_name in approves]
        equal(stdout, sorted(expected_output))
        for team_name in approves:
            mailing_list = self.list_set.get(team_name)
            equal(mailing_list.status, MailingListStatus.APPROVED)
            equal(mailing_list.reviewer, reviewer_person)
        # Do declines.
        stdout = self._run_command(
            './mlist-admin.py --reviewer %s decline %s' %
            (reviewer, SPACE.join(declines)))
        expected_output = ['DECLINED: ' + team_name for team_name in declines]
        equal(stdout, sorted(expected_output))
        for team_name in declines:
            mailing_list = self.list_set.get(team_name)
            equal(mailing_list.status, MailingListStatus.DECLINED)
            equal(mailing_list.reviewer, reviewer_person)

    def test_decline_both(self):
        self._review([], ['team-one', 'team-two'])

    def test_approve_one_decline_two(self):
        self._review(['team-one'], ['team-two'])

    def test_approve_two_decline_one(self):
        self._review(['team-two'], ['team-one'])

    def test_approve_both(self):
        self._review(['team-two', 'team-one'], [])

    def test_approve_one(self):
        self._review(['team-one'], [])

    def test_approve_two(self):
        self._review(['team-two'], [])

    def test_decline_one(self):
        self._review([], ['team-one'])

    def test_decline_two(self):
        self._review([], ['team-two'])

    def test_approve_one_decline_two_with_reviewer(self):
        self._review(['team-one'], ['team-two'], 'salgado')

    def test_approve_decline_no_reviewer(self):
        stderr = self._run_error_command('./mlist-admin.py approve team-one')
        self.assertEqual(stderr[-1],
                         'mlist-admin.py: error: --reviewer is required.')
        stderr = self._run_error_command('./mlist-admin.py decline team-two')
        self.assertEqual(stderr[-1], 
                         'mlist-admin.py: error: --reviewer is required.')

    def test_approve_decline_no_list(self):
        stdout = self._run_command(
            './mlist-admin.py --reviewer sabdfl approve team-three')
        self.assertEqual(stdout[-1], 'SKIPPED: team-three (no team list yet)')
        stdout = self._run_command(
            './mlist-admin.py --reviewer sabdfl decline team-three')
        self.assertEqual(stdout[-1], 'SKIPPED: team-three (no team list yet)')

    def test_double_approve_decline_attempt(self):
        # The first time does the initial approval.
        self._run_command(
            './mlist-admin.py --reviewer sabdfl approve team-one')
        # This one attempts to approve the already approved list.
        stdout = self._run_command(
            './mlist-admin.py --reviewer sabdfl approve team-one')
        self.assertEqual(stdout[-1], 'SKIPPED: team-one (already APPROVED)')
        # The first time does the initial decline.
        self._run_command(
            './mlist-admin.py --reviewer sabdfl decline team-two')
        # This one attempts to approve the already declined list.
        stdout = self._run_command(
            './mlist-admin.py --reviewer sabdfl approve team-two')
        self.assertEqual(stdout[-1], 'SKIPPED: team-two (already DECLINED)')

    def test_list_after_admin(self):
        self._review(['team-one', 'team-two'], [])
        stdout = self._run_command('./mlist-admin.py list')
        self.assertEqual(stdout, ['No team mailing lists awaiting approval.'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
