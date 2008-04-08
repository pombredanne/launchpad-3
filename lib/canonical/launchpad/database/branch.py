# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212,W0141

__metaclass__ = type
__all__ = [
    'Branch',
    'BranchSet',
    'BranchWithSortKeys',
    'DEFAULT_BRANCH_LISTING_SORT',
    ]

from datetime import datetime, timedelta
import re
import os

import pytz

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin,
    SQLObjectNotFound)
from sqlobject.sqlbuilder import AND

from canonical.codehosting import branch_id_to_path
from canonical.config import config
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.sqlbase import (
    cursor, quote, SQLBase, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES,
    BranchCreationForbidden, BranchCreationNoTeamOwnedJunkBranches,
    BranchCreatorNotMemberOfOwnerTeam, BranchCreatorNotOwner,
    BranchLifecycleStatus, BranchListingSort, BranchMergeProposalStatus,
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel, BranchType, BranchTypeError,
    BranchVisibilityRule, CannotDeleteBranch, CodeReviewNotificationLevel,
    DEFAULT_BRANCH_STATUS_IN_LISTING, IBranch, IBranchSet,
    ILaunchpadCelebrities, InvalidBranchMergeProposal,
    MAXIMUM_MIRROR_FAILURES, MIRROR_TIME_INCREMENT, NotFoundError)
from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal)
from canonical.launchpad.database.branchrevision import BranchRevision
from canonical.launchpad.database.branchsubscription import BranchSubscription
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.database.revision import Revision
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.mailnotification import NotificationRecipientSet
from canonical.launchpad.webapp import urlappend


class Branch(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranch)
    _table = 'Branch'
    _defaultOrder = ['product', '-lifecycle_status', 'author', 'name']

    branch_type = EnumCol(enum=BranchType, notNull=True)

    name = StringCol(notNull=False)
    title = StringCol(notNull=False)
    summary = StringCol(notNull=False)
    url = StringCol(dbName='url')
    whiteboard = StringCol(default=None)
    mirror_status_message = StringCol(default=None)

    private = BoolCol(default=False, notNull=True)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    author = ForeignKey(
        dbName='author', foreignKey='Person',
        validator=public_person_validator, default=None)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person',
        validator=public_person_validator, default=None)

    product = ForeignKey(dbName='product', foreignKey='Product', default=None)

    lifecycle_status = EnumCol(
        enum=BranchLifecycleStatus, notNull=True,
        default=BranchLifecycleStatus.NEW)

    last_mirrored = UtcDateTimeCol(default=None)
    last_mirrored_id = StringCol(default=None)
    last_mirror_attempt = UtcDateTimeCol(default=None)
    mirror_failures = IntCol(default=0, notNull=True)
    pull_disabled = BoolCol(default=False, notNull=True)
    next_mirror_time = UtcDateTimeCol(default=None)

    last_scanned = UtcDateTimeCol(default=None)
    last_scanned_id = StringCol(default=None)
    revision_count = IntCol(default=DEFAULT, notNull=True)

    def __repr__(self):
        return '<Branch %r (%d)>' % (self.unique_name, self.id)

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
                         date_created=None):
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
            raise InvalidBranchMergeProposal(
                'There is already a branch merge proposal registered for '
                'branch %s to land on %s that is still active.'
                % (self.unique_name, target_branch.unique_name))

        if date_created is None:
            date_created = UTC_NOW
        # Update the last_modified_date of the source and target branches to
        # be the date_created for the merge proposal.
        self.date_last_modified = date_created
        target_branch.date_last_modified = date_created

        bmp = BranchMergeProposal(
            registrant=registrant, source_branch=self,
            target_branch=target_branch, dependent_branch=dependent_branch,
            whiteboard=whiteboard, date_created=date_created)
        notify(SQLObjectCreatedEvent(bmp))
        return bmp

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
        return self.revision_count > 0 and not self.private

    def _getNameDict(self, person):
        """Return a simple dict with the person name or placeholder."""
        if person is not None:
            name = person.name
        else:
            name = "<name>"
        return {'user': name}

    def getBzrUploadURL(self, person=None):
        """See `IBranch`."""
        root = config.codehosting.smartserver_root % self._getNameDict(person)
        return root + self.unique_name

    def getBzrDownloadURL(self, person=None):
        """See `IBranch`."""
        if self.private:
            root = config.codehosting.smartserver_root
        else:
            root = config.codehosting.supermirror_root
        root = root % self._getNameDict(person)
        return root + self.unique_name

    @property
    def related_bugs(self):
        """See `IBranch`."""
        return [bug_branch.bug for bug_branch in self.bug_branches]

    @property
    def related_bug_tasks(self):
        """See `IBranch`."""
        tasks = []
        for bug in self.related_bugs:
            task = bug.getBugTask(self.product)
            if task is None:
                # Just choose the first task for the bug.
                task = bug.bugtasks[0]
            tasks.append(task)
        return tasks

    @property
    def warehouse_url(self):
        """See `IBranch`."""
        root = config.supermirror.warehouse_root_url
        return "%s%08x" % (root, self.id)

    @property
    def product_name(self):
        """See `IBranch`."""
        if self.product is None:
            return '+junk'
        return self.product.name

    @property
    def unique_name(self):
        """See `IBranch`."""
        return u'~%s/%s/%s' % (self.owner.name, self.product_name, self.name)

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

    @property
    def sort_key(self):
        """See `IBranch`."""
        if self.product is None:
            product = None
        else:
            product = self.product.name
        if self.author is None:
            author = None
        else:
            author = self.author.browsername
        status = self.lifecycle_status.sortkey
        name = self.name
        owner = self.owner.name
        return (product, status, author, name, owner)

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
        if (len(self.deletionRequirements()) != 0):
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
                    ' proposal.'), merge_proposal.destroySelf))
        # Cannot use self.landing_candidates, because it ignores merged
        # merge proposals.
        for merge_proposal in BranchMergeProposal.selectBy(
            target_branch=self):
            deletion_operations.append(
                DeletionCallable(merge_proposal,
                    _('This branch is the target branch of this merge'
                    ' proposal.'), merge_proposal.destroySelf))
        for merge_proposal in BranchMergeProposal.selectBy(
            dependent_branch=self):
            alteration_operations.append(ClearDependentBranch(merge_proposal))

        for subscription in self.subscriptions:
            deletion_operations.append(
                DeletionCallable(subscription,
                    _('This is a subscription to this branch.'),
                    subscription.destroySelf))
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
        return ProductSeries.select("""
            ProductSeries.user_branch = %s OR
            ProductSeries.import_branch = %s
            """ % sqlvalues(self, self))

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
            "BranchSubscription.branch = Branch.id "
            "AND BranchSubscription.notification_level IN (%s)"
            % ', '.join(sqlvalues(*notification_levels)),
            clauseTables=['Branch'])

    def hasSubscription(self, person):
        """See `IBranch`."""
        return self.getSubscription(person) is not None

    def unsubscribe(self, person):
        """See `IBranch`."""
        subscription = self.getSubscription(person)
        assert subscription is not None, "User is not subscribed."
        BranchSubscription.delete(subscription.id)

    def getBranchRevision(self, sequence):
        """See `IBranch`."""
        assert sequence is not None, \
               "Only use this to fetch revisions from mainline history."
        return BranchRevision.selectOneBy(branch=self, sequence=sequence)

    def getBranchRevisionByRevisionId(self, revision_id):
        """See `IBranch`."""
        revision = Revision.selectOneBy(revision_id=revision_id)
        return BranchRevision.selectOneBy(branch=self, revision=revision)

    def createBranchRevision(self, sequence, revision):
        """See `IBranch`."""
        return BranchRevision(
            branch=self, sequence=sequence, revision=revision)

    def getTipRevision(self):
        """See `IBranch`."""
        tip_revision_id = self.last_scanned_id
        if tip_revision_id is None:
            return None
        return Revision.selectOneBy(revision_id=tip_revision_id)

    def updateScannedDetails(self, revision_id, revision_count):
        """See `IBranch`."""
        self.date_last_modified = UTC_NOW
        self.last_scanned = UTC_NOW
        self.last_scanned_id = revision_id
        self.revision_count = revision_count

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
            # This is a push branch, hosted on the supermirror
            # (pushed there by users via SFTP).
            prefix = config.codehosting.branches_root
            return os.path.join(prefix, branch_id_to_path(self.id))
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
        self.syncUpdate()

    def mirrorComplete(self, last_revision_id):
        """See `IBranch`."""
        if self.branch_type == BranchType.REMOTE:
            raise BranchTypeError(self.unique_name)
        assert self.last_mirror_attempt != None, (
            "startMirroring must be called before mirrorComplete.")
        self.last_mirrored = self.last_mirror_attempt
        self.mirror_failures = 0
        self.mirror_status_message = None
        if (self.next_mirror_time != None
            and self.last_mirror_attempt > self.next_mirror_time):
            # No mirror was requested since we started mirroring.
            if self.branch_type == BranchType.MIRRORED:
                self.next_mirror_time = (
                    datetime.now(pytz.timezone('UTC')) +
                    MIRROR_TIME_INCREMENT)
            else:
                self.next_mirror_time = None
        self.last_mirrored_id = last_revision_id
        self.syncUpdate()

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
        else:
            self.next_mirror_time = None
        self.syncUpdate()

    def destroySelf(self, break_references=False):
        """See `IBranch`."""
        if break_references:
            self._breakReferences()
        if self.canBeDeleted():
            # Delete any branch revisions.
            branch_ancestry = BranchRevision.selectBy(branch=self)
            for branch_revision in branch_ancestry:
                BranchRevision.delete(branch_revision.id)
            # Now delete the branch itself.
            SQLBase.destroySelf(self)
        else:
            raise CannotDeleteBranch(
                "Cannot delete branch: %s" % self.unique_name)


class BranchWithSortKeys(Branch):
    """A hack to allow the sorting of Branch queries by human-meaningful keys.

    The view BranchWithSortKeys has all of the columns of Branch, with:

     - product.name joined as product_name
     - author.displayname joined as author_name
     - owner.displayname joined as owner_name

    These columns are never accessed at the Python level so we don't define
    them in this class.

    If we could get SQLObject to generate LEFT OUTER JOINs nicely, all this
    wouldn't be necessary.

    XXX: MichaelHudson 2007-10-12 bug=154016: Get rid of this hack
    when we've converted over to using Storm.
    """

    @classmethod
    def select(cls, query, clauseTables=None, orderBy=None):
        """Wrap a query that refers to Branch to refer to BranchWithSortKeys.

        All the queries carefully and generically created in this file refer
        to the Branch table.  To be able to query the BranchWithSortKeys view
        instead, we ask the view for the rows with the same ids as the
        branches returned by the generated query.
        """
        tables = ['Branch']
        if clauseTables is not None:
            tables.extend(clauseTables)
        query = """BranchWithSortKeys.id IN
                   (SELECT Branch.id FROM %s WHERE %s)""" % (
                ', '.join(tables), query)
        return super(BranchWithSortKeys, cls).select(query, orderBy=orderBy)


LISTING_SORT_TO_COLUMN = {
    BranchListingSort.PRODUCT: 'product_name',
    BranchListingSort.LIFECYCLE: '-lifecycle_status',
    BranchListingSort.AUTHOR: 'author_name',
    BranchListingSort.NAME: 'name',
    BranchListingSort.REGISTRANT: 'owner_name',
    BranchListingSort.MOST_RECENTLY_CHANGED_FIRST: '-last_scanned',
    BranchListingSort.LEAST_RECENTLY_CHANGED_FIRST: 'last_scanned',
    BranchListingSort.NEWEST_FIRST: '-date_created',
    BranchListingSort.OLDEST_FIRST: 'date_created',
    }


DEFAULT_BRANCH_LISTING_SORT = [
    'product_name', '-lifecycle_status', 'author_name', 'name']


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

    def get(self, branch_id, default=None):
        """See `IBranchSet`."""
        try:
            return Branch.get(branch_id)
        except SQLObjectNotFound:
            return default

    def getBranch(self, owner, product, branch_name):
        """See `IBranchSet`."""
        return Branch.selectOneBy(
            owner=owner, product=product, name=branch_name)

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
                raise BranchCreationNoTeamOwnedJunkBranches(
                    "Cannot create team-owned junk branches.")
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

    def new(self, branch_type, name, creator, owner, product,
            url, title=None,
            lifecycle_status=BranchLifecycleStatus.NEW, author=None,
            summary=None, whiteboard=None, date_created=None):
        """See `IBranchSet`."""
        if date_created is None:
            date_created = UTC_NOW

        # Check the policy for the person creating the branch.
        private, implicit_subscription = self._checkVisibilityPolicy(
            creator, owner, product)

        # Not all code paths that lead to branch creation go via a
        # schema-validated form (e.g. the register_branch XML-RPC call or
        # pushing a new branch to the supermirror), so we validate the branch
        # name here to give a nicer error message than 'ERROR: new row for
        # relation "branch" violates check constraint "valid_name"...'.
        IBranch['name'].validate(unicode(name))

        branch = Branch(
            registrant=creator,
            name=name, owner=owner, author=author, product=product, url=url,
            title=title, lifecycle_status=lifecycle_status, summary=summary,
            whiteboard=whiteboard, private=private,
            date_created=date_created, branch_type=branch_type,
            date_last_modified=date_created)

        # Implicit subscriptions are to enable teams to see private branches
        # as soon as they are created.  The subscriptions can be edited at
        # a later date if desired.
        if implicit_subscription is not None:
            branch.subscribe(
                implicit_subscription,
                BranchSubscriptionNotificationLevel.NOEMAIL,
                BranchSubscriptionDiffSize.NODIFF,
                CodeReviewNotificationLevel.NOEMAIL)

        notify(SQLObjectCreatedEvent(branch))
        return branch

    def getByUrl(self, url, default=None):
        """See `IBranchSet`."""
        assert not url.endswith('/')
        prefix = config.codehosting.supermirror_root
        if url.startswith(prefix):
            branch = self.getByUniqueName(url[len(prefix):])
        else:
            branch = Branch.selectOneBy(url=url)
        if branch is None:
            return default
        else:
            return branch

    def getByUniqueName(self, unique_name, default=None):
        """Find a branch by its ~owner/product/name unique name."""
        # import locally to avoid circular imports
        match = re.match('^~([^/]+)/([^/]+)/([^/]+)$', unique_name)
        if match is None:
            return default
        owner_name, product_name, branch_name = match.groups()
        if product_name == '+junk':
            query = ("Branch.owner = Person.id"
                     + " AND Branch.product IS NULL"
                     + " AND Person.name = " + quote(owner_name)
                     + " AND Branch.name = " + quote(branch_name))
            tables = ['Person']
        else:
            query = ("Branch.owner = Person.id"
                     + " AND Branch.product = Product.id"
                     + " AND Person.name = " + quote(owner_name)
                     + " AND Product.name = " + quote(product_name)
                     + " AND Branch.name = " + quote(branch_name))
            tables = ['Person', 'Product']
        branch = Branch.selectOne(query, clauseTables=tables)
        if branch is None:
            return default
        else:
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

    def getProductDevelopmentBranches(self, products):
        """See `IBranchSet`."""
        product_ids = [product.id for product in products]
        query = Branch.select('''
            (Branch.id = ProductSeries.import_branch OR
            Branch.id = ProductSeries.user_branch) AND
            ProductSeries.id = Product.development_focus AND
            Branch.product IN %s''' % sqlvalues(product_ids),
            clauseTables = ['Product', 'ProductSeries'])
        return query.prejoin(['author'])

    def getActiveUserBranchSummaryForProducts(self, products):
        """See `IBranchSet`."""
        product_ids = [product.id for product in products]
        if not product_ids:
            return []
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        lifecycle_clause = self._lifecycleClause(
            DEFAULT_BRANCH_STATUS_IN_LISTING)
        cur = cursor()
        cur.execute("""
            SELECT
                Branch.product, COUNT(Branch.id), MAX(Revision.revision_date)
            FROM Branch
            LEFT OUTER JOIN Revision
            ON Branch.last_scanned_id = Revision.revision_id
            WHERE Branch.product in %s
            AND Branch.owner <> %d %s
            GROUP BY Product
            """ % (quote(product_ids), vcs_imports.id, lifecycle_clause))
        result = {}
        product_map = dict([(product.id, product) for product in products])
        for product_id, branch_count, last_commit in cur.fetchall():
            product = product_map[product_id]
            result[product] = {'branch_count' : branch_count,
                               'last_commit' : last_commit}
        return result

    def getRecentlyChangedBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        query = ('''
            Branch.branch_type <> %s AND
            Branch.last_scanned IS NOT NULL %s
            '''
            % (quote(BranchType.IMPORTED), lifecycle_clause))
        results = Branch.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=['-last_scanned', '-id'],
            prejoins=['author', 'product'])
        if branch_count is not None:
            results = results.limit(branch_count)
        return results

    def getRecentlyImportedBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        query = ('''
            Branch.branch_type = %s AND
            Branch.last_scanned IS NOT NULL %s
            '''
            % (quote(BranchType.IMPORTED), lifecycle_clause))
        results = Branch.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=['-last_scanned', '-id'],
            prejoins=['author', 'product'])
        if branch_count is not None:
            results = results.limit(branch_count)
        return results

    def getRecentlyRegisteredBranches(
        self, branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """See `IBranchSet`."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        # Since the lifecycle_clause may or may not contain anything,
        # we need something that is valid if the lifecycle clause starts
        # with 'AND', so we choose true.
        query = 'true %s' % lifecycle_clause
        results = Branch.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=['-date_created', '-id'],
            prejoins=['author', 'product'])
        if branch_count is not None:
            results = results.limit(branch_count)
        return results

    def _generateBranchClause(self, query, visible_by_user):
        # If the visible_by_user is a member of the Launchpad admins team,
        # then don't filter the results at all.
        lp_admins = getUtility(ILaunchpadCelebrities).admin
        if visible_by_user is not None and visible_by_user.inTeam(lp_admins):
            return query

        if len(query) > 0:
            query = '%s AND ' % query

        # Non logged in people can only see public branches.
        if visible_by_user is None:
            return '%sNOT Branch.private' % query

        # Logged in people can see public branches (first part of the union),
        # branches owned by teams they are in (second part),
        # and all branches they are subscribed to (third part).
        clause = ('''
            %sBranch.id IN (
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
                AND TeamParticipation.person = %d)
            '''
            % (query, visible_by_user.id, visible_by_user.id))

        return clause

    def _lifecycleClause(self, lifecycle_statuses):
        lifecycle_clause = ''
        if lifecycle_statuses:
            lifecycle_clause = (
                ' AND Branch.lifecycle_status in %s' %
                quote(lifecycle_statuses))
        return lifecycle_clause

    def _dormantClause(self, hide_dormant):
        dormant_clause = ''
        if hide_dormant:
            dormant_days = timedelta(
                days=config.launchpad.branch_dormant_days)
            last_date = datetime.utcnow() - dormant_days
            dormant_clause = (
                ' AND Branch.date_last_modified > %s' %
                quote(last_date))
        return dormant_clause

    @staticmethod
    def _listingSortToOrderBy(sort_by):
        """Compute a value to pass as orderBy to BranchWithSortKeys.select().

        :param sort_by: an item from the BranchListingSort enumeration.
        """
        order_by = DEFAULT_BRANCH_LISTING_SORT[:]
        if sort_by is None:
            return order_by
        else:
            column = LISTING_SORT_TO_COLUMN[sort_by]
            if column.startswith('-'):
                variant_column = column[1:]
            else:
                variant_column = '-' + column
            if column in order_by:
                order_by.remove(column)
            if variant_column in order_by:
                order_by.remove(variant_column)
            order_by.insert(0, column)
            return order_by

    def getBranchesForPerson(self, person, lifecycle_statuses=None,
                             visible_by_user=None, sort_by=None,
                             hide_dormant=False):
        """See `IBranchSet`."""
        query_params = {
            'person': person.id,
            'lifecycle_clause': self._lifecycleClause(lifecycle_statuses),
            'dormant_clause': self._dormantClause(hide_dormant)
            }
        query = ('''
            Branch.id in (
                SELECT Branch.id
                FROM Branch, BranchSubscription
                WHERE
                    Branch.id = BranchSubscription.branch
                AND BranchSubscription.person = %(person)s

                UNION

                SELECT Branch.id
                FROM Branch
                WHERE
                    Branch.owner = %(person)s
                OR Branch.registrant = %(person)s
                )
            %(lifecycle_clause)s
            %(dormant_clause)s
            '''
            % query_params)

        return BranchWithSortKeys.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=self._listingSortToOrderBy(sort_by))

    def getBranchesOwnedByPerson(self, person, lifecycle_statuses=None,
                                 visible_by_user=None, sort_by=None,
                                 hide_dormant=False):
        """See `IBranchSet`."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        dormant_clause = self._dormantClause(hide_dormant)
        query = 'Branch.owner = %s %s %s' % (
            person.id, lifecycle_clause, dormant_clause)
        return BranchWithSortKeys.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=self._listingSortToOrderBy(sort_by))

    def getBranchesRegisteredByPerson(self, person, lifecycle_statuses=None,
                                      visible_by_user=None, sort_by=None,
                                      hide_dormant=False):
        """See `IBranchSet`."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        dormant_clause = self._dormantClause(hide_dormant)
        query = 'Branch.registrant = %s %s %s' % (
            person.id, lifecycle_clause, dormant_clause)
        return BranchWithSortKeys.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=self._listingSortToOrderBy(sort_by))

    def getBranchesSubscribedByPerson(self, person, lifecycle_statuses=None,
                                      visible_by_user=None, sort_by=None,
                                      hide_dormant=False):
        """See `IBranchSet`."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        dormant_clause = self._dormantClause(hide_dormant)
        query = ('''
            Branch.id = BranchSubscription.branch
            AND BranchSubscription.person = %s %s %s
            '''
            % (person.id, lifecycle_clause, dormant_clause))
        return BranchWithSortKeys.select(
            self._generateBranchClause(query, visible_by_user),
            clauseTables=['BranchSubscription'],
            orderBy=self._listingSortToOrderBy(sort_by))

    def getBranchesForProduct(self, product, lifecycle_statuses=None,
                              visible_by_user=None, sort_by=None,
                              hide_dormant=False):
        """See `IBranchSet`."""
        assert product is not None, "Must have a valid product."
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        dormant_clause = self._dormantClause(hide_dormant)

        query = 'Branch.product = %s %s %s' % (
            product.id, lifecycle_clause, dormant_clause)

        return BranchWithSortKeys.select(
            self._generateBranchClause(query, visible_by_user),
            orderBy=self._listingSortToOrderBy(sort_by))

    def getBranchesForProject(self, project, lifecycle_statuses=None,
                              visible_by_user=None, sort_by=None,
                              hide_dormant=False):
        """See `IBranchSet`."""
        assert project is not None, "Must have a valid project."
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)
        dormant_clause = self._dormantClause(hide_dormant)

        query = ('''
            Branch.product = Product.id AND
            Product.project = %s %s %s
            '''
            % (project.id, lifecycle_clause, dormant_clause))

        return BranchWithSortKeys.select(
            self._generateBranchClause(query, visible_by_user),
            clauseTables=['Product'],
            orderBy=self._listingSortToOrderBy(sort_by))

    def getHostedBranchesForPerson(self, person):
        """See `IBranchSet`."""
        branches = Branch.select("""
            Branch.branch_type = %s
            AND Branch.owner IN (
            SELECT TeamParticipation.team
            FROM TeamParticipation
            WHERE TeamParticipation.person = %s)
            """ % sqlvalues(BranchType.HOSTED, person))
        return branches

    def getLatestBranchesForProduct(self, product, quantity,
                                    visible_by_user=None):
        """See `IBranchSet`."""
        assert product is not None, "Must have a valid product."
        lifecycle_clause = self._lifecycleClause(
            DEFAULT_BRANCH_STATUS_IN_LISTING)
        query = "Branch.product = %d%s" % (product.id, lifecycle_clause)
        return Branch.select(
            self._generateBranchClause(query, visible_by_user),
            limit=quantity,
            orderBy=['-date_created', '-id'])

    def getBranchesWithRecentRevisionsForProduct(self, product, quantity,
                                                 visible_by_user=None):
        """See `IBranchSet`."""
        assert product is not None, "Must have a valid product."
        # XXX thumper 2008-01-07
        # This is a slight bastardisation due to a SQLObject limitation.
        # Here we have the same problem as the generalised sorting problem
        # where we want to order the results based on a field that is not
        # visible.  When we get stormified we can fix this, but I don't
        # think it is worthwile blocking this feature on storm.

        select_query = """
            select branch.id
            from branch, revision, branchrevision
            where branch.id = branchrevision.branch
            and branchrevision.revision = revision.id
            and branchrevision.sequence = branch.revision_count
            and branch.product = %s
            """ % product.id
        query = """
            %s order by revision.revision_date desc
            limit %s
            """ % (self._generateBranchClause(select_query, visible_by_user),
                   quantity)
        cur = cursor()
        cur.execute(query)

        branch_ids = [id for (id,) in cur.fetchall()]
        cur.close()
        # Now get the branches for these id's and sort them so they
        # are in the same order.

        # If there are no branch_ids, then return an empty list.
        if len(branch_ids) == 0:
            return []

        # Use a dictionary as a hash search for our insertion sort.
        branches = {}
        for branch in Branch.select('id in %s' % quote(branch_ids)):
            branches[branch.id] = branch

        return [branches[id] for id in branch_ids]

    def getPullQueue(self, branch_type):
        """See `IBranchSet`."""
        return Branch.select(
            AND(Branch.q.branch_type == branch_type,
                Branch.q.next_mirror_time < UTC_NOW),
            prejoins=['owner', 'product'], orderBy='next_mirror_time')

    def getTargetBranchesForUsersMergeProposals(self, user, product):
        """See `IBranchSet`."""
        return Branch.select("""
            BranchMergeProposal.target_branch = Branch.id
            AND BranchMergeProposal.registrant = %s
            AND Branch.product = %s
            """ % sqlvalues(user, product),
            clauseTables=['BranchMergeProposal'],
            orderBy=['owner', 'name'], distinct=True)
