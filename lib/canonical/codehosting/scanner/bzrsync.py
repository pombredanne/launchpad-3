#!/usr/bin/python
# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Import version control metadata from a Bazaar branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    ]

import logging
from datetime import datetime, timedelta
from StringIO import StringIO
import urlparse

import pytz
from zope.component import getUtility
from bzrlib.branch import Branch
from bzrlib.diff import show_diff_trees
from bzrlib.errors import NoSuchRevision
from bzrlib.log import log_formatter, show_log
from bzrlib.revision import NULL_REVISION

from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BugBranchStatus,
    IBranchRevisionSet, IBugBranchSet, IBugSet,
    IRevisionSet, NotFoundError)
from canonical.launchpad.mailout.branch import (
    send_branch_revision_notifications)

UTC = pytz.timezone('UTC')
# Use at most the first 100 characters of the commit message.
SUBJECT_COMMIT_MESSAGE_LENGTH = 100


class BadLineInBugsProperty(Exception):
    """Raised when the scanner encounters a bad line in a bug property."""


class RevisionModifiedError(Exception):
    """An error indicating that a revision has been modified."""
    pass


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


def get_diff(bzr_branch, bzr_revision):
    """Return the diff for `bzr_revision` on `bzr_branch`.

    :param bzr_branch: A `bzrlib.branch.Branch` object.
    :param bzr_revision: A Bazaar `Revision` object.
    :return: A byte string that is the diff of the changes introduced by
        `bzr_revision` on `bzr_branch`.
    """
    repo = bzr_branch.repository
    if bzr_revision.parent_ids:
        ids = (bzr_revision.revision_id, bzr_revision.parent_ids[0])
        tree_new, tree_old = repo.revision_trees(ids)
    else:
        # can't get both trees at once, so one at a time
        tree_new = repo.revision_tree(bzr_revision.revision_id)
        tree_old = repo.revision_tree(None)

    diff_content = StringIO()
    show_diff_trees(tree_old, tree_new, diff_content)
    raw_diff = diff_content.getvalue()
    return raw_diff.decode('utf8', 'replace')


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
        self.initial_scan = None
        self.email_from = config.noreply_from_address

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
        self.subscribers_want_notification = (subscriptions.count() > 0)

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
            self.pending_emails.append((contents, '', None))

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
            revision_diff = get_diff(bzr_branch, bzr_revision)
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
            self.pending_emails.append(
                (message, revision_diff, subject))

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
            send_branch_revision_notifications(
                self.db_branch, self.email_from, message, '', None)
        else:
            for message, diff, subject in self.pending_emails:
                send_branch_revision_notifications(
                    self.db_branch, self.email_from, message, diff,
                    subject)

        self.trans_manager.commit()


class BzrSync:
    """Import version control metadata from a Bazaar branch into the database.

    If the constructor succeeds, a read-lock for the underlying bzrlib branch
    is held, and must be released by calling the `close` method.
    """

    def __init__(self, trans_manager, branch, logger=None):
        self.trans_manager = trans_manager
        self.email_from = config.noreply_from_address

        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

        self.db_branch = branch
        self._bug_linker = BugBranchLinker(self.db_branch)
        self._branch_mailer = BranchMailer(self.trans_manager, self.db_branch)

    def syncBranchAndClose(self, bzr_branch=None):
        """Synchronize the database with a Bazaar branch and close resources.

        Convenience method that implements the proper idiom for the common
        case of calling `syncBranch` and `close`.
        """
        if bzr_branch is None:
            bzr_branch = Branch.open(self.db_branch.warehouse_url)
        bzr_branch.lock_read()
        try:
            self.syncBranch(bzr_branch)
        finally:
            bzr_branch.unlock()

    def syncBranch(self, bzr_branch):
        """Synchronize the database view of a branch with Bazaar data.

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
        self.retrieveBranchDetails(bzr_branch)
        # The BranchRevision, Revision and RevisionParent tables are only
        # written to by the branch-scanner, so they are not subject to
        # write-lock contention. Update them all in a single transaction to
        # improve the performance and allow garbage collection in the future.
        self.trans_manager.begin()
        self.retrieveDatabaseAncestry()
        (revisions_to_insert_or_check, branchrevisions_to_delete,
            branchrevisions_to_insert) = self.planDatabaseChanges()
        self.syncRevisions(bzr_branch, revisions_to_insert_or_check)
        self.deleteBranchRevisions(branchrevisions_to_delete)
        self.insertBranchRevisions(bzr_branch, branchrevisions_to_insert)
        self.trans_manager.commit()
        self._branch_mailer.sendRevisionNotificationEmails(self.bzr_history)
        # The Branch table is modified by other systems, including the web UI,
        # so we need to update it in a short transaction to avoid causing
        # timeouts in the webapp. This opens a small race window where the
        # revision data is updated in the database, but the Branch table has
        # not been updated. Since this has no ill-effect, and can only err on
        # the pessimistic side (tell the user the data has not yet been
        # updated although it has), the race is acceptable.
        self.trans_manager.begin()
        self.updateBranchStatus()
        self.trans_manager.commit()

    def retrieveDatabaseAncestry(self):
        """Efficiently retrieve ancestry from the database."""
        self.logger.info("Retrieving ancestry from database.")
        self.db_ancestry, self.db_history, self.db_branch_revision_map = (
            self.db_branch.getScannerData())
        initial_scan = (len(self.db_history) == 0)
        self._branch_mailer.initializeEmailQueue(initial_scan)

    def retrieveBranchDetails(self, bzr_branch):
        """Retrieve ancestry from the the bzr branch on disk."""
        self.logger.info("Retrieving ancestry from bzrlib.")
        self.last_revision = bzr_branch.last_revision()
        # Make bzr_ancestry a set for consistency with db_ancestry.
        bzr_ancestry_ordered = (
            bzr_branch.repository.get_ancestry(self.last_revision))
        first_ancestor = bzr_ancestry_ordered.pop(0)
        assert first_ancestor is None, 'history horizons are not supported'
        self.bzr_ancestry = set(bzr_ancestry_ordered)
        self.bzr_history = bzr_branch.revision_history()

    def planDatabaseChanges(self):
        """Plan database changes to synchronize with bzrlib data.

        Use the data retrieved by `retrieveDatabaseAncestry` and
        `retrieveBranchDetails` to plan the changes to apply to the database.
        """
        self.logger.info("Planning changes.")
        bzr_ancestry = self.bzr_ancestry
        bzr_history = self.bzr_history
        db_ancestry = self.db_ancestry
        db_history = self.db_history
        db_branch_revision_map = self.db_branch_revision_map

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
        branchrevisions_to_insert = list(
            self.getRevisions(added_merged.union(added_history)))

        # We must insert, or check for consistency, all revisions which were
        # added to the ancestry.
        revisions_to_insert_or_check = added_ancestry

        return (revisions_to_insert_or_check, branchrevisions_to_delete,
            branchrevisions_to_insert)

    def syncRevisions(self, bzr_branch, revisions_to_insert_or_check):
        """Import all the revisions added to the ancestry of the branch."""
        self.logger.info("Inserting or checking %d revisions.",
            len(revisions_to_insert_or_check))
        # Add new revisions to the database.
        for revision_id in revisions_to_insert_or_check:
            # If the revision is a ghost, it won't appear in the repository.
            try:
                revision = bzr_branch.repository.get_revision(
                    revision_id)
            except NoSuchRevision:
                self.logger.debug("%d of %d: %s is a ghost",
                                  self.curr, self.last, revision_id)
                continue
            self.syncOneRevision(revision)

    def syncOneRevision(self, bzr_revision):
        """Import the revision with the given revision_id.

        :param bzr_revision: the revision to import
        :type bzr_revision: bzrlib.revision.Revision
        """
        revision_id = bzr_revision.revision_id
        revision_set = getUtility(IRevisionSet)
        db_revision = revision_set.getByRevisionId(revision_id)
        if db_revision is not None:
            # Verify that the revision in the database matches the
            # revision from the branch.  Currently we just check that
            # the parent revision list matches.
            self.logger.debug("Checking revision: %s", revision_id)
            db_parents = db_revision.parents
            bzr_parents = bzr_revision.parent_ids

            seen_parents = set()
            for sequence, parent_id in enumerate(bzr_parents):
                if parent_id in seen_parents:
                    continue
                seen_parents.add(parent_id)
                matching_parents = [db_parent for db_parent in db_parents
                                    if db_parent.parent_id == parent_id]
                if len(matching_parents) == 0:
                    raise RevisionModifiedError(
                        'parent %s was added since last scan' % parent_id)
                elif len(matching_parents) > 1:
                    raise RevisionModifiedError(
                        'parent %s is listed multiple times in db'
                        % parent_id)
                if matching_parents[0].sequence != sequence:
                    raise RevisionModifiedError(
                        'parent %s reordered (old index %d, new index %d)'
                        % (parent_id, matching_parents[0].sequence, sequence))
            if len(seen_parents) != len(db_parents):
                removed_parents = [db_parent.parent_id
                                   for db_parent in db_parents
                                   if db_parent.parent_id not in seen_parents]
                raise RevisionModifiedError(
                    'some parents removed since last scan: %s'
                    % (removed_parents,))
        else:
            # Revision not yet in the database. Load it.
            self.logger.debug("Inserting revision: %s", revision_id)
            revision_date = self._timestampToDatetime(bzr_revision.timestamp)
            db_revision = revision_set.new(
                revision_id=revision_id,
                log_body=bzr_revision.message,
                revision_date=revision_date,
                revision_author=bzr_revision.get_apparent_author(),
                parent_ids=bzr_revision.parent_ids,
                properties=bzr_revision.properties)

    def getRevisions(self, limit=None):
        """Generate revision IDs that make up the branch's ancestry.

        Generate a sequence of (sequence, revision-id) pairs to be inserted
        into the branchrevision table.

        :param limit: set of revision ids, only yield tuples whose revision-id
            is in this set. Defaults to the full ancestry of the branch.
        """
        if limit is None:
            limit = self.bzr_ancestry
        for (index, revision_id) in enumerate(self.bzr_history):
            if revision_id in limit:
                # sequence numbers start from 1
                yield index + 1, revision_id
        for revision_id in limit.difference(set(self.bzr_history)):
            yield None, revision_id

    def _timestampToDatetime(self, timestamp):
        """Convert the given timestamp to a datetime object.

        This works around a bug in Python that causes datetime.fromtimestamp
        to raise an exception if it is given a negative, fractional timestamp.

        :param timestamp: A timestamp from a bzrlib.revision.Revision
        :type timestamp: float

        :return: A datetime corresponding to the given timestamp.
        """
        # Work around Python bug #1646728.
        # See https://launchpad.net/bugs/81544.
        int_timestamp = int(timestamp)
        revision_date = datetime.fromtimestamp(int_timestamp, tz=UTC)
        revision_date += timedelta(seconds=timestamp - int_timestamp)
        return revision_date

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
        for sequence, revision_id in branchrevisions_to_insert:
            db_revision = revision_set.getByRevisionId(revision_id)
            self.db_branch.createBranchRevision(sequence, db_revision)

            # Generate an email if the revision is in the revision_history
            # for the branch.  If the sequence is None then the revision
            # is just in the ancestry so no email is generated.
            if sequence is not None:
                try:
                    revision = bzr_branch.repository.get_revision(revision_id)
                except NoSuchRevision:
                    self.logger.debug("%d of %d: %s is a ghost",
                                      self.curr, self.last, revision_id)
                    continue
                self._branch_mailer.generateEmailForRevision(
                    bzr_branch, revision, sequence)
                self._bug_linker.createBugBranchLinksForRevision(revision)

    def updateBranchStatus(self):
        """Update the branch-scanner status in the database Branch table."""
        # Record that the branch has been updated.
        self.logger.info("Updating branch scanner status.")
        if len(self.bzr_history) > 0:
            last_revision = self.bzr_history[-1]
        else:
            last_revision = NULL_REVISION

        # FIXME: move that conditional logic down to updateScannedDetails.
        # -- DavidAllouche 2007-02-22
        revision_count = len(self.bzr_history)
        if ((last_revision != self.db_branch.last_scanned_id)
                or (revision_count != self.db_branch.revision_count)):
            self.db_branch.updateScannedDetails(last_revision, revision_count)
