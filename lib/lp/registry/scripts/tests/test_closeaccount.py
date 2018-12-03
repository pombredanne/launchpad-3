# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the close-account script."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.person import IPersonSet
from lp.registry.scripts.closeaccount import CloseAccountScript
from lp.services.identity.interfaces.account import (
    AccountStatus,
    IAccountSet,
    )
from lp.services.log.logger import DevNullLogger
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.faketransaction import FakeTransaction
from lp.testing.layers import ZopelessDatabaseLayer


class TestCloseAccount(TestCaseWithFactory):
    """Test the close-account script.

    Unfortunately, we have no way of detecting schema updates containing new
    information that needs to be removed or sanitized on account closure
    apart from reviewers noticing and prompting developers to update this
    script.  See Bug #120506 for more details.
    """

    layer = ZopelessDatabaseLayer

    def makeScript(self, test_args):
        script = CloseAccountScript(test_args=test_args)
        script.logger = DevNullLogger()
        script.txn = FakeTransaction()
        return script

    def getSampleUser(self, name, email):
        """Return a sampledata account with some personal information."""
        person = getUtility(IPersonSet).getByEmail(email)
        account = removeSecurityProxy(person.account)
        self.assertEqual(AccountStatus.ACTIVE, account.status)
        self.assertEqual(name, person.name)
        return person.id, account.id

    def assertRemoved(self, account_id, person_id):
        # We can't just set the account to DEACTIVATED, as the
        # close-account.py script is used to satisfy people who insist on us
        # removing all their personal details from our system.  The Account
        # has been removed entirely.
        self.assertRaises(
            LookupError, getUtility(IAccountSet).get, account_id)

        # The Person record still exists to maintain links with information
        # that won't be removed, such as bug comments, but has been
        # anonymized.
        person = getUtility(IPersonSet).get(person_id)
        self.assertStartsWith(person.name, 'removed')
        self.assertEqual('Removed by request', person.display_name)

    def assertNotRemoved(self, account_id, person_id):
        account = getUtility(IAccountSet).get(account_id)
        self.assertEqual(AccountStatus.ACTIVE, account.status)
        person = getUtility(IPersonSet).get(person_id)
        self.assertIsNotNone(person.account)

    def test_nonexistent(self):
        script = self.makeScript(['nonexistent-person'])
        with dbuser('launchpad'):
            self.assertRaisesWithContent(
                LaunchpadScriptFailure,
                'User nonexistent-person does not exist',
                script.main)

    def test_team(self):
        team = self.factory.makeTeam()
        script = self.makeScript([team.name])
        with dbuser('launchpad'):
            self.assertRaisesWithContent(
                LaunchpadScriptFailure,
                '%s is a team' % team.name,
                script.main)

    def test_single_by_name(self):
        person_id, account_id = self.getSampleUser('mark', 'mark@example.com')
        script = self.makeScript(['mark'])
        with dbuser('launchpad'):
            script.main()
        self.assertRemoved(account_id, person_id)

    def test_single_by_email(self):
        person_id, account_id = self.getSampleUser('mark', 'mark@example.com')
        script = self.makeScript(['mark@example.com'])
        with dbuser('launchpad'):
            script.main()
        self.assertRemoved(account_id, person_id)

    def test_multiple(self):
        persons = [self.factory.makePerson() for _ in range(3)]
        person_ids = [person.id for person in persons]
        account_ids = [person.account.id for person in persons]
        script = self.makeScript([persons[0].name, persons[1].name])
        with dbuser('launchpad'):
            script.main()
        self.assertRemoved(account_ids[0], person_ids[0])
        self.assertRemoved(account_ids[1], person_ids[1])
        self.assertNotRemoved(account_ids[2], person_ids[2])
