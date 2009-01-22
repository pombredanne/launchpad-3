#!/usr/bin/python
# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Import version control metadata from a Bazaar branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    ]

import logging
from StringIO import StringIO
import urlparse

import pytz
from zope.component import getUtility
from bzrlib.branch import BzrBranchFormat4
from bzrlib.log import log_formatter, show_log
from bzrlib.revision import NULL_REVISION
from bzrlib.repofmt.weaverepo import (
    RepositoryFormat4, RepositoryFormat5, RepositoryFormat6)
from bzrlib import urlutils

from canonical.codehosting.puller.worker import BranchMirrorer, BranchPolicy
from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BugBranchStatus,
    IBranchRevisionSet, IBugBranchSet, IBugSet, IRevisionSet,
    NotFoundError, RepositoryFormat)
from canonical.launchpad.interfaces.branch import (
    BranchFormat, BranchLifecycleStatus, ControlFormat, IBranchSet,
    IRevisionMailJobSource)
from canonical.launchpad.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES)
from canonical.launchpad.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize)
from canonical.launchpad.interfaces.codehosting import LAUNCHPAD_SERVICES
from canonical.launchpad.webapp.uri import URI


UTC = pytz.timezone('UTC')
# Use at most the first 100 characters of the commit message.
SUBJECT_COMMIT_MESSAGE_LENGTH = 100


class BadLineInBugsProperty(Exception):
    """Raised when the scanner encounters a bad line in a bug property."""


class RevisionModifiedError(Exception):
    """An error indicating that a revision has been modified."""
    pass


class InvalidStackedBranchURL(Exception):
    """Raised when we try to scan a branch stacked on an invalid URL."""


def set_bug_branch_status(bug, branch, status):
    """Ensure there's a BugBranch for 'bug' and 'branch' set to 'status'.

    This creates a BugBranch if one doesn't exist, and changes the status if
    it does. If a BugBranch is created, the registrant is the branch owner.

    :return: The updated BugBranch.
    """
    bug_branch_set = getUtility(IBugBranchSet)
    bug_branch = bug_branch_set.getBugBranch(bug, branch)
    if bug_branch is None:
        return bug_branch_set.new(
            bug=bug, branch=branch, status=status, registrant=branch.owner)
    if bug_branch.status != BugBranchStatus.BESTFIX:
        bug_branch.status = status
    return bug_branch


def get_revision_message(bzr_branch, bzr_revision):
    """Return the log message for `bzr_revision` on `bzr_branch`.

    :param bzr_branch: A `bzrlib.branch.Branch` object.
    :param bzr_revision: A Bazaar `Revision` object.
    :return: The commit message entered for `bzr_revision`.
    """
    outf = StringIO()
    lf = log_formatter('long', to_file=outf)
    rev_id = bzr_revision.revision_id
    rev1 = rev2 = bzr_branch.revision_id_to_revno(rev_id)
    if rev1 == 0:
        rev1 = None
        rev2 = None

    show_log(bzr_branch,
             lf,
             start_revision=rev1,
             end_revision=rev2,
             verbose=True)
    return outf.getvalue()


class BugBranchLinker:
    """Links branches to bugs based on revision metadata."""

    def __init__(self, db_branch):
        self.db_branch = db_branch

    def _parseBugLine(self, line):
        """Parse a line from a bug property.

        :param line: A line from a Bazaar bug property.
        :raise BadLineInBugsProperty: if the line is invalid.
        :return: (bug_url, bug_id) if the line is good, None if the line
            should be skipped.
        """
        valid_statuses = {'fixed': BugBranchStatus.FIXAVAILABLE}
        line = line.strip()

        # Skip blank lines.
        if len(line) == 0:
            return None

        # Lines must be <url> <status>.
        try:
            url, status = line.split(None, 2)
        except ValueError:
            raise BadLineInBugsProperty('Invalid line: %r' % line)
        protocol, host, path, ignored, ignored = urlparse.urlsplit(url)

        # Skip URLs that don't point to Launchpad.
        if host != 'launchpad.net':
            return None

        # Don't allow Launchpad URLs that aren't /bugs/<integer>.
        try:
            # Remove empty path segments.
            bug_segment, bug_id = [
                segment for segment in path.split('/') if len(segment) > 0]
            if bug_segment != 'bugs':
                raise ValueError('Bad path segment')
            bug = int(path.split('/')[-1])
        except ValueError:
            raise BadLineInBugsProperty('Invalid bug reference: %s' % url)

        # Make sure the status is acceptable.
        try:
            status = valid_statuses[status.lower()]
        except KeyError:
            raise BadLineInBugsProperty('Invalid bug status: %r' % status)
        return bug, status

    def extractBugInfo(self, bug_property):
        """Parse bug information out of the given revision property.

        :param bug_status_prop: A string containing lines of
            '<bug_url> <status>'.
        :return: dict mapping bug IDs to BugBranchStatuses.
        """
        bug_statuses = {}
        for line in bug_property.splitlines():
            try:
                parsed_line = self._parseBugLine(line)
                if parsed_line is None:
                    continue
                bug, status = parsed_line
            except BadLineInBugsProperty, e:
                continue
            bug_statuses[bug] = status
        return bug_statuses

    def createBugBranchLinksForRevision(self, bzr_revision):
        """Create bug-branch links for a revision.

        This looks inside the 'bugs' property of the given Bazaar revision and
        creates a BugBranch record for each bug mentioned.
        """
        bug_property = bzr_revision.properties.get('bugs', None)
        if bug_property is None:
            return
        bug_set = getUtility(IBugSet)
        for bug_id, status in self.extractBugInfo(bug_property).iteritems():
            try:
                bug = bug_set.get(bug_id)
            except NotFoundError:
                pass
            else:
                set_bug_branch_status(bug, self.db_branch, status)


class BranchMailer:
    """Handles mail notifications for changes to the code in a branch."""

    def __init__(self, trans_manager, db_branch):
        self.trans_manager = trans_manager
        self.db_branch = db_branch
        self.pending_emails = []
        self.subscribers_want_notification = False
        self.generate_diffs = False
        self.initial_scan = None
        self.email_from = config.canonical.noreply_from_address

    def initializeEmailQueue(self, initial_scan):
        """Create an email queue and determine whether to create diffs.

        In order to avoid creating diffs when no one is interested in seeing
        it, we check all the branch subscriptions first, and decide here
        whether or not to generate the revision diffs as the branch is scanned.

        See XXX comment in `sendRevisionNotificationEmails` for the reason
        behind the queue itself.
        """
        self.pending_emails = []
        self.subscribers_want_notification = False

        diff_levels = (BranchSubscriptionNotificationLevel.DIFFSONLY,
                       BranchSubscriptionNotificationLevel.FULL)

        subscriptions = self.db_branch.getSubscriptionsByLevel(diff_levels)
        for subscription in subscriptions:
            self.subscribers_want_notification = True
            if (subscription.max_diff_lines !=
                BranchSubscriptionDiffSize.NODIFF):
                self.generate_diffs = True
                break

        # If db_history is empty, then this is the initial scan of the
        # branch.  We only want to send one email for the initial scan
        # of a branch, not one for each revision.
        self.initial_scan = initial_scan

    def generateEmailForRemovedRevisions(self, removed_history):
        """Notify subscribers of removed revisions.

        When the history is shortened, and email is sent that says this. This
        will never happen for a newly scanned branch, so not checking that
        here.
        """
        if not self.subscribers_want_notification:
            return
        number_removed = len(removed_history)
        if number_removed > 0:
            if number_removed == 1:
                contents = '1 revision was removed from the branch.'
            else:
                contents = ('%d revisions were removed from the branch.'
                            % number_removed)
            # No diff is associated with the removed email.
            job = getUtility(IRevisionMailJobSource).create(
                self.db_branch, revno='removed', from_address=self.email_from,
                body=contents, perform_diff=False, subject=None)
            self.pending_emails.append(job)

    def generateEmailForRevision(self, bzr_branch, bzr_revision, sequence):
        """Generate an email for a revision for later sending.

        :param bzr_branch: The branch being scanned.
        :param bzr_revision: The revision that we are sending the email about.
            This is assumed to be in the main-line history of the branch. (Not
            just the ancestry).
        :param sequence: The revision number of `bzr_revision`.
        """
        if (not self.initial_scan
            and self.subscribers_want_notification):
            message = get_revision_message(bzr_branch, bzr_revision)
            # Use the first (non blank) line of the commit message
            # as part of the subject, limiting it to 100 characters
            # if it is longer.
            message_lines = [
                line.strip() for line in bzr_revision.message.split('\n')
                if len(line.strip()) > 0]
            if len(message_lines) == 0:
                first_line = 'no commit message given'
            else:
                first_line = message_lines[0]
                if len(first_line) > SUBJECT_COMMIT_MESSAGE_LENGTH:
                    offset = SUBJECT_COMMIT_MESSAGE_LENGTH - 3
                    first_line = first_line[:offset] + '...'
            subject = '[Branch %s] Rev %s: %s' % (
                self.db_branch.unique_name, sequence, first_line)
            job = getUtility(IRevisionMailJobSource).create(
                self.db_branch, revno=sequence, from_address=self.email_from,
                    body=message, perform_diff=self.generate_diffs,
                    subject=subject)
            self.pending_emails.append(job)

    def sendRevisionNotificationEmails(self, bzr_history):
        """Send out the pending emails.

        If this is the first scan of a branch, then we send out a simple
        notification email saying that the branch has been scanned.
        """
        # XXX: thumper 2007-03-28 bug=29744:
        # The whole reason that this method exists is due to
        # emails being sent immediately in a zopeless environment.
        # When bug #29744 is fixed, this method will no longer be
        # necessary, and the emails should be sent at the source
        # instead of appending them to the pending_emails.
        # This method is enclosed in a transaction so emails will
        # continue to be sent out when the bug is closed without
        # immediately having to fix this method.
        # Now that these changes have been committed, send the pending emails.
        if not self.subscribers_want_notification:
            return
        self.trans_manager.begin()

        if self.initial_scan:
            assert len(self.pending_emails) == 0, (
                'Unexpected pending emails on new branch.')
            revision_count = len(bzr_history)
            if revision_count == 1:
                revisions = '1 revision'
            else:
                revisions = '%d revisions' % revision_count
            message = ('First scan of the branch detected %s'
                       ' in the revision history of the branch.' %
                       revisions)

            job = getUtility(IRevisionMailJobSource).create(
                self.db_branch, 'initial', self.email_from, message, False,
                None)
        self.trans_manager.commit()


class BranchMergeDetectionHandler:
    """Handle merge detection events."""

    def __init__(self, logger=None):
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

    def _markSourceBranchMerged(self, source):
        # If the source branch is a series branch, then don't change the
        # lifecycle status of it at all.
        if source.associatedProductSeries().count() > 0:
            return
        # In other cases, we now want to update the lifecycle status of the
        # source branch to merged.
        self.logger.info("%s now Merged.", source.bzr_identity)
        source.lifecycle_status = BranchLifecycleStatus.MERGED

    def mergeProposalMerge(self, proposal):
        """Handle a detected merge of a proposal."""
        self.logger.info(
            'Merge detected: %s => %s',
            proposal.source_branch.bzr_identity,
            proposal.target_branch.bzr_identity)
        proposal.markAsMerged()
        # Don't update the source branch unless the target branch is a series
        # branch.
        if proposal.target_branch.associatedProductSeries().count() == 0:
            return
        self._markSourceBranchMerged(proposal.source_branch)

    def mergeOfTwoBranches(self, source, target):
        """Handle the merge of source into target."""
        # If the target branch is not the development focus, then don't update
        # the status of the source branch.
        self.logger.info(
            'Merge detected: %s => %s',
            source.bzr_identity, target.bzr_identity)
        dev_focus = target.product.development_focus
        if target != dev_focus.user_branch:
            return
        self._markSourceBranchMerged(source)


class WarehouseBranchPolicy(BranchPolicy):

    def checkOneURL(self, url):
        """See `BranchOpener.checkOneURL`.

        If the URLs we are mirroring from are anything but a
        lp-mirrored:///~user/project/branch URLs, we don't want to scan them.
        Opening branches on remote systems takes too long, and we want all of
        our local access to be channelled through this transport.
        """
        uri = URI(url)
        if uri.scheme != 'lp-mirrored':
            raise InvalidStackedBranchURL(url)

    def transformFallbackLocation(self, branch, url):
        """See `BranchPolicy.transformFallbackLocation`.

        We're happy to open stacked branches in the usual manner, but want to
        go on checking the URLs of any branches we then open.
        """
        return urlutils.join(branch.base, url), True


def iter_list_chunks(a_list, size):
    """Iterate over `a_list` in chunks of size `size`.

    I'm amazed this isn't in itertools (mwhudson).
    """
    for i in range(0, len(a_list), size):
        yield a_list[i:i+size]


class BzrSync:
    """Import version control metadata from a Bazaar branch into the database.
    """

    def __init__(self, trans_manager, branch, logger=None):
        self.trans_manager = trans_manager
        self.email_from = config.canonical.noreply_from_address

        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

        self.db_branch = branch
        self._bug_linker = BugBranchLinker(self.db_branch)
        self._branch_mailer = BranchMailer(self.trans_manager, self.db_branch)
        self._merge_handler = BranchMergeDetectionHandler(self.logger)

    def syncBranchAndClose(self, bzr_branch=None):
        """Synchronize the database with a Bazaar branch, handling locking.
        """
        if bzr_branch is None:
            bzr_branch = BranchMirrorer(WarehouseBranchPolicy()).open(
                self.db_branch.warehouse_url)
        bzr_branch.lock_read()
        try:
            self.syncBranch(bzr_branch)
        finally:
            bzr_branch.unlock()

    def syncBranch(self, bzr_branch):
        """Synchronize the database view of a branch with Bazaar data.

        `bzr_branch` must be read locked.

        Several tables must be updated:

        * Revision: there must be one Revision row for each revision in the
          branch ancestry. If the row for a revision that has just been added
          to the branch is already present, it must be checked for consistency.

        * BranchRevision: there must be one BrancheRevision row for each
          revision in the branch ancestry. If history revisions became merged
          revisions, the corresponding rows must be changed.

        * Branch: the branch-scanner status information must be updated when
          the sync is complete.
        """
        self.logger.info("Scanning branch: %s", self.db_branch.unique_name)
        self.logger.info("    from %s", bzr_branch.base)
        # Get the history and ancestry from the branch first, to fail early
        # if something is wrong with the branch.
        bzr_ancestry, bzr_history = self.retrieveBranchDetails(bzr_branch)
        # The BranchRevision, Revision and RevisionParent tables are only
        # written to by the branch-scanner, so they are not subject to
        # write-lock contention. Update them all in a single transaction to
        # improve the performance and allow garbage collection in the future.
        self.trans_manager.begin()
        self.setFormats(bzr_branch)
        db_ancestry, db_history, db_branch_revision_map = (
            self.retrieveDatabaseAncestry())

        (added_ancestry, branchrevisions_to_delete,
            branchrevisions_to_insert) = self.planDatabaseChanges(
            bzr_ancestry, bzr_history, db_ancestry, db_history,
            db_branch_revision_map)
        added_ancestry.difference_update(
            getUtility(IRevisionSet).onlyPresent(added_ancestry))
        self.logger.info("Adding %s new revisions.", len(added_ancestry))
        for revids in iter_list_chunks(list(added_ancestry), 1000):
            revisions = self.getBazaarRevisions(bzr_branch, revids)
            for revision in revisions:
                # This would probably go much faster if we found some way to
                # bulk-load multiple revisions at once, but as this is only
                # executed for revisions new to Launchpad, it doesn't seem
                # worth it at this stage.
                self.syncOneRevision(revision, branchrevisions_to_insert)
        self.deleteBranchRevisions(branchrevisions_to_delete)
        self.insertBranchRevisions(bzr_branch, branchrevisions_to_insert)
        self.trans_manager.commit()

        self._branch_mailer.sendRevisionNotificationEmails(bzr_history)
        # The Branch table is modified by other systems, including the web UI,
        # so we need to update it in a short transaction to avoid causing
        # timeouts in the webapp. This opens a small race window where the
        # revision data is updated in the database, but the Branch table has
        # not been updated. Since this has no ill-effect, and can only err on
        # the pessimistic side (tell the user the data has not yet been
        # updated although it has), the race is acceptable.
        self.trans_manager.begin()
        self.updateBranchStatus(bzr_history)
        self.autoMergeProposals(bzr_ancestry)
        self.autoMergeBranches(bzr_ancestry)
        self.trans_manager.commit()

    def autoMergeBranches(self, bzr_ancestry):
        """Detect branches that have been merged."""
        # We only check branches that have been merged into the branch that is
        # being scanned as we already have the ancestry handy.  It is much
        # more work to determine which other branches this branch has been
        # merged into.  At this stage the merge detection only checks other
        # branches merged into the scanned one.

        # Only do this for non-junk branches.
        if self.db_branch.product is None:
            return
        # Get all the active branches for the product, and if the
        # last_scanned_revision is in the ancestry, then mark it as merged.
        branches = getUtility(IBranchSet).getBranchesForContext(
            context=self.db_branch.product,
            visible_by_user=LAUNCHPAD_SERVICES,
            lifecycle_statuses=(
                BranchLifecycleStatus.NEW,
                BranchLifecycleStatus.DEVELOPMENT,
                BranchLifecycleStatus.EXPERIMENTAL,
                BranchLifecycleStatus.MATURE,
                BranchLifecycleStatus.ABANDONED))
        for branch in branches:
            last_scanned = branch.last_scanned_id
            # If the branch doesn't have any revisions, not any point setting
            # anything.
            if last_scanned is None or last_scanned == NULL_REVISION:
                # Skip this branch.
                pass
            elif branch == self.db_branch:
                # No point merging into ourselves.
                pass
            elif self.db_branch.last_scanned_id == last_scanned:
                # If the tip revisions are the same, then it is the same
                # branch, not one merged into the other.
                pass
            elif last_scanned in bzr_ancestry:
                self._merge_handler.mergeOfTwoBranches(
                    branch, self.db_branch)

    def autoMergeProposals(self, bzr_ancestry):
        """Detect merged proposals."""
        # Check landing candidates in non-terminal states to see if their tip
        # is in our ancestry. If it is, set the state of the proposal to
        # 'merged'.

        # At this stage we are not going to worry about the revno
        # which introduced the change, that will either be set through the web
        # ui by a person, of by PQM once it is integrated.
        for proposal in self.db_branch.landing_candidates:
            if proposal.source_branch.last_scanned_id in bzr_ancestry:
                self._merge_handler.mergeProposalMerge(proposal)

        # Now check the landing targets.
        final_states = BRANCH_MERGE_PROPOSAL_FINAL_STATES
        tip_rev_id = self.db_branch.last_scanned_id
        for proposal in self.db_branch.landing_targets:
            if proposal.queue_status not in final_states:
                # If there is a branch revision record for target branch with
                # the tip_rev_id of the source branch, then it is merged.
                branch_revision = proposal.target_branch.getBranchRevision(
                    revision_id=tip_rev_id)
                if branch_revision is not None:
                    self._merge_handler.mergeProposalMerge(proposal)

    def retrieveDatabaseAncestry(self):
        """Efficiently retrieve ancestry from the database."""
        self.logger.info("Retrieving ancestry from database.")
        db_ancestry, db_history, db_branch_revision_map = (
            self.db_branch.getScannerData())
        initial_scan = (len(db_history) == 0)
        self._branch_mailer.initializeEmailQueue(initial_scan)
        return db_ancestry, db_history, db_branch_revision_map

    def retrieveBranchDetails(self, bzr_branch):
        """Retrieve ancestry from the the bzr branch on disk."""
        self.logger.info("Retrieving ancestry from bzrlib.")
        last_revision = bzr_branch.last_revision()
        # Make bzr_ancestry a set for consistency with db_ancestry.
        bzr_ancestry_ordered = (
            bzr_branch.repository.get_ancestry(last_revision))
        first_ancestor = bzr_ancestry_ordered.pop(0)
        assert first_ancestor is None, 'history horizons are not supported'
        bzr_ancestry = set(bzr_ancestry_ordered)
        bzr_history = bzr_branch.revision_history()
        return bzr_ancestry, bzr_history

    def setFormats(self, bzr_branch):
        """Record the stored formats in the database object.

        The previous value is unconditionally overwritten.

        Note that the strings associated with the formats themselves are used,
        not the strings on disk.
        """
        def match_title(enum, title, default):
            for value in enum.items:
                if value.title == title:
                    return value
            else:
                return default

        # XXX: Aaron Bentley 2008-06-13
        # Bazaar does not provide a public API for learning about format
        # markers.  Fix this in Bazaar, then here.
        control_string = bzr_branch.bzrdir._format.get_format_string()
        if bzr_branch._format.__class__ is BzrBranchFormat4:
            branch_string = BranchFormat.BZR_BRANCH_4.title
        else:
            branch_string = bzr_branch._format.get_format_string()
        repository_format = bzr_branch.repository._format
        if repository_format.__class__ is RepositoryFormat6:
            repository_string = RepositoryFormat.BZR_REPOSITORY_6.title
        elif repository_format.__class__ is RepositoryFormat5:
            repository_string = RepositoryFormat.BZR_REPOSITORY_5.title
        elif repository_format.__class__ is RepositoryFormat4:
            repository_string = RepositoryFormat.BZR_REPOSITORY_4.title
        else:
            repository_string = repository_format.get_format_string()
        self.db_branch.control_format = match_title(
            ControlFormat, control_string, ControlFormat.UNRECOGNIZED)
        self.db_branch.branch_format = match_title(
            BranchFormat, branch_string, BranchFormat.UNRECOGNIZED)
        self.db_branch.repository_format = match_title(
            RepositoryFormat, repository_string,
            RepositoryFormat.UNRECOGNIZED)

    def planDatabaseChanges(self, bzr_ancestry, bzr_history, db_ancestry,
                            db_history, db_branch_revision_map):
        """Plan database changes to synchronize with bzrlib data.

        Use the data retrieved by `retrieveDatabaseAncestry` and
        `retrieveBranchDetails` to plan the changes to apply to the database.
        """
        self.logger.info("Planning changes.")
        # Find the length of the common history.
        common_len = min(len(bzr_history), len(db_history))
        while common_len > 0:
            # The outer conditional improves efficiency. Without it, the
            # algorithm is O(history-size * change-size), which can be
            # excessive if a long branch is replaced by another long branch
            # with a distant (or no) common mainline parent. The inner
            # conditional is needed for correctness with branches where the
            # history does not follow the line of leftmost parents.
            if db_history[common_len - 1] == bzr_history[common_len - 1]:
                if db_history[:common_len] == bzr_history[:common_len]:
                    break
            common_len -= 1

        # Revisions added to the branch's ancestry.
        added_ancestry = bzr_ancestry.difference(db_ancestry)

        # Revision added or removed from the branch's history. These lists may
        # include revisions whose history position has merely changed.
        removed_history = db_history[common_len:]
        added_history = bzr_history[common_len:]

        self._branch_mailer.generateEmailForRemovedRevisions(removed_history)

        # Merged (non-history) revisions in the database and the bzr branch.
        old_merged = db_ancestry.difference(db_history)
        new_merged = bzr_ancestry.difference(bzr_history)

        # Revisions added or removed from the set of merged revisions.
        removed_merged = old_merged.difference(new_merged)
        added_merged = new_merged.difference(old_merged)

        # We must delete BranchRevision rows for all revisions which where
        # removed from the ancestry or whose sequence value has changed.
        branchrevisions_to_delete = set(
            db_branch_revision_map[revid]
            for revid in removed_merged.union(removed_history))

        # We must insert BranchRevision rows for all revisions which were
        # added to the ancestry or whose sequence value has changed.
        branchrevisions_to_insert = dict(
            self.getRevisions(
                bzr_history, added_merged.union(added_history)))

        return (added_ancestry, branchrevisions_to_delete,
                branchrevisions_to_insert)

    def getBazaarRevisions(self, bzr_branch, revisions):
        """Like ``get_revisions(revisions)`` but filter out ghosts first.

        :param revisions: the set of Bazaar revision IDs to return bzrlib
            Revision objects for.
        """
        revisions = bzr_branch.repository.get_parent_map(revisions)
        return bzr_branch.repository.get_revisions(revisions.keys())

    def syncOneRevision(self, bzr_revision, branchrevisions_to_insert):
        """Import the revision with the given revision_id.

        :param bzr_revision: the revision to import
        :type bzr_revision: bzrlib.revision.Revision
        :param branchrevisions_to_insert: a dict of revision ids to integer
            revno.  (Non-mainline revisions will not be present).
        """
        revision_id = bzr_revision.revision_id
        revision_set = getUtility(IRevisionSet)
        # Revision not yet in the database. Load it.
        self.logger.debug("Inserting revision: %s", revision_id)
        revision_set.newFromBazaarRevision(bzr_revision)
        # If a mainline revision, add the bug branch link.
        if branchrevisions_to_insert[revision_id] is not None:
            self._bug_linker.createBugBranchLinksForRevision(bzr_revision)

    def getRevisions(self, bzr_history, revision_subset):
        """Generate revision IDs that make up the branch's ancestry.

        Generate a sequence of (revision-id, sequence) pairs to be inserted
        into the branchrevision table.
        """
        for (index, revision_id) in enumerate(bzr_history):
            if revision_id in revision_subset:
                # sequence numbers start from 1
                yield revision_id, index + 1
        for revision_id in revision_subset.difference(set(bzr_history)):
            yield revision_id, None

    def deleteBranchRevisions(self, branchrevisions_to_delete):
        """Delete a batch of BranchRevision rows."""
        self.logger.info("Deleting %d branchrevision records.",
            len(branchrevisions_to_delete))
        branch_revision_set = getUtility(IBranchRevisionSet)
        for branchrevision in sorted(branchrevisions_to_delete):
            branch_revision_set.delete(branchrevision)

    def insertBranchRevisions(self, bzr_branch, branchrevisions_to_insert):
        """Insert a batch of BranchRevision rows."""
        self.logger.info("Inserting %d branchrevision records.",
            len(branchrevisions_to_insert))
        revision_set = getUtility(IRevisionSet)
        revid_seq_pairs = branchrevisions_to_insert.items()
        for revid_seq_pair_chunk in iter_list_chunks(revid_seq_pairs, 1000):
            self.db_branch.createBranchRevisionFromIDs(revid_seq_pair_chunk)

        # Generate emails for the revisions in the revision_history
        # for the branch.
        mainline_revids = [
            revid for (revid, sequence)
            in branchrevisions_to_insert.iteritems() if sequence is not None]

        for revid_chunk in iter_list_chunks(mainline_revids, 1000):
            present_mainline_revisions = self.getBazaarRevisions(
                bzr_branch, revid_chunk)
            for revision in present_mainline_revisions:
                sequence = branchrevisions_to_insert[revision.revision_id]
                assert sequence is not None
                self._branch_mailer.generateEmailForRevision(
                    bzr_branch, revision, sequence)

    def updateBranchStatus(self, bzr_history):
        """Update the branch-scanner status in the database Branch table."""
        # Record that the branch has been updated.
        if len(bzr_history) > 0:
            last_revision = bzr_history[-1]
            revision = getUtility(IRevisionSet).getByRevisionId(last_revision)
        else:
            revision = None

        revision_count = len(bzr_history)
        self.logger.info(
            "Updating branch scanner status: %s revs", revision_count)
        self.db_branch.updateScannedDetails(revision, revision_count)
