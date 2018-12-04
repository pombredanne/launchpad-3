# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the close-account script."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import (
    Not,
    StartsWith,
    )
import transaction
from twisted.python.compat import nativeString
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.answers.enums import QuestionStatus
from lp.registry.interfaces.person import IPersonSet
from lp.registry.scripts.closeaccount import CloseAccountScript
from lp.services.database.sqlbase import flush_database_caches
from lp.services.identity.interfaces.account import (
    AccountStatus,
    IAccountSet,
    )
from lp.services.identity.interfaces.emailaddress import IEmailAddressSet
from lp.services.log.logger import BufferLogger
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
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
        script.logger = BufferLogger()
        script.txn = transaction
        return script

    def runScript(self, script):
        try:
            script.main()
        finally:
            self.addDetail("log", script.logger.content)
            flush_database_caches()

    def makePopulatedUser(self):
        """Return a person and account linked to some personal information."""
        person = self.factory.makePerson(karma=10)
        self.assertEqual(AccountStatus.ACTIVE, person.account.status)
        self.assertNotEqual([], list(person.account.openid_identifiers))
        self.factory.makeBugTask().transitionToAssignee(person, validate=False)
        self.factory.makeQuestion().assignee = person
        self.factory.makeQuestion(owner=person)
        self.factory.makeGPGKey(owner=person)
        self.factory.makeBranchSubscription(person=person)
        self.factory.makeBug().subscribe(person, person)
        self.factory.makeGitSubscription(person=person)
        team = self.factory.makeTeam()
        self.factory.makeMailingList(team, team.teamowner).subscribe(person)
        self.factory.makeQuestionSubscription(person=person)
        self.factory.makeSpecification().subscribe(person)
        person.addLanguage(self.factory.makeLanguage())
        self.factory.makeSSHKey(person=person)
        self.factory.makeAccessArtifactGrant(grantee=person)
        self.factory.makeAccessPolicyGrant(grantee=person)
        self.factory.makeGitRuleGrant(grantee=person)
        person.selfgenerated_bugnotifications = True
        person.expanded_notification_footers = True
        person.require_strong_email_authentication = True
        return person, person.id, person.account.id

    def assertRemoved(self, account_id, person_id):
        # The Account row still exists, but has been anonymised, leaving
        # only a minimal audit trail.
        account = getUtility(IAccountSet).get(account_id)
        self.assertEqual('Removed by request', account.displayname)
        self.assertEqual(AccountStatus.CLOSED, account.status)
        self.assertIn('Closed using close-account.', account.status_history)

        # The Person row still exists to maintain links with information
        # that won't be removed, such as bug comments, but has been
        # anonymised.
        person = getUtility(IPersonSet).get(person_id)
        self.assertThat(person.name, StartsWith('removed'))
        self.assertEqual('Removed by request', person.display_name)
        self.assertEqual(account, person.account)

        # The corresponding PersonSettings row has been reset to the
        # defaults.
        self.assertFalse(person.selfgenerated_bugnotifications)
        self.assertFalse(person.expanded_notification_footers)
        self.assertFalse(person.require_strong_email_authentication)

        # EmailAddress and OpenIdIdentifier rows have been removed.
        self.assertEqual(
            [], list(getUtility(IEmailAddressSet).getByPerson(person)))
        self.assertEqual([], list(account.openid_identifiers))

    def assertNotRemoved(self, account_id, person_id):
        account = getUtility(IAccountSet).get(account_id)
        self.assertNotEqual('Removed by request', account.displayname)
        self.assertEqual(AccountStatus.ACTIVE, account.status)
        person = getUtility(IPersonSet).get(person_id)
        self.assertEqual(account, person.account)
        self.assertNotEqual('Removed by request', person.display_name)
        self.assertThat(person.name, Not(StartsWith('removed')))
        self.assertNotEqual(
            [], list(getUtility(IEmailAddressSet).getByPerson(person)))
        self.assertNotEqual([], list(account.openid_identifiers))

    def test_nonexistent(self):
        script = self.makeScript(['nonexistent-person'])
        with dbuser('launchpad'):
            self.assertRaisesWithContent(
                LaunchpadScriptFailure,
                'User nonexistent-person does not exist',
                self.runScript, script)

    def test_team(self):
        team = self.factory.makeTeam()
        script = self.makeScript([team.name])
        with dbuser('launchpad'):
            self.assertRaisesWithContent(
                LaunchpadScriptFailure,
                '%s is a team' % team.name,
                self.runScript, script)

    def test_unhandled_reference(self):
        person = self.factory.makePerson()
        person_id = person.id
        account_id = person.account.id
        self.factory.makeProduct(owner=person)
        script = self.makeScript([nativeString(person.name)])
        with dbuser('launchpad'):
            self.assertRaisesWithContent(
                LaunchpadScriptFailure,
                'User %s is still referenced' % person.name,
                self.runScript, script)
        self.assertIn(
            'ERROR User %s is still referenced by 1 product.owner values' % (
                person.name),
            script.logger.getLogBuffer())
        self.assertNotRemoved(account_id, person_id)

    def test_single_by_name(self):
        person, person_id, account_id = self.makePopulatedUser()
        script = self.makeScript([nativeString(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)

    def test_single_by_email(self):
        person, person_id, account_id = self.makePopulatedUser()
        script = self.makeScript([nativeString(person.preferredemail.email)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)

    def test_multiple(self):
        persons = [self.factory.makePerson() for _ in range(3)]
        person_ids = [person.id for person in persons]
        account_ids = [person.account.id for person in persons]
        script = self.makeScript([persons[0].name, persons[1].name])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_ids[0], person_ids[0])
        self.assertRemoved(account_ids[1], person_ids[1])
        self.assertNotRemoved(account_ids[2], person_ids[2])

    def test_retains_audit_trail(self):
        person = self.factory.makePerson()
        person_id = person.id
        account_id = person.account.id
        branch_subscription = self.factory.makeBranchSubscription(
            subscribed_by=person)
        snap = self.factory.makeSnap()
        snap_build = self.factory.makeSnapBuild(requester=person, snap=snap)
        specification = self.factory.makeSpecification(drafter=person)
        script = self.makeScript([nativeString(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertEqual(person, branch_subscription.subscribed_by)
        self.assertEqual(person, snap_build.requester)
        self.assertEqual(person, specification.drafter)

    def test_solves_questions_in_non_final_states(self):
        person = self.factory.makePerson()
        person_id = person.id
        account_id = person.account.id
        questions = []
        for status in (
                QuestionStatus.OPEN, QuestionStatus.NEEDSINFO,
                QuestionStatus.ANSWERED):
            question = self.factory.makeQuestion(owner=person)
            question.addComment(person, "comment")
            removeSecurityProxy(question).status = status
            questions.append(question)
        script = self.makeScript([nativeString(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        for question in questions:
            self.assertEqual(QuestionStatus.SOLVED, question.status)
            self.assertEqual(
                'Closed by Launchpad due to owner requesting account removal',
                question.whiteboard)

    def test_skips_questions_in_final_states(self):
        person = self.factory.makePerson()
        person_id = person.id
        account_id = person.account.id
        questions = {}
        for status in (
                QuestionStatus.SOLVED, QuestionStatus.EXPIRED,
                QuestionStatus.INVALID):
            question = self.factory.makeQuestion(owner=person)
            question.addComment(person, "comment")
            removeSecurityProxy(question).status = status
            questions[status] = question
        script = self.makeScript([nativeString(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        for question_status, question in questions.items():
            self.assertEqual(question_status, question.status)
            self.assertIsNone(question.whiteboard)
