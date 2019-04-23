# Copyright 2018-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the close-account script."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import six
from storm.store import Store
from testtools.matchers import (
    MatchesSetwise,
    MatchesStructure,
    Not,
    StartsWith,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.answers.enums import QuestionStatus
from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.model.bugsummary import BugSummary
from lp.hardwaredb.interfaces.hwdb import (
    HWBus,
    IHWDeviceSet,
    IHWSubmissionSet,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.registry.scripts.closeaccount import CloseAccountScript
from lp.scripts.garbo import PopulateLatestPersonSourcePackageReleaseCache
from lp.services.database.sqlbase import (
    flush_database_caches,
    get_transaction_timestamp,
    )
from lp.services.identity.interfaces.account import (
    AccountStatus,
    IAccountSet,
    )
from lp.services.identity.interfaces.emailaddress import IEmailAddressSet
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.enums import (
    ArchiveSubscriberStatus,
    PackagePublishingStatus,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import LaunchpadZopelessLayer
from lp.translations.interfaces.pofiletranslator import IPOFileTranslatorSet
from lp.translations.interfaces.translationsperson import ITranslationsPerson


class TestCloseAccount(TestCaseWithFactory):
    """Test the close-account script.

    Unfortunately, we have no way of detecting schema updates containing new
    information that needs to be removed or sanitized on account closure
    apart from reviewers noticing and prompting developers to update this
    script.  See Bug #120506 for more details.
    """

    layer = LaunchpadZopelessLayer

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
        script = self.makeScript([six.ensure_str(person.name)])
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
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)

    def test_single_by_email(self):
        person, person_id, account_id = self.makePopulatedUser()
        script = self.makeScript([six.ensure_str(person.preferredemail.email)])
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

    def test_unactivated(self):
        person = self.factory.makePerson(
            account_status=AccountStatus.NOACCOUNT)
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([person.guessedemails[0].email])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)

    def test_retains_audit_trail(self):
        person = self.factory.makePerson()
        person_id = person.id
        account_id = person.account.id
        branch_subscription = self.factory.makeBranchSubscription(
            subscribed_by=person)
        snap = self.factory.makeSnap()
        snap_build = self.factory.makeSnapBuild(requester=person, snap=snap)
        specification = self.factory.makeSpecification(drafter=person)
        script = self.makeScript([six.ensure_str(person.name)])
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
        script = self.makeScript([six.ensure_str(person.name)])
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
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        for question_status, question in questions.items():
            self.assertEqual(question_status, question.status)
            self.assertIsNone(question.whiteboard)

    def test_handles_packaging_references(self):
        person = self.factory.makePerson()
        person_id = person.id
        account_id = person.account.id
        self.factory.makeGPGKey(person)
        publisher = SoyuzTestPublisher()
        publisher.person = person
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        spph = publisher.getPubSource(
            status=PackagePublishingStatus.PUBLISHED,
            distroseries=ubuntu.currentseries,
            maintainer=person, creator=person)
        with dbuser('garbo_frequently'):
            job = PopulateLatestPersonSourcePackageReleaseCache(
                DevNullLogger())
            while not job.isDone():
                job(chunk_size=100)
        self.assertTrue(person.hasMaintainedPackages())
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertEqual(person, spph.package_maintainer)
        self.assertEqual(person, spph.package_creator)
        self.assertFalse(person.hasMaintainedPackages())

    def test_skips_reported_bugs(self):
        person = self.factory.makePerson()
        bug = self.factory.makeBug(owner=person)
        bugtask = self.factory.makeBugTask(bug=bug, owner=person)
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertEqual(person, bug.owner)
        self.assertEqual(person, bugtask.owner)

    def test_handles_bug_affects_person(self):
        person = self.factory.makePerson()
        bug = self.factory.makeBug()
        bug.markUserAffected(person)
        self.assertTrue(bug.isUserAffected(person))
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertFalse(bug.isUserAffected(person))

    def test_skips_translation_relicensing_agreements(self):
        person = self.factory.makePerson()
        translations_person = ITranslationsPerson(person)
        translations_person.translations_relicensing_agreement = True
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertTrue(translations_person.translations_relicensing_agreement)

    def test_skips_po_file_translators(self):
        person = self.factory.makePerson()
        pofile = self.factory.makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        self.factory.makeCurrentTranslationMessage(
            potmsgset=potmsgset, translator=person, language=pofile.language)
        self.assertIsNotNone(
            getUtility(IPOFileTranslatorSet).getForPersonPOFile(
                person, pofile))
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertIsNotNone(
            getUtility(IPOFileTranslatorSet).getForPersonPOFile(
                person, pofile))

    def test_handles_archive_subscriptions_and_tokens(self):
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(private=True)
        subscription = ppa.newSubscription(person, ppa.owner)
        other_subscription = ppa.newSubscription(
            self.factory.makePerson(), ppa.owner)
        ppa.newAuthToken(person)
        self.assertEqual(ArchiveSubscriberStatus.CURRENT, subscription.status)
        self.assertIsNotNone(ppa.getAuthToken(person))
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            now = get_transaction_timestamp(Store.of(person))
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertEqual(
            ArchiveSubscriberStatus.CANCELLED, subscription.status)
        self.assertEqual(now, subscription.date_cancelled)
        self.assertEqual(
            ArchiveSubscriberStatus.CURRENT, other_subscription.status)
        self.assertIsNotNone(ppa.getAuthToken(person))

    def test_handles_hardware_submissions(self):
        person = self.factory.makePerson()
        submission = self.factory.makeHWSubmission(
            emailaddress=person.preferredemail.email)
        other_submission = self.factory.makeHWSubmission()
        device = getUtility(IHWDeviceSet).getByDeviceID(
            HWBus.PCI, '0x10de', '0x0455')
        with dbuser('hwdb-submission-processor'):
            parent_submission_device = self.factory.makeHWSubmissionDevice(
                submission, device, None, None, 1)
            self.factory.makeHWSubmissionDevice(
                submission, device, None, parent_submission_device, 2)
            other_submission_device = self.factory.makeHWSubmissionDevice(
                other_submission, device, None, None, 1)
        key = submission.submission_key
        other_key = other_submission.submission_key
        hw_submission_set = getUtility(IHWSubmissionSet)
        self.assertNotEqual([], list(hw_submission_set.getByOwner(person)))
        self.assertEqual(submission, hw_submission_set.getBySubmissionKey(key))
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertEqual([], list(hw_submission_set.getByOwner(person)))
        self.assertIsNone(hw_submission_set.getBySubmissionKey(key))
        self.assertEqual(
            other_submission, hw_submission_set.getBySubmissionKey(other_key))
        self.assertEqual(
            [other_submission_device], list(other_submission.devices))

    def test_skips_bug_summary(self):
        person = self.factory.makePerson()
        other_person = self.factory.makePerson()
        bug = self.factory.makeBug(information_type=InformationType.USERDATA)
        bug.subscribe(person, bug.owner)
        bug.subscribe(other_person, bug.owner)
        store = Store.of(bug)
        summaries = list(store.find(
            BugSummary,
            BugSummary.viewed_by_id.is_in([person.id, other_person.id])))
        self.assertThat(summaries, MatchesSetwise(
            MatchesStructure.byEquality(count=1, viewed_by=person),
            MatchesStructure.byEquality(count=1, viewed_by=other_person)))
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        # BugSummaryJournal has been updated, but BugSummary hasn't yet.
        summaries = list(store.find(
            BugSummary,
            BugSummary.viewed_by_id.is_in([person.id, other_person.id])))
        self.assertThat(summaries, MatchesSetwise(
            MatchesStructure.byEquality(count=1, viewed_by=person),
            MatchesStructure.byEquality(count=1, viewed_by=other_person),
            MatchesStructure.byEquality(count=-1, viewed_by=person)))
        # If we force an update (the equivalent of the
        # BugSummaryJournalRollup garbo job), that's enough to get rid of
        # the reference.
        store.execute('SELECT bugsummary_rollup_journal()')
        summaries = list(store.find(
            BugSummary,
            BugSummary.viewed_by_id.is_in([person.id, other_person.id])))
        self.assertThat(summaries, MatchesSetwise(
            MatchesStructure.byEquality(viewed_by=other_person)))

    def test_skips_bug_nomination(self):
        person = self.factory.makePerson()
        other_person = self.factory.makePerson()
        bug = self.factory.makeBug()
        targets = [self.factory.makeProductSeries() for _ in range(2)]
        self.factory.makeBugTask(bug=bug, target=targets[0].parent)
        bug.addNomination(person, targets[0])
        self.factory.makeBugTask(bug=bug, target=targets[1].parent)
        bug.addNomination(other_person, targets[1])
        self.assertThat(bug.getNominations(), MatchesSetwise(
            MatchesStructure.byEquality(owner=person),
            MatchesStructure.byEquality(owner=other_person)))
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertThat(bug.getNominations(), MatchesSetwise(
            MatchesStructure.byEquality(owner=person),
            MatchesStructure.byEquality(owner=other_person)))

    def test_skips_inactive_product_owner(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct(owner=person)
        product.active = False
        person_id = person.id
        account_id = person.account.id
        script = self.makeScript([six.ensure_str(person.name)])
        with dbuser('launchpad'):
            self.runScript(script)
        self.assertRemoved(account_id, person_id)
        self.assertEqual(person, product.owner)
