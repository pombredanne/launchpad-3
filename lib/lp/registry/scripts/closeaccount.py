# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Remove personal details of a user from the database, leaving a stub."""

__metaclass__ = type
__all__ = ['CloseAccountScript']

from storm.expr import (
    LeftJoin,
    Lower,
    Or,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.answers.enums import QuestionStatus
from lp.answers.model.question import Question
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.model.bugtask import BugTask
from lp.hardwaredb.model.hwdb import HWSubmission
from lp.registry.interfaces.person import PersonCreationRationale
from lp.registry.model.person import (
    Person,
    PersonSettings,
    )
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.services.database import postgresql
from lp.services.database.constants import DEFAULT
from lp.services.database.interfaces import IMasterStore
from lp.services.database.sqlbase import cursor
from lp.services.identity.interfaces.account import (
    AccountCreationRationale,
    AccountStatus,
    )
from lp.services.identity.model.emailaddress import EmailAddress
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.enums import ArchiveSubscriberStatus
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriberSet
from lp.soyuz.model.archivesubscriber import ArchiveSubscriber


def close_account(username, log):
    """Close a person's account.

    Return True on success, or log an error message and return False
    """
    store = IMasterStore(Person)
    janitor = getUtility(ILaunchpadCelebrities).janitor

    cur = cursor()
    references = list(postgresql.listReferences(cur, 'person', 'id'))
    postgresql.check_indirect_references(references)

    person = store.using(
        Person,
        LeftJoin(EmailAddress, Person.id == EmailAddress.personID)
    ).find(
        Person,
        Or(Person.name == username,
           Lower(EmailAddress.email) == Lower(username))).one()
    if person is None:
        raise LaunchpadScriptFailure("User %s does not exist" % username)
    person_name = person.name

    # We don't do teams
    if person.is_team:
        raise LaunchpadScriptFailure("%s is a team" % person_name)

    log.info("Closing %s's account" % person_name)

    def table_notification(table):
        log.debug("Handling the %s table" % table)

    # All names starting with 'removed' are blacklisted, so this will always
    # succeed.
    new_name = 'removed%d' % person.id

    # Some references can safely remain in place and link to the cleaned-out
    # Person row.
    skip = {
        # These references express some kind of audit trail.  The actions in
        # question still happened, and in some cases the rows may still have
        # functional significance (e.g. subscriptions or access grants), but
        # we no longer identify the actor.
        ('accessartifactgrant', 'grantor'),
        ('accesspolicygrant', 'grantor'),
        ('binarypackagepublishinghistory', 'removed_by'),
        ('branch', 'registrant'),
        ('branchmergeproposal', 'merge_reporter'),
        ('branchmergeproposal', 'merger'),
        ('branchmergeproposal', 'queuer'),
        ('branchmergeproposal', 'registrant'),
        ('branchmergeproposal', 'reviewer'),
        ('branchsubscription', 'subscribed_by'),
        ('bug', 'owner'),
        ('bug', 'who_made_private'),
        ('bugactivity', 'person'),
        ('bugnomination', 'decider'),
        ('bugnomination', 'owner'),
        ('bugtask', 'owner'),
        ('bugsubscription', 'subscribed_by'),
        ('codeimport', 'owner'),
        ('codeimport', 'registrant'),
        ('codeimportevent', 'person'),
        ('faq', 'last_updated_by'),
        ('featureflagchangelogentry', 'person'),
        ('gitactivity', 'changee'),
        ('gitactivity', 'changer'),
        ('gitrepository', 'registrant'),
        ('gitrule', 'creator'),
        ('gitrulegrant', 'grantor'),
        ('gitsubscription', 'subscribed_by'),
        ('message', 'owner'),
        ('messageapproval', 'disposed_by'),
        ('messageapproval', 'posted_by'),
        ('packagecopyrequest', 'requester'),
        ('packagediff', 'requester'),
        ('packageupload', 'signing_key_owner'),
        ('personlocation', 'last_modified_by'),
        ('persontransferjob', 'major_person'),
        ('persontransferjob', 'minor_person'),
        ('poexportrequest', 'person'),
        ('pofile', 'lasttranslator'),
        ('pofiletranslator', 'person'),
        ('product', 'registrant'),
        ('question', 'answerer'),
        ('questionreopening', 'answerer'),
        ('questionreopening', 'reopener'),
        ('snapbuild', 'requester'),
        ('sourcepackagepublishinghistory', 'creator'),
        ('sourcepackagepublishinghistory', 'removed_by'),
        ('sourcepackagepublishinghistory', 'sponsor'),
        ('sourcepackagerecipebuild', 'requester'),
        ('sourcepackagerelease', 'creator'),
        ('sourcepackagerelease', 'maintainer'),
        ('sourcepackagerelease', 'signing_key_owner'),
        ('specification', 'approver'),
        ('specification', 'completer'),
        ('specification', 'drafter'),
        ('specification', 'goal_decider'),
        ('specification', 'goal_proposer'),
        ('specification', 'last_changed_by'),
        ('specification', 'starter'),
        ('structuralsubscription', 'subscribed_by'),
        ('teammembership', 'acknowledged_by'),
        ('teammembership', 'proposed_by'),
        ('teammembership', 'reviewed_by'),
        ('translationimportqueueentry', 'importer'),
        ('translationmessage', 'reviewer'),
        ('translationmessage', 'submitter'),
        ('translationrelicensingagreement', 'person'),
        ('usertouseremail', 'recipient'),
        ('usertouseremail', 'sender'),
        ('xref', 'creator'),

        # This is maintained by trigger functions and a garbo job.  It
        # doesn't need to be updated immediately.
        ('bugsummary', 'viewed_by'),

        # XXX cjwatson 2019-05-02 bug=1827399: This is suboptimal because it
        # does retain some personal information, but it's currently hard to
        # deal with due to the size and complexity of references to it.  We
        # can hopefully provide a garbo job for this eventually.
        ('revisionauthor', 'person'),
        }
    reference_names = {
        (src_tab, src_col) for src_tab, src_col, _, _, _, _ in references}
    for src_tab, src_col in skip:
        if (src_tab, src_col) not in reference_names:
            raise AssertionError(
                "%s.%s is not a Person reference; possible typo?" %
                (src_tab, src_col))

    # XXX cjwatson 2018-11-29: Registrants could possibly be left as-is, but
    # perhaps we should pretend that the registrant was ~registry in that
    # case instead?

    # Remove the EmailAddress. This is the most important step, as
    # people requesting account removal seem to primarily be interested
    # in ensuring we no longer store this information.
    table_notification('EmailAddress')
    store.find(EmailAddress, EmailAddress.personID == person.id).remove()

    # Clean out personal details from the Person table
    table_notification('Person')
    person.display_name = 'Removed by request'
    person.name = new_name
    person.homepage_content = None
    person.icon = None
    person.mugshot = None
    person.hide_email_addresses = False
    person.registrant = None
    person.logo = None
    person.creation_rationale = PersonCreationRationale.UNKNOWN
    person.creation_comment = None

    # Keep the corresponding PersonSettings row, but reset everything to the
    # defaults.
    table_notification('PersonSettings')
    store.find(PersonSettings, PersonSettings.personID == person.id).set(
        selfgenerated_bugnotifications=DEFAULT,
        # XXX cjwatson 2018-11-29: These two columns have NULL defaults, but
        # perhaps shouldn't?
        expanded_notification_footers=False,
        require_strong_email_authentication=False)
    skip.add(('personsettings', 'person'))

    # Remove almost everything from the Account row and the corresponding
    # OpenIdIdentifier rows, preserving only a minimal audit trail.
    if person.account is not None:
        table_notification('Account')
        account = removeSecurityProxy(person.account)
        account.displayname = 'Removed by request'
        account.creation_rationale = AccountCreationRationale.UNKNOWN
        person.setAccountStatus(
            AccountStatus.CLOSED, janitor, "Closed using close-account.")

        table_notification('OpenIdIdentifier')
        store.find(
            OpenIdIdentifier,
            OpenIdIdentifier.account_id == account.id).remove()

    # Reassign their bugs
    table_notification('BugTask')
    store.find(BugTask, BugTask.assigneeID == person.id).set(assigneeID=None)

    # Reassign questions assigned to the user, and close all their questions
    # in non-final states since nobody else can.
    table_notification('Question')
    store.find(Question, Question.assigneeID == person.id).set(assigneeID=None)
    owned_non_final_questions = store.find(
        Question, Question.ownerID == person.id,
        Question.status.is_in([
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO,
            QuestionStatus.ANSWERED,
            ]))
    owned_non_final_questions.set(
        status=QuestionStatus.SOLVED,
        whiteboard=(
            'Closed by Launchpad due to owner requesting account removal'))
    skip.add(('question', 'owner'))

    # Remove rows from tables in simple cases in the given order
    removals = [
        # Trash their email addresses. People who request complete account
        # removal would be unhappy if they reregistered with their old email
        # address and this resurrected their deleted account, as the email
        # address is probably the piece of data we store that they were most
        # concerned with being removed from our systems.
        ('EmailAddress', 'person'),

        # Trash their codes of conduct and GPG keys
        ('SignedCodeOfConduct', 'owner'),
        ('GpgKey', 'owner'),

        # Subscriptions and notifications
        ('BranchSubscription', 'person'),
        ('BugMute', 'person'),
        ('BugNotificationRecipient', 'person'),
        ('BugSubscription', 'person'),
        ('BugSubscriptionFilterMute', 'person'),
        ('GitSubscription', 'person'),
        ('MailingListSubscription', 'person'),
        ('QuestionSubscription', 'person'),
        ('SpecificationSubscription', 'person'),
        ('StructuralSubscription', 'subscriber'),

        # Personal stuff, freeing up the namespace for others who want to play
        # or just to remove any fingerprints identifying the user.
        ('IrcId', 'person'),
        ('JabberId', 'person'),
        ('WikiName', 'person'),
        ('PersonLanguage', 'person'),
        ('PersonLocation', 'person'),
        ('SshKey', 'person'),

        # Karma
        ('Karma', 'person'),
        ('KarmaCache', 'person'),
        ('KarmaTotalCache', 'person'),

        # Team memberships
        ('TeamMembership', 'person'),
        ('TeamParticipation', 'person'),

        # Contacts
        ('AnswerContact', 'person'),

        # Pending items in queues
        ('POExportRequest', 'person'),

        # Access grants
        ('AccessArtifactGrant', 'grantee'),
        ('AccessPolicyGrant', 'grantee'),
        ('ArchivePermission', 'person'),
        ('GitRuleGrant', 'grantee'),
        ('SharingJob', 'grantee'),

        # Soyuz reporting
        ('LatestPersonSourcePackageReleaseCache', 'creator'),
        ('LatestPersonSourcePackageReleaseCache', 'maintainer'),

        # "Affects me too" information
        ('BugAffectsPerson', 'person'),
        ]
    for table, person_id_column in removals:
        table_notification(table)
        store.execute("""
            DELETE FROM %(table)s WHERE %(person_id_column)s = ?
            """ % {
                'table': table,
                'person_id_column': person_id_column,
                },
            (person.id,))

    # Trash Sprint Attendance records in the future.
    table_notification('SprintAttendance')
    store.execute("""
        DELETE FROM SprintAttendance
        USING Sprint
        WHERE Sprint.id = SprintAttendance.sprint
            AND attendee = ?
            AND Sprint.time_starts > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        """, (person.id,))
    # Any remaining past sprint attendance records can harmlessly refer to
    # the placeholder person row.
    skip.add(('sprintattendance', 'attendee'))

    # generate_ppa_htaccess currently relies on seeing active
    # ArchiveAuthToken rows so that it knows which ones to remove from
    # .htpasswd files on disk in response to the cancellation of the
    # corresponding ArchiveSubscriber rows; but even once PPA authorisation
    # is handled dynamically, we probably still want to have the per-person
    # audit trail here.
    archive_subscriber_ids = set(store.find(
        ArchiveSubscriber.id,
        ArchiveSubscriber.subscriber_id == person.id,
        ArchiveSubscriber.status == ArchiveSubscriberStatus.CURRENT))
    if archive_subscriber_ids:
        getUtility(IArchiveSubscriberSet).cancel(
            archive_subscriber_ids, janitor)
    skip.add(('archivesubscriber', 'subscriber'))
    skip.add(('archiveauthtoken', 'person'))

    # Remove hardware submissions.
    table_notification('HWSubmissionDevice')
    store.execute("""
        DELETE FROM HWSubmissionDevice
        USING HWSubmission
        WHERE HWSubmission.id = HWSubmissionDevice.submission
            AND owner = ?
        """, (person.id,))
    table_notification('HWSubmission')
    store.find(HWSubmission, HWSubmission.ownerID == person.id).remove()

    has_references = False

    # Check for active related projects, and skip inactive ones.
    for col in 'bug_supervisor', 'driver', 'owner':
        # Raw SQL because otherwise using Product._owner while displaying it
        # as Product.owner is too fiddly.
        result = store.execute("""
            SELECT COUNT(*) FROM product WHERE active AND %(col)s = ?
            """ % {'col': col},
            (person.id,))
        count = result.get_one()[0]
        if count:
            log.error(
                "User %s is still referenced by %d product.%s values" %
                (person_name, count, col))
            has_references = True
        skip.add(('product', col))
    for col in 'driver', 'owner':
        count = store.find(
            ProductSeries,
            ProductSeries.product == Product.id, Product.active,
            getattr(ProductSeries, col) == person).count()
        if count:
            log.error(
                "User %s is still referenced by %d productseries.%s values" %
                (person_name, count, col))
            has_references = True
        skip.add(('productseries', col))

    # Closing the account will only work if all references have been handled
    # by this point.  If not, it's safer to bail out.  It's OK if this
    # doesn't work in all conceivable situations, since some of them may
    # require careful thought and decisions by a human administrator.
    for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
        if (src_tab, src_col) in skip:
            continue
        result = store.execute("""
            SELECT COUNT(*) FROM %(src_tab)s WHERE %(src_col)s = ?
            """ % {
                'src_tab': src_tab,
                'src_col': src_col,
                },
            (person.id,))
        count = result.get_one()[0]
        if count:
            log.error(
                "User %s is still referenced by %d %s.%s values" %
                (person_name, count, src_tab, src_col))
            has_references = True
    if has_references:
        raise LaunchpadScriptFailure(
            "User %s is still referenced" % person_name)

    return True


class CloseAccountScript(LaunchpadScript):

    usage = '%prog [options] (username|email) [...]'
    description = (
        "Close a person's account, deleting as much personal information "
        "as possible.")

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option(
            "-n", "--dry-run", default=False, action="store_true",
            help="Do not commit changes.")

    def main(self):
        if not self.args:
            raise LaunchpadScriptFailure(
                "Must specify username (Person.name)")

        for username in self.args:
            try:
                close_account(unicode(username), self.logger)
            except Exception:
                self.txn.abort()
                raise

        if self.options.dry_run:
            self.logger.debug("Dry run, so not committing changes")
            self.txn.abort()
        else:
            self.logger.debug("Committing changes")
            self.txn.commit()
