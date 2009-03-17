# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212,W0141

__metaclass__ = type
__all__ = [
    'Branch',
    'BranchSet',
    ]

from datetime import datetime

from bzrlib.branch import Branch as BzrBranch
from bzrlib.revision import NULL_REVISION
from bzrlib import urlutils
import pytz

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from storm.expr import And, Count, Desc, Max, Or, Select
from storm.store import Store
from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin)
from sqlobject.sqlbuilder import AND

from lazr.lifecycle.event import ObjectCreatedEvent

from canonical.config import config
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.sqlbase import (
    cursor, quote, SQLBase, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad import _
from canonical.launchpad.database.branchmergeproposal import (
     BranchMergeProposal)
from canonical.launchpad.database.branchrevision import BranchRevision
from canonical.launchpad.database.branchsubscription import BranchSubscription
from canonical.launchpad.database.job import Job
from canonical.launchpad.database.revision import Revision
from canonical.launchpad.event.branchmergeproposal import (
    NewBranchMergeProposalEvent)
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, NotFoundError)
from canonical.launchpad.interfaces.branch import (
    BranchCreationForbidden, BranchCreationNoTeamOwnedJunkBranches,
    BranchCreatorNotMemberOfOwnerTeam, BranchCreatorNotOwner, BranchExists,
    BranchFormat, BranchLifecycleStatus, BranchMergeControlStatus,
    BranchType, BranchTypeError, CannotDeleteBranch, ControlFormat,
    DEFAULT_BRANCH_STATUS_IN_LISTING, IBranch, IBranchSet,
    MAXIMUM_MIRROR_FAILURES, MIRROR_TIME_INCREMENT, RepositoryFormat)
from canonical.launchpad.interfaces.branch import (
    bazaar_identity, IBranchNavigationMenu, user_has_special_branch_access)
from canonical.launchpad.interfaces.branchcollection import IAllBranches
from canonical.launchpad.interfaces.branchnamespace import (
    get_branch_namespace)
from canonical.launchpad.interfaces.branchmergeproposal import (
     BRANCH_MERGE_PROPOSAL_FINAL_STATES, BranchMergeProposalExists,
     BranchMergeProposalStatus, InvalidBranchMergeProposal)
from canonical.launchpad.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel)
from canonical.launchpad.interfaces.branchtarget import IBranchTarget
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    BranchVisibilityRule)
from canonical.launchpad.interfaces.codehosting import LAUNCHPAD_SERVICES
from canonical.launchpad.mailnotification import NotificationRecipientSet
from canonical.launchpad.validators.person import validate_public_person
from canonical.launchpad.webapp import urlappend
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)


class Branch(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranch, IBranchNavigationMenu)
    _table = 'Branch'
    _defaultOrder = ['product', '-lifecycle_status', 'owner', 'name']

    branch_type = EnumCol(enum=BranchType, notNull=True)

    name = StringCol(notNull=False)
    title = StringCol(notNull=False)
    summary = StringCol(notNull=False)
    url = StringCol(dbName='url')
    branch_format = EnumCol(enum=BranchFormat)
    repository_format = EnumCol(enum=RepositoryFormat)
    # XXX: Aaron Bentley 2008-06-13
    # Rename the metadir_format in the database, see bug 239746
    control_format = EnumCol(enum=ControlFormat, dbName='metadir_format')
    whiteboard = StringCol(default=None)
    mirror_status_message = StringCol(default=None)

    private = BoolCol(default=False, notNull=True)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person',
        storm_validator=validate_public_person, default=None)

    product = ForeignKey(dbName='product', foreignKey='Product', default=None)

    distroseries = ForeignKey(
        dbName='distroseries', foreignKey='DistroSeries', default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        default=None)

    lifecycle_status = EnumCol(
        enum=BranchLifecycleStatus, notNull=True,
        default=BranchLifecycleStatus.DEVELOPMENT)

    last_mirrored = UtcDateTimeCol(default=None)
    last_mirrored_id = StringCol(default=None)
    last_mirror_attempt = UtcDateTimeCol(default=None)
    mirror_failures = IntCol(default=0, notNull=True)
    next_mirror_time = UtcDateTimeCol(default=None)

    last_scanned = UtcDateTimeCol(default=None)
    last_scanned_id = StringCol(default=None)
    revision_count = IntCol(default=DEFAULT, notNull=True)
    stacked_on = ForeignKey(
        dbName='stacked_on', foreignKey='Branch', default=None)

    def __repr__(self):
        return '<Branch %r (%d)>' % (self.unique_name, self.id)

    @property
    def target(self):
        """See `IBranch`."""
        if self.product is None:
            if self.distroseries is None:
                target = self.owner
            else:
                target = self.sourcepackage
        else:
            target = self.product
        return IBranchTarget(target)

    @property
    def namespace(self):
        """See `IBranch`."""
        return self.target.getNamespace(self.owner)

    @property
    def distribution(self):
        """See `IBranch`."""
        if self.distroseries is None:
            return None
        return self.distroseries.distribution

    @property
    def sourcepackage(self):
        """See `IBranch`."""
        # Avoid circular imports.
        from canonical.launchpad.database.sourcepackage import SourcePackage
        if self.distroseries is None:
            return None
        return SourcePackage(self.sourcepackagename, self.distroseries)

    @property
    def revision_history(self):
        return BranchRevision.select('''
            BranchRevision.branch = %s AND
            BranchRevision.sequence IS NOT NULL
            ''' % sqlvalues(self),
            prejoins=['revision'], orderBy='-sequence')

    subscriptions = SQLMultipleJoin(
        'BranchSubscription', joinColumn='branch', orderBy='id')
    subscribers = SQLRelatedJoin(
        'Person', joinColumn='branch', otherColumn='person',
        intermediateTable='BranchSubscription', orderBy='name')

    bug_branches = SQLMultipleJoin(
        'BugBranch', joinColumn='branch', orderBy='id')

    spec_links = SQLMultipleJoin('SpecificationBranch',
        joinColumn='branch',
        orderBy='id')

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_last_modified = UtcDateTimeCol(notNull=True, default=DEFAULT)

    landing_targets = SQLMultipleJoin(
        'BranchMergeProposal', joinColumn='source_branch')

    @property
    def landing_candidates(self):
        """See `IBranch`."""
        return BranchMergeProposal.select("""
            BranchMergeProposal.target_branch = %s AND
            BranchMergeProposal.queue_status NOT IN %s
            """ % sqlvalues(self, BRANCH_MERGE_PROPOSAL_FINAL_STATES))

    @property
    def dependent_branches(self):
        """See `IBranch`."""
        return BranchMergeProposal.select("""
            BranchMergeProposal.dependent_branch = %s AND
            BranchMergeProposal.queue_status NOT IN %s
            """ % sqlvalues(self, BRANCH_MERGE_PROPOSAL_FINAL_STATES))

    def addLandingTarget(self, registrant, target_branch,
                         dependent_branch=None, whiteboard=None,
                         date_created=None, needs_review=False,
                         initial_comment=None, review_requests=None,
                         review_diff=None):
        """See `IBranch`."""
        if self.product is None:
            raise InvalidBranchMergeProposal(
                'Junk branches cannot be used as source branches.')
        if not IBranch.providedBy(target_branch):
            raise InvalidBranchMergeProposal(
                'Target branch must implement IBranch.')
        if self == target_branch:
            raise InvalidBranchMergeProposal(
                'Source and target branches must be different.')
        if self.product != target_branch.product:
            raise InvalidBranchMergeProposal(
                'The source branch and target branch must be branches of the '
                'same project.')
        if dependent_branch is not None:
            if not IBranch.providedBy(dependent_branch):
                raise InvalidBranchMergeProposal(
                    'Dependent branch must implement IBranch.')
            if self.product != dependent_branch.product:
                raise InvalidBranchMergeProposal(
                    'The source branch and dependent branch must be branches '
                    'of the same project.')
            if self == dependent_branch:
                raise InvalidBranchMergeProposal(
                    'Source and dependent branches must be different.')
            if target_branch == dependent_branch:
                raise InvalidBranchMergeProposal(
                    'Target and dependent branches must be different.')

        target = BranchMergeProposal.select("""
            BranchMergeProposal.source_branch = %s AND
            BranchMergeProposal.target_branch = %s AND
            BranchMergeProposal.queue_status NOT IN %s
            """ % sqlvalues(self, target_branch,
                            BRANCH_MERGE_PROPOSAL_FINAL_STATES))
        if target.count() > 0:
            raise BranchMergeProposalExists(
                'There is already a branch merge proposal registered for '
                'branch %s to land on %s that is still active.'
                % (self.unique_name, target_branch.unique_name))

        if date_created is None:
            date_created = UTC_NOW

        if needs_review:
            queue_status = BranchMergeProposalStatus.NEEDS_REVIEW
            date_review_requested = date_created
        else:
            queue_status = BranchMergeProposalStatus.WORK_IN_PROGRESS
            date_review_requested = None

        if review_requests is None:
            review_requests = []

        bmp = BranchMergeProposal(
            registrant=registrant, source_branch=self,
            target_branch=target_branch, dependent_branch=dependent_branch,
            whiteboard=whiteboard, date_created=date_created,
            date_review_requested=date_review_requested,
            queue_status=queue_status, review_diff=review_diff)

        if initial_comment is not None:
            bmp.createComment(
                registrant, None, initial_comment, _notify_listeners=False)

        for reviewer, review_type in review_requests:
            bmp.nominateReviewer(
                reviewer, registrant, review_type, _notify_listeners=False)

        notify(NewBranchMergeProposalEvent(bmp))
        return bmp

    # XXX: Tim Penhey, 2008-06-18, bug 240881
    merge_queue = ForeignKey(
        dbName='merge_robot', foreignKey='MultiBranchMergeQueue',
        default=None)

    merge_control_status = EnumCol(
        enum=BranchMergeControlStatus, notNull=True,
        default=BranchMergeControlStatus.NO_QUEUE)

    def addToLaunchBag(self, launchbag):
        """See `IBranch`."""
        launchbag.add(self.product)
        if self.distroseries is not None:
            launchbag.add(self.distroseries)
            launchbag.add(self.distribution)
            launchbag.add(self.sourcepackage)

    def getStackedBranches(self):
        """See `IBranch`."""
        store = Store.of(self)
        return store.find(Branch, Branch.stacked_on == self)

    def getStackedBranchesWithIncompleteMirrors(self):
        """See `IBranch`."""
        store = Store.of(self)
        return store.find(
            Branch, Branch.stacked_on == self,
            # Have been started.
            Branch.last_mirror_attempt != None,
            # Either never successfully mirrored or started since the last
            # successful mirror.
            Or(Branch.last_mirrored == None,
               Branch.last_mirror_attempt > Branch.last_mirrored))

    def getMergeQueue(self):
        """See `IBranch`."""
        return BranchMergeProposal.select("""
            BranchMergeProposal.target_branch = %s AND
            BranchMergeProposal.queue_status = %s
            """ % sqlvalues(self, BranchMergeProposalStatus.QUEUED),
            orderBy="queue_position")

    @property
    def code_is_browseable(self):
        """See `IBranch`."""
        return (self.revision_count > 0  or self.last_mirrored != None)

    def codebrowse_url(self, *extras):
        """See `IBranch`."""
        if self.private:
            root = config.codehosting.secure_codebrowse_root
        else:
            root = config.codehosting.codebrowse_root
        return urlutils.join(root, self.unique_name, *extras)

    @property
    def bzr_identity(self):
        """See `IBranch`."""
        # XXX: This should not dispatch on product is None
        if self.product is not None:
            series_branch = self.product.development_focus.series_branch
            is_dev_focus = (series_branch == self)
        else:
            is_dev_focus = False
        return bazaar_identity(
            self, self.associatedProductSeries(), is_dev_focus)

    @property
    def related_bugs(self):
        """See `IBranch`."""
        return [bug_branch.bug for bug_branch in self.bug_branches]

    @property
    def warehouse_url(self):
        """See `IBranch`."""
        return 'lp-mirrored:///%s' % self.unique_name

    def getBzrBranch(self):
        """Return the BzrBranch for this database Branch.

        This provides the mirrored copy of the branch.
        """
        return BzrBranch.open(self.warehouse_url)

    @property
    def unique_name(self):
        """See `IBranch`."""
        return u'~%s/%s/%s' % (
            self.owner.name, self.target.name, self.name)

    @property
    def displayname(self):
        """See `IBranch`."""
        if self.title:
            return self.title
        else:
            return self.unique_name

    @property
    def code_reviewer(self):
        """See `IBranch`."""
        if self.reviewer:
            return self.reviewer
        else:
            return self.owner

    def latest_revisions(self, quantity=10):
        """See `IBranch`."""
        return self.revision_history.limit(quantity)

    def revisions_since(self, timestamp):
        """See `IBranch`."""
        return BranchRevision.select(
            'Revision.id=BranchRevision.revision AND '
            'BranchRevision.branch = %d AND '
            'BranchRevision.sequence IS NOT NULL AND '
            'Revision.revision_date > %s' %
            (self.id, quote(timestamp)),
            orderBy='-sequence',
            clauseTables=['Revision'])

    def canBeDeleted(self):
        """See `IBranch`."""
        if ((len(self.deletionRequirements()) != 0) or
            self.getStackedBranches().count() > 0):
            # Can't delete if the branch is associated with anything.
            return False
        else:
            return True

    @property
    def code_import(self):
        from canonical.launchpad.database.codeimport import CodeImportSet
        return CodeImportSet().getByBranch(self)

    def _deletionRequirements(self):
        """Determine what operations must be performed to delete this branch.

        Two dictionaries are returned, one for items that must be deleted,
        one for items that must be altered.  The item in question is the
        key, and the value is a user-facing string explaining why the item
        is affected.

        As well as the dictionaries, this method returns two list of callables
        that may be called to perform the alterations and deletions needed.
        """
        alteration_operations = []
        deletion_operations = []
        # Merge proposals require their source and target branches to exist.
        for merge_proposal in self.landing_targets:
            deletion_operations.append(
                DeletionCallable(merge_proposal,
                    _('This branch is the source branch of this merge'
                    ' proposal.'), merge_proposal.deleteProposal))
        # Cannot use self.landing_candidates, because it ignores merged
        # merge proposals.
        for merge_proposal in BranchMergeProposal.selectBy(
            target_branch=self):
            deletion_operations.append(
                DeletionCallable(merge_proposal,
                    _('This branch is the target branch of this merge'
                    ' proposal.'), merge_proposal.deleteProposal))
        for merge_proposal in BranchMergeProposal.selectBy(
            dependent_branch=self):
            alteration_operations.append(ClearDependentBranch(merge_proposal))

        for bugbranch in self.bug_branches:
            deletion_operations.append(
                DeletionCallable(bugbranch,
                _('This bug is linked to this branch.'),
                bugbranch.destroySelf))
        for spec_link in self.spec_links:
            deletion_operations.append(
                DeletionCallable(spec_link,
                    _('This blueprint is linked to this branch.'),
                    spec_link.destroySelf))
        for series in self.associatedProductSeries():
            alteration_operations.append(ClearSeriesBranch(series, self))
        if self.code_import is not None:
            deletion_operations.append(DeleteCodeImport(self.code_import))
        return (alteration_operations, deletion_operations)

    def deletionRequirements(self):
        """See `IBranch`."""
        alteration_operations, deletion_operations, = (
            self._deletionRequirements())
        result = dict(
            (operation.affected_object, ('alter', operation.rationale)) for
            operation in alteration_operations)
        # Deletion entries should overwrite alteration entries.
        result.update(
            (operation.affected_object, ('delete', operation.rationale)) for
            operation in deletion_operations)
        return result

    def _breakReferences(self):
        """Break all external references to this branch.

        NULLable references will be NULLed.  References which are not NULLable
        will cause the item holding the reference to be deleted.

        This function is guaranteed to perform the operations predicted by
        deletionRequirements, because it uses the same backing function.
        """
        (alteration_operations,
            deletion_operations) = self._deletionRequirements()
        for operation in alteration_operations:
            operation()
        for operation in deletion_operations:
            operation()

    def associatedProductSeries(self):
        """See `IBranch`."""
        # Imported here to avoid circular import.
        from canonical.launchpad.database.productseries import ProductSeries
        return Store.of(self).find(
            ProductSeries,
            Or(ProductSeries.user_branch == self,
               ProductSeries.import_branch == self))

    # subscriptions
    def subscribe(self, person, notification_level, max_diff_lines,
                  review_level):
        """See `IBranch`."""
        # If the person is already subscribed, update the subscription with
        # the specified notification details.
        subscription = self.getSubscription(person)
        if subscription is None:
            subscription = BranchSubscription(
                branch=self, person=person,
                notification_level=notification_level,
                max_diff_lines=max_diff_lines, review_level=review_level)
            Store.of(subscription).flush()
        else:
            subscription.notification_level = notification_level
            subscription.max_diff_lines = max_diff_lines
            subscription.review_level = review_level
        return subscription

    def getSubscription(self, person):
        """See `IBranch`."""
        if person is None:
            return None
        subscription = BranchSubscription.selectOneBy(
            person=person, branch=self)
        return subscription

    def getSubscriptionsByLevel(self, notification_levels):
        """See `IBranch`."""
        notification_levels = [level.value for level in notification_levels]
        return BranchSubscription.select(
            "BranchSubscription.branch = %s "
            "AND BranchSubscription.notification_level IN %s"
            % sqlvalues(self, notification_levels))

    def hasSubscription(self, person):
        """See `IBranch`."""
        return self.getSubscription(person) is not None

    def unsubscribe(self, person):
        """See `IBranch`."""
        subscription = self.getSubscription(person)
        store = Store.of(subscription)
        assert subscription is not None, "User is not subscribed."
        BranchSubscription.delete(subscription.id)
        store.flush()

    def getMainlineBranchRevisions(self, revision_ids):
        return Store.of(self).find(
            BranchRevision,
            BranchRevision.branch == self,
            BranchRevision.sequence != None,
            BranchRevision.revision == Revision.id,
            Revision.revision_id.is_in(revision_ids))

    def getBranchRevision(self, sequence=None, revision=None,
                          revision_id=None):
        """See `IBranch`."""
        params = (sequence, revision, revision_id)
        if len([p for p in params if p is not None]) != 1:
            raise AssertionError(
                "One and only one of sequence, revision, or revision_id "
                "should have a value.")
        if sequence is not None:
            query = BranchRevision.sequence == sequence
        elif revision is not None:
            query = BranchRevision.revision == revision
        else:
            query = And(BranchRevision.revision == Revision.id,
                        Revision.revision_id == revision_id)

        store = Store.of(self)

        return store.find(
            BranchRevision,
            BranchRevision.branch == self,
            query).one()

    def createBranchRevision(self, sequence, revision):
        """See `IBranch`."""
        branch_revision = BranchRevision(
            branch=self, sequence=sequence, revision=revision)
        # Allocate karma if no karma has been allocated for this revision.
        if not revision.karma_allocated:
            revision.allocateKarma(self)
        return branch_revision

    def createBranchRevisionFromIDs(self, revision_id_sequence_pairs):
        """See `IBranch`."""
        if not revision_id_sequence_pairs:
            return
        store = Store.of(self)
        store.execute(
            """
            CREATE TEMPORARY TABLE RevidSequence
            (revision_id text, sequence integer)
            """)
        data = []
        for revid, sequence in revision_id_sequence_pairs:
            data.append('(%s, %s)' % sqlvalues(revid, sequence))
        data = ', '.join(data)
        store.execute(
            "INSERT INTO RevidSequence (revision_id, sequence) VALUES %s"
            % data)
        store.execute(
            """
            INSERT INTO BranchRevision (branch, revision, sequence)
            SELECT %s, Revision.id, RevidSequence.sequence
            FROM RevidSequence, Revision
            WHERE Revision.revision_id = RevidSequence.revision_id
            """ % sqlvalues(self))
        store.execute("DROP TABLE RevidSequence")

    def getTipRevision(self):
        """See `IBranch`."""
        tip_revision_id = self.last_scanned_id
        if tip_revision_id is None:
            return None
        return Revision.selectOneBy(revision_id=tip_revision_id)

    def updateScannedDetails(self, db_revision, revision_count):
        """See `IBranch`."""
        # By taking the minimum of the revision date and the date created, we
        # cap the revision date to make sure that we don't use a future date.
        # The date created is set to be the time that the revision was created
        # in the database, so if the revision_date is a future date, then we
        # use the date created instead.
        if db_revision is None:
            revision_id = NULL_REVISION
            revision_date = UTC_NOW
        else:
            revision_id = db_revision.revision_id
            revision_date = min(
                db_revision.revision_date, db_revision.date_created)

        # If the branch has changed through either a different tip revision or
        # revision count, then update.
        if ((revision_id != self.last_scanned_id) or
            (revision_count != self.revision_count)):
            # If the date of the last revision is greated than the date last
            # modified, then bring the date last modified forward to the last
            # revision date (as long as the revision date isn't in the
            # future).
            if db_revision is None or revision_date > self.date_last_modified:
                self.date_last_modified = revision_date
            self.last_scanned = UTC_NOW
            self.last_scanned_id = revision_id
            self.revision_count = revision_count
            if self.lifecycle_status in (BranchLifecycleStatus.MERGED,
                                         BranchLifecycleStatus.ABANDONED):
                self.lifecycle_status = BranchLifecycleStatus.DEVELOPMENT

    def getNotificationRecipients(self):
        """See `IBranch`."""
        recipients = NotificationRecipientSet()
        for subscription in self.subscriptions:
            if subscription.person.isTeam():
                rationale = 'Subscriber @%s' % subscription.person.name
            else:
                rationale = 'Subscriber'
            recipients.add(subscription.person, subscription, rationale)
        return recipients

    def getScannerData(self):
        """See `IBranch`."""
        cur = cursor()
        cur.execute("""
            SELECT BranchRevision.id, BranchRevision.sequence,
                Revision.revision_id
            FROM Revision, BranchRevision
            WHERE Revision.id = BranchRevision.revision
                AND BranchRevision.branch = %s
            ORDER BY BranchRevision.sequence
            """ % sqlvalues(self))
        ancestry = set()
        history = []
        branch_revision_map = {}
        for branch_revision_id, sequence, revision_id in cur.fetchall():
            ancestry.add(revision_id)
            branch_revision_map[revision_id] = branch_revision_id
            if sequence is not None:
                history.append(revision_id)
        return ancestry, history, branch_revision_map

    def getPullURL(self):
        """See `IBranch`."""
        if self.branch_type == BranchType.MIRRORED:
            # This is a pull branch, hosted externally.
            return self.url
        elif self.branch_type == BranchType.IMPORTED:
            # This is an import branch, imported into bzr from
            # another RCS system such as CVS.
            prefix = config.launchpad.bzr_imports_root_url
            return urlappend(prefix, '%08x' % self.id)
        elif self.branch_type == BranchType.HOSTED:
            # This is a push branch, hosted on Launchpad (pushed there by
            # users via sftp or bzr+ssh).
            return 'lp-hosted:///%s' % (self.unique_name,)
        else:
            raise AssertionError("No pull URL for %r" % (self,))

    def requestMirror(self):
        """See `IBranch`."""
        if self.branch_type == BranchType.REMOTE:
            raise BranchTypeError(self.unique_name)
        self.next_mirror_time = UTC_NOW
        self.syncUpdate()
        return self.next_mirror_time

    def startMirroring(self):
        """See `IBranch`."""
        if self.branch_type == BranchType.REMOTE:
            raise BranchTypeError(self.unique_name)
        self.last_mirror_attempt = UTC_NOW
        self.next_mirror_time = None

    def mirrorComplete(self, last_revision_id):
        """See `IBranch`."""
        if self.branch_type == BranchType.REMOTE:
            raise BranchTypeError(self.unique_name)
        assert self.last_mirror_attempt != None, (
            "startMirroring must be called before mirrorComplete.")
        self.last_mirrored = self.last_mirror_attempt
        self.mirror_failures = 0
        self.mirror_status_message = None
        if (self.next_mirror_time is None
            and self.branch_type == BranchType.MIRRORED):
            # No mirror was requested since we started mirroring.
            self.next_mirror_time = (
                datetime.now(pytz.timezone('UTC')) + MIRROR_TIME_INCREMENT)
        self.last_mirrored_id = last_revision_id

    def mirrorFailed(self, reason):
        """See `IBranch`."""
        if self.branch_type == BranchType.REMOTE:
            raise BranchTypeError(self.unique_name)
        self.mirror_failures += 1
        self.mirror_status_message = reason
        if (self.branch_type == BranchType.MIRRORED
            and self.mirror_failures < MAXIMUM_MIRROR_FAILURES):
            self.next_mirror_time = (
                datetime.now(pytz.timezone('UTC'))
                + MIRROR_TIME_INCREMENT * 2 ** (self.mirror_failures - 1))

    def destroySelf(self, break_references=False):
        """See `IBranch`."""
        from canonical.launchpad.database.branchjob import BranchJob
        if break_references:
            self._breakReferences()
        if self.canBeDeleted():
            # BranchRevisions are taken care of a cascading delete
            # in the database.
            store = Store.of(self)
            # Delete the branch subscriptions.
            subscriptions = store.find(
                BranchSubscription, BranchSubscription.branch == self)
            subscriptions.remove()
            # Delete any linked jobs.
            # Using a sub-select here as joins in delete statements is not
            # valid standard sql.
            jobs = store.find(
                Job,
                Job.id.is_in(Select([BranchJob.jobID],
                                    And(BranchJob.job == Job.id,
                                        BranchJob.branch == self))))
            jobs.remove()
            # Now destroy the branch.
            SQLBase.destroySelf(self)
        else:
            raise CannotDeleteBranch(
                "Cannot delete branch: %s" % self.unique_name)


class DeletionOperation:
    """Represent an operation to perform as part of branch deletion."""

    def __init__(self, affected_object, rationale):
        self.affected_object = affected_object
        self.rationale = rationale

    def __call__(self):
        """Perform the deletion operation."""
        raise NotImplementedError(DeletionOperation.__call__)


class DeletionCallable(DeletionOperation):
    """Deletion operation that invokes a callable."""

    def __init__(self, affected_object, rationale, func):
        DeletionOperation.__init__(self, affected_object, rationale)
        self.func = func

    def __call__(self):
        self.func()


class ClearDependentBranch(DeletionOperation):
    """Deletion operation that clears a merge proposal's dependent branch."""

    def __init__(self, merge_proposal):
        DeletionOperation.__init__(self, merge_proposal,
            _('This branch is the dependent branch of this merge proposal.'))

    def __call__(self):
        self.affected_object.dependent_branch = None
        self.affected_object.syncUpdate()


class ClearSeriesBranch(DeletionOperation):
    """Deletion operation that clears a series' branch."""

    def __init__(self, series, branch):
        DeletionOperation.__init__(
            self, series, _('This series is linked to this branch.'))
        self.branch = branch

    def __call__(self):
        if self.affected_object.user_branch == self.branch:
            self.affected_object.user_branch = None
        if self.affected_object.import_branch == self.branch:
            self.affected_object.import_branch = None
        self.affected_object.syncUpdate()


class DeleteCodeImport(DeletionOperation):
    """Deletion operation that deletes a branch's import."""

    def __init__(self, code_import):
        DeletionOperation.__init__(
            self, code_import, _( 'This is the import data for this branch.'))

    def __call__(self):
        from canonical.launchpad.database.codeimport import CodeImportSet
        CodeImportSet().delete(self.affected_object)


class BranchSet:
    """The set of all branches."""

    implements(IBranchSet)

    def __getitem__(self, branch_id):
        """See `IBranchSet`."""
        branch = self.get(branch_id)
        if branch is None:
            raise NotFoundError(branch_id)
        return branch

    def __iter__(self):
        """See `IBranchSet`."""
        # XXX: JonathanLange 2009-02-10 spec=package-branches: Prejoining
        # product is probably not the best idea, given that there'll be a lot
        # of package branches.
        return iter(Branch.select(prejoins=['owner', 'product']))

    def count(self):
        """See `IBranchSet`."""
        return Branch.select('NOT Branch.private').count()

    def countBranchesWithAssociatedBugs(self):
        """See `IBranchSet`."""
        return Branch.select(
            'NOT Branch.private AND Branch.id = BugBranch.branch',
            clauseTables=['BugBranch'],
            distinct=True).count()

    def _checkVisibilityPolicy(self, creator, owner, product):
        """Return a tuple of private flag and person or team to subscribe.

        This method checks the branch visibility policy of the product.  The
        product can define any number of policies that apply to particular
        teams.  Each team can have only one policy, and that policy is defined
        by the enumerated type BranchVisibilityRule.  The possibilities are
        PUBLIC, PRIVATE, PRIVATE_ONLY, and FORBIDDEN.

        PUBLIC: branches default to public for the team.
        PRIVATE: branches default to private for the team.
        PRIVATE_ONLY: branches are created private, and cannot be changed to
            public.
        FORBIDDEN: users cannot create branches for that product. The forbidden
            policy can only apply to all people, not specific teams.

        As well as specifying a policy for particular teams, there can be a
        policy that applies to everyone.  Since there is no team for everyone,
        a team policy where the team is None applies to everyone.  If there is
        no explicit policy set for everyone, then the default applies, which is
        for branches to be created PUBLIC.

        The user must be in the team of the owner in order to create a branch
        in the owner's namespace.

        If there is a policy that applies specificly to the owner of the
        branch, then that policy is applied for the branch.  This is to handle
        the situation where TeamA is a member of TeamB, TeamA has a PUBLIC
        policy, and TeamB has a PRIVATE policy.  By pushing to TeamA's branch
        area, the PUBLIC policy is used.

        If a owner is a member of more than one team that has a specified
        policy the PRIVATE and PRIVATE_ONLY override PUBLIC policies.

        If the owner is a member of more than one team that has PRIVATE or
        PRIVATE_ONLY set as the policy, then the branch is created private, and
        no team is subscribed to it as we can't guess which team the user means
        to have the visibility.
        """
        PUBLIC_BRANCH = (False, None)
        PRIVATE_BRANCH = (True, None)
        # You are not allowed to specify an owner that you are not a member
        # of.
        if not creator.inTeam(owner):
            if owner.isTeam():
                raise BranchCreatorNotMemberOfOwnerTeam(
                    "%s is not a member of %s"
                    % (creator.displayname, owner.displayname))
            else:
                raise BranchCreatorNotOwner(
                    "%s cannot create branches owned by %s"
                    % (creator.displayname, owner.displayname))
        # If the product is None, then the branch is a +junk branch.
        if product is None:
            # The only team that is allowed to own +junk branches is
            # ~vcs-imports.
            if (owner.isTeam() and
                owner != getUtility(ILaunchpadCelebrities).vcs_imports):
                raise BranchCreationNoTeamOwnedJunkBranches()
            # All junk branches are public.
            return PUBLIC_BRANCH
        # First check if the owner has a defined visibility rule.
        policy = product.getBranchVisibilityRuleForTeam(owner)
        if policy is not None:
            if policy in (BranchVisibilityRule.PRIVATE,
                          BranchVisibilityRule.PRIVATE_ONLY):
                return PRIVATE_BRANCH
            else:
                return PUBLIC_BRANCH

        rule_memberships = dict(
            [(item, []) for item in BranchVisibilityRule.items])

        # Here we ignore the team policy that applies to everyone as
        # that is the base visibility rule and it is checked only if there
        # are no team policies that apply to the owner.
        for item in product.getBranchVisibilityTeamPolicies():
            if item.team is not None and owner.inTeam(item.team):
                rule_memberships[item.rule].append(item.team)

        private_teams = (
            rule_memberships[BranchVisibilityRule.PRIVATE] +
            rule_memberships[BranchVisibilityRule.PRIVATE_ONLY])

        # Private trumps public.
        if len(private_teams) == 1:
            # The owner is a member of only one team that has private branches
            # enabled.  The case where the private_team is the same as the
            # owner of the branch is caught above where a check is done for a
            # defined policy for the owner.  So if we get to here, the owner
            # of the branch is a member of another team that has private
            # branches enabled, so subscribe the private_team to the branch.
            return (True, private_teams[0])
        elif len(private_teams) > 1:
            # If the owner is a member of multiple teams that specify private
            # branches, then we cannot guess which team should get subscribed
            # automatically, so subscribe no-one.
            return PRIVATE_BRANCH
        elif len(rule_memberships[BranchVisibilityRule.PUBLIC]) > 0:
            # If the owner is not a member of any teams that specify private
            # branches, but is a member of a team that is allowed public
            # branches, then the branch is created as a public branch.
            return PUBLIC_BRANCH
        else:
            membership_teams = rule_memberships.itervalues()
            owner_membership = reduce(lambda x, y: x + y, membership_teams)
            assert len(owner_membership) == 0, (
                'The owner should not be a member of any team that has '
                'a specified team policy.')

        # Need to check the base branch visibility policy since there were no
        # team policies that matches the owner.
        base_visibility_rule = product.getBaseBranchVisibilityRule()
        if base_visibility_rule == BranchVisibilityRule.FORBIDDEN:
            raise BranchCreationForbidden(
                "You cannot create branches for the product %r"
                % product.name)
        elif base_visibility_rule == BranchVisibilityRule.PUBLIC:
            return PUBLIC_BRANCH
        else:
            return PRIVATE_BRANCH

    def new(self, branch_type, name, registrant, owner, product=None,
            url=None, title=None,
            lifecycle_status=BranchLifecycleStatus.DEVELOPMENT,
            summary=None, whiteboard=None, date_created=None,
            branch_format=None, repository_format=None, control_format=None,
            distroseries=None, sourcepackagename=None,
            merge_control_status=BranchMergeControlStatus.NO_QUEUE):
        """See `IBranchSet`."""
        if date_created is None:
            date_created = UTC_NOW

        # Check the policy for the person creating the branch.
        private, implicit_subscription = self._checkVisibilityPolicy(
            registrant, owner, product)

        # Not all code paths that lead to branch creation go via a
        # schema-validated form (e.g. the register_branch XML-RPC call or
        # pushing a new branch to codehosting), so we validate the branch name
        # here to give a nicer error message than 'ERROR: new row for relation
        # "branch" violates check constraint "valid_name"...'.
        IBranch['name'].validate(unicode(name))

        # Run any necessary data massage on the branch URL.
        if url is not None:
            url = IBranch['url'].normalize(url)

        # Make sure that the new branch has a unique name if not a junk
        # branch.
        namespace = get_branch_namespace(
            owner, product=product, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        existing_branch = namespace.getByName(name)
        if existing_branch is not None:
            raise BranchExists(existing_branch)

        branch = Branch(
            registrant=registrant,
            name=name, owner=owner, product=product, url=url,
            title=title, lifecycle_status=lifecycle_status, summary=summary,
            whiteboard=whiteboard, private=private,
            date_created=date_created, branch_type=branch_type,
            date_last_modified=date_created, branch_format=branch_format,
            repository_format=repository_format,
            control_format=control_format, distroseries=distroseries,
            sourcepackagename=sourcepackagename,
            merge_control_status=merge_control_status)

        # Implicit subscriptions are to enable teams to see private branches
        # as soon as they are created.  The subscriptions can be edited at
        # a later date if desired.
        if implicit_subscription is not None:
            branch.subscribe(
                implicit_subscription,
                BranchSubscriptionNotificationLevel.NOEMAIL,
                BranchSubscriptionDiffSize.NODIFF,
                CodeReviewNotificationLevel.NOEMAIL)

        # The owner of the branch should also be automatically subscribed
        # in order for them to get code review notifications.  The implicit
        # owner subscription does not cause email to be sent about attribute
        # changes, just merge proposals and code review comments.
        branch.subscribe(
            branch.owner,
            BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.FULL)

        notify(ObjectCreatedEvent(branch))
        return branch

    def getBranchesToScan(self):
        """See `IBranchSet`"""
        # Return branches where the scanned and mirrored IDs don't match.
        # Branches with a NULL last_mirrored_id have never been
        # successfully mirrored so there is no point scanning them.
        # Branches with a NULL last_scanned_id have not been scanned yet,
        # so are included.

        return Branch.select('''
            Branch.branch_type <> %s AND
            Branch.last_mirrored_id IS NOT NULL AND
            (Branch.last_scanned_id IS NULL OR
             Branch.last_scanned_id <> Branch.last_mirrored_id)
            ''' % quote(BranchType.REMOTE))

    def getRecentlyChangedBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        all_branches = getUtility(IAllBranches)
        branches = all_branches.visibleByUser(
            visible_by_user).withLifecycleStatus(*lifecycle_statuses)
        branches = branches.withBranchType(
            BranchType.HOSTED, BranchType.MIRRORED).scanned().getBranches()
        branches.order_by(
            Desc(Branch.last_scanned), Desc(Branch.id))
        if branch_count is not None:
            branches.config(limit=branch_count)
        return branches

    def getRecentlyImportedBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        all_branches = getUtility(IAllBranches)
        branches = all_branches.visibleByUser(
            visible_by_user).withLifecycleStatus(*lifecycle_statuses)
        branches = branches.withBranchType(
            BranchType.IMPORTED).scanned().getBranches()
        branches.order_by(
            Desc(Branch.last_scanned), Desc(Branch.id))
        if branch_count is not None:
            branches.config(limit=branch_count)
        return branches

    def getRecentlyRegisteredBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        all_branches = getUtility(IAllBranches)
        branches = all_branches.withLifecycleStatus(
            *lifecycle_statuses).visibleByUser(visible_by_user).getBranches()
        branches.order_by(
            Desc(Branch.date_created), Desc(Branch.id))
        if branch_count is not None:
            branches.config(limit=branch_count)
        return branches

    @staticmethod
    def _getBranchVisibilitySubQuery(visible_by_user):
        # Logged in people can see public branches (first part of the union),
        # branches owned by teams they are in (second part),
        # and all branches they are subscribed to (third part).
        return """
            SELECT Branch.id
            FROM Branch
            WHERE
                NOT Branch.private

            UNION

            SELECT Branch.id
            FROM Branch, TeamParticipation
            WHERE
                Branch.owner = TeamParticipation.team
            AND TeamParticipation.person = %d

            UNION

            SELECT Branch.id
            FROM Branch, BranchSubscription, TeamParticipation
            WHERE
                Branch.private
            AND Branch.id = BranchSubscription.branch
            AND BranchSubscription.person = TeamParticipation.team
            AND TeamParticipation.person = %d
            """ % (visible_by_user.id, visible_by_user.id)

    def _generateBranchClause(self, query, visible_by_user):
        # If the visible_by_user is a member of the Launchpad admins team,
        # then don't filter the results at all.
        if (LAUNCHPAD_SERVICES == visible_by_user or
            user_has_special_branch_access(visible_by_user)):
            return query

        if len(query) > 0:
            query = '%s AND ' % query

        # Non logged in people can only see public branches.
        if visible_by_user is None:
            return '%sNOT Branch.private' % query

        clause = (
            '%sBranch.id IN (%s)'
            % (query, self._getBranchVisibilitySubQuery(visible_by_user)))

        return clause

    def getLatestBranchesForProduct(self, product, quantity,
                                    visible_by_user=None):
        """See `IBranchSet`."""
        assert product is not None, "Must have a valid product."
        all_branches = getUtility(IAllBranches)
        latest = all_branches.visibleByUser(visible_by_user).inProduct(
            product).withLifecycleStatus(*DEFAULT_BRANCH_STATUS_IN_LISTING)
        latest_branches = latest.getBranches().order_by(
            Desc(Branch.date_created), Desc(Branch.id))
        latest_branches.config(limit=quantity)
        return latest_branches

    def getPullQueue(self, branch_type):
        """See `IBranchSet`."""
        return Branch.select(
            AND(Branch.q.branch_type == branch_type,
                Branch.q.next_mirror_time <= UTC_NOW),
            prejoins=['owner', 'product'], orderBy='next_mirror_time')

    def getTargetBranchesForUsersMergeProposals(self, user, product):
        """See `IBranchSet`."""
        # XXX: JonathanLange 2008-11-27 spec=package-branches: Why the hell is
        # this using SQL? In any case, we want to change this to allow source
        # packages.
        return Branch.select("""
            BranchMergeProposal.target_branch = Branch.id
            AND BranchMergeProposal.registrant = %s
            AND Branch.product = %s
            """ % sqlvalues(user, product),
            clauseTables=['BranchMergeProposal'],
            orderBy=['owner', 'name'], distinct=True)


class BranchCloud:
    """See `IBranchCloud`."""

    def getProductsWithInfo(self, num_products=None, store_flavor=None):
        """See `IBranchCloud`."""
        # Circular imports are fun.
        from canonical.launchpad.database.product import Product
        # It doesn't matter if this query is even a whole day out of date, so
        # use the slave store by default.
        if store_flavor is None:
            store_flavor = SLAVE_FLAVOR
        store = getUtility(IStoreSelector).get(MAIN_STORE, store_flavor)
        # Get all products, the count of all hosted & mirrored branches and
        # the last revision date.
        result = store.find(
            (Product, Count(Branch.id), Max(Revision.revision_date)),
            Branch.private == False,
            Branch.product == Product.id,
            Or(Branch.branch_type == BranchType.HOSTED,
               Branch.branch_type == BranchType.MIRRORED),
            Branch.last_scanned_id == Revision.revision_id).group_by(Product)
        result = result.order_by(Desc(Count(Branch.id)))
        if num_products:
            result.config(limit=num_products)
        # XXX: JonathanLange 2009-02-10: The revision date in the result set
        # isn't timezone-aware. Not sure why this is. Doesn't matter too much
        # for the purposes of cloud calculation though.
        return result
