# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
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

from storm.expr import And, Count, Desc, Max, NamedFunc, Or, Select
from storm.store import Store
from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin)

from canonical.config import config
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.sqlbase import (
    cursor, quote, SQLBase, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad import _
from lp.services.job.model.job import Job
from canonical.launchpad.mailnotification import NotificationRecipientSet
from canonical.launchpad.webapp import urlappend
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)

from lp.code.model.branchmergeproposal import (
     BranchMergeProposal)
from lp.code.model.branchrevision import BranchRevision
from lp.code.model.branchsubscription import BranchSubscription
from lp.code.model.revision import Revision
from lp.code.event.branchmergeproposal import NewBranchMergeProposalEvent
from lp.code.interfaces.branch import (
    bazaar_identity, BranchCannotBePrivate, BranchCannotBePublic,
    BranchFormat, BranchLifecycleStatus, BranchMergeControlStatus,
    BranchType, BranchTypeError, CannotDeleteBranch,
    ControlFormat, DEFAULT_BRANCH_STATUS_IN_LISTING, IBranch,
    IBranchNavigationMenu, IBranchSet, RepositoryFormat)
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branchmergeproposal import (
     BRANCH_MERGE_PROPOSAL_FINAL_STATES, BranchMergeProposalExists,
     BranchMergeProposalStatus, InvalidBranchMergeProposal)
from lp.code.interfaces.branchnamespace import IBranchNamespacePolicy
from lp.code.interfaces.branchpuller import IBranchPuller
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.seriessourcepackagebranch import (
    IFindOfficialBranchLinks)
from lp.registry.interfaces.person import (
    validate_person_not_private_membership, validate_public_person)


class Branch(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranch, IBranchNavigationMenu)
    _table = 'Branch'

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

    def setPrivate(self, private):
        """See `IBranch`."""
        if private == self.private:
            return
        policy = IBranchNamespacePolicy(self.namespace)

        if private and not policy.canBranchesBePrivate():
            raise BranchCannotBePrivate()
        if not private and not policy.canBranchesBePublic():
            raise BranchCannotBePublic()
        self.private = private

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_person_not_private_membership, notNull=True)
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
        from lp.registry.model.sourcepackage import SourcePackage
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

    def isBranchMergeable(self, target_branch):
        """See `IBranch`."""
        # In some imaginary time we may actually check to see if this branch
        # and the target branch have common ancestry.
        return self.target.areBranchesMergeable(target_branch.target)

    def addLandingTarget(self, registrant, target_branch,
                         dependent_branch=None, whiteboard=None,
                         date_created=None, needs_review=False,
                         initial_comment=None, review_requests=None,
                         review_diff=None):
        """See `IBranch`."""
        if not self.target.supports_merge_proposals:
            raise InvalidBranchMergeProposal(
                '%s branches do not support merge proposals.'
                % self.target.displayname)
        if self == target_branch:
            raise InvalidBranchMergeProposal(
                'Source and target branches must be different.')
        if not target_branch.isBranchMergeable(self):
            raise InvalidBranchMergeProposal(
                '%s is not mergeable into %s' % (
                    self.displayname, target_branch.displayname))
        if dependent_branch is not None:
            if not self.isBranchMergeable(dependent_branch):
                raise InvalidBranchMergeProposal(
                    '%s is not mergeable into %s' % (
                        dependent_branch.displayname, self.displayname))
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
                % (self.displayname, target_branch.displayname))

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
        # XXX: JonathanLange 2009-03-19 spec=package-branches bug=345740: This
        # should not dispatch on product is None.
        if self.product is not None:
            series_branch = self.product.development_focus.branch
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
        return self.bzr_identity

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
        from lp.code.model.codeimport import CodeImportSet
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

        series_set = getUtility(IFindOfficialBranchLinks)
        alteration_operations.extend(
            map(ClearOfficialPackageBranch, series_set.findForBranch(self)))
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
        from lp.registry.model.productseries import ProductSeries
        return Store.of(self).find(
            ProductSeries,
            ProductSeries.branch == self)

    # subscriptions
    def subscribe(self, person, notification_level, max_diff_lines,
                  code_review_level):
        """See `IBranch`."""
        # If the person is already subscribed, update the subscription with
        # the specified notification details.
        subscription = self.getSubscription(person)
        if subscription is None:
            subscription = BranchSubscription(
                branch=self, person=person,
                notification_level=notification_level,
                max_diff_lines=max_diff_lines, review_level=code_review_level)
            Store.of(subscription).flush()
        else:
            subscription.notification_level = notification_level
            subscription.max_diff_lines = max_diff_lines
            subscription.review_level = code_review_level
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
        # XXX: JonathanLange 2009-05-07 bug=373026: This is only used by real
        # code to determine whether there are any subscribers at the given
        # notification levels. The only code that cares about the actual
        # object is in a test:
        # test_only_nodiff_subscribers_means_no_diff_generated.
        store = Store.of(self)
        return store.find(
            BranchSubscription,
            BranchSubscription.branch == self,
            BranchSubscription.notification_level.is_in(notification_levels))

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

    @property
    def pending_writes(self):
        """See `IBranch`.

        A branch has pending writes if it has just been pushed to, if it has
        been mirrored and not yet scanned or if it is in the middle of being
        mirrored.
        """
        new_data_pushed = (
             self.branch_type in (BranchType.HOSTED, BranchType.IMPORTED)
             and self.next_mirror_time is not None)
        pulled_but_not_scanned = self.last_mirrored_id != self.last_scanned_id
        pull_in_progress = (
            self.last_mirror_attempt is not None
            and (self.last_mirrored is None
                 or self.last_mirror_attempt > self.last_mirrored))
        return (
            new_data_pushed or pulled_but_not_scanned or pull_in_progress)

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
            increment = getUtility(IBranchPuller).MIRROR_TIME_INCREMENT
            self.next_mirror_time = (
                datetime.now(pytz.timezone('UTC')) + increment)
        self.last_mirrored_id = last_revision_id

    def mirrorFailed(self, reason):
        """See `IBranch`."""
        if self.branch_type == BranchType.REMOTE:
            raise BranchTypeError(self.unique_name)
        self.mirror_failures += 1
        self.mirror_status_message = reason
        branch_puller = getUtility(IBranchPuller)
        max_failures = branch_puller.MAXIMUM_MIRROR_FAILURES
        increment = branch_puller.MIRROR_TIME_INCREMENT
        if (self.branch_type == BranchType.MIRRORED
            and self.mirror_failures < max_failures):
            self.next_mirror_time = (
                datetime.now(pytz.timezone('UTC'))
                + increment * 2 ** (self.mirror_failures - 1))

    def destroySelf(self, break_references=False):
        """See `IBranch`."""
        from lp.code.model.branchjob import BranchJob
        if break_references:
            self._breakReferences()
        if not self.canBeDeleted():
            raise CannotDeleteBranch(
                "Cannot delete branch: %s" % self.unique_name)
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

    def commitsForDays(self, since):
        """See `IBranch`."""
        class DateTrunc(NamedFunc):
            name = "date_trunc"
        results = Store.of(self).find(
            (DateTrunc('day', Revision.revision_date), Count(Revision.id)),
            Revision.id == BranchRevision.revisionID,
            Revision.revision_date > since,
            BranchRevision.branch == self)
        results = results.group_by(
            DateTrunc('day', Revision.revision_date))
        return sorted(results)


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
        if self.affected_object.branch == self.branch:
            self.affected_object.branch = None
        self.affected_object.syncUpdate()


class ClearOfficialPackageBranch(DeletionOperation):
    """Deletion operation that clears an official package branch."""

    def __init__(self, sspb):
        DeletionOperation.__init__(
            self, sspb, _('Branch is officially linked to a source package.'))

    def __call__(self):
        package = self.affected_object.sourcepackage
        pocket = self.affected_object.pocket
        package.setBranch(pocket, None, None)


class DeleteCodeImport(DeletionOperation):
    """Deletion operation that deletes a branch's import."""

    def __init__(self, code_import):
        DeletionOperation.__init__(
            self, code_import, _( 'This is the import data for this branch.'))

    def __call__(self):
        from lp.code.model.codeimport import CodeImportSet
        CodeImportSet().delete(self.affected_object)


class BranchSet:
    """The set of all branches."""

    implements(IBranchSet)

    def countBranchesWithAssociatedBugs(self):
        """See `IBranchSet`."""
        return Branch.select(
            'NOT Branch.private AND Branch.id = BugBranch.branch',
            clauseTables=['BugBranch'],
            distinct=True).count()

    def getRecentlyChangedBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        all_branches = getUtility(IAllBranches)
        branches = all_branches.visibleByUser(
            visible_by_user).withLifecycleStatus(*lifecycle_statuses)
        branches = branches.withBranchType(
            BranchType.HOSTED, BranchType.MIRRORED).scanned().getBranches(
            join_owner=False, join_product=False)
        branches.order_by(
            Desc(Branch.date_last_modified), Desc(Branch.id))
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
            BranchType.IMPORTED).scanned().getBranches(
            join_owner=False, join_product=False)
        branches.order_by(
            Desc(Branch.date_last_modified), Desc(Branch.id))
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
            *lifecycle_statuses).visibleByUser(visible_by_user).getBranches(
            join_owner=False, join_product=False)
        branches.order_by(
            Desc(Branch.date_created), Desc(Branch.id))
        if branch_count is not None:
            branches.config(limit=branch_count)
        return branches

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


class BranchCloud:
    """See `IBranchCloud`."""

    def getProductsWithInfo(self, num_products=None, store_flavor=None):
        """See `IBranchCloud`."""
        # Circular imports are fun.
        from lp.registry.model.product import Product
        # It doesn't matter if this query is even a whole day out of date, so
        # use the slave store by default.
        if store_flavor is None:
            store_flavor = SLAVE_FLAVOR
        store = getUtility(IStoreSelector).get(MAIN_STORE, store_flavor)
        # Get all products, the count of all hosted & mirrored branches and
        # the last revision date.
        result = store.find(
            (Product.name, Count(Branch.id), Max(Revision.revision_date)),
            Branch.private == False,
            Branch.product == Product.id,
            Or(Branch.branch_type == BranchType.HOSTED,
               Branch.branch_type == BranchType.MIRRORED),
            Branch.last_scanned_id == Revision.revision_id)
        result = result.group_by(Product.name)
        result = result.order_by(Desc(Count(Branch.id)))
        if num_products:
            result.config(limit=num_products)
        # XXX: JonathanLange 2009-02-10: The revision date in the result set
        # isn't timezone-aware. Not sure why this is. Doesn't matter too much
        # for the purposes of cloud calculation though.
        return result
