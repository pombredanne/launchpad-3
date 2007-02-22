#!/usr/bin/python
# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Import version control metadata from a Bazaar branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    ]

import sys
import os
import logging
from datetime import datetime, timedelta

import pytz
from zope.component import getUtility
from bzrlib.branch import Branch
from bzrlib.revision import NULL_REVISION
from bzrlib.errors import NoSuchRevision

from sqlobject import AND
from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBranchRevisionSet, IBranchSet, IRevisionSet)

UTC = pytz.timezone('UTC')


class RevisionModifiedError(Exception):
    """An error indicating that a revision has been modified."""
    pass


class BzrSync:
    """Import version control metadata from a Bazaar branch into the database.

    If the contructor succeeds, a read-lock for the underlying bzrlib branch is
    held, and must be released by calling the `close` method.
    """

    def __init__(self, trans_manager, branch, branch_url=None, logger=None):
        self.trans_manager = trans_manager
        self._admin = getUtility(ILaunchpadCelebrities).admin
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger
        self.db_branch = branch
        if branch_url is None:
            branch_url = self.db_branch.url
        self.bzr_branch = Branch.open(branch_url)
        self.bzr_branch.lock_read()

    def close(self):
        """Explicitly release resources."""
        # release the read lock on the bzrlib branch
        self.bzr_branch.unlock()
        # prevent further use of that object
        self.bzr_branch = None
        self.db_branch = None
        self.bzr_history = None

    def syncBranchAndClose(self):
        """Synchronize the database with a Bazaar branch and release resources.

        Convenience method that implements the proper for the common case of
        retrieving information from the database, Bazaar branch, calling
        `syncBranch` and `close`.
        """
        try:
            # Load the ancestry as the database knows of it.
            self.retrieveDatabaseAncestry()
            # And get the history and ancestry from the branch.
            self.retrieveBranchDetails()
            self.syncBranch()
        finally:
            self.close()

    def syncBranch(self):
        """Synchronize the database view of a branch with Bazaar data.

        Several tables must be updated:

        * Revision: there must be one Revision row for each revision in the
          branch ancestry. If the row for a revision that has just been added
          to the branch is already present, it must be checked for consistency.

        * BranchRevision: there must be one BrancheRevision row for each
          revision in the branch ancestry. If history revisions became merged
          revision, the corresponding rows must be changed.

        * Branch: the branch-scanner status information must be updated when
          the sync is complete.
        """
        self.syncInitialAncestry()
        self.syncRevisions()
        self.syncBranchRevisions()
        self.trans_manager.begin()
        self.updateBranchStatus()
        self.trans_manager.commit()

    def retrieveDatabaseAncestry(self):
        """Since the ancestry of some branches is into the tens of thousands
        we don't want to materialise BranchRevision instances for each of these
        in the SQLObject cache, so keep a simple map here."""
        # NOMERGE: move that into the content class, add interface.
        cur = cursor()
        cur.execute("""
            SELECT BranchRevision.id, BranchRevision.sequence, Revision.revision_id
            FROM Revision, BranchRevision
            WHERE
                Revision.id = BranchRevision.revision
            AND BranchRevision.branch = %s
            ORDER BY BranchRevision.sequence
            """ % sqlvalues(self.db_branch))
        self.db_ancestry = set()
        self.db_history = []
        self.db_branch_revision_map = {}
        for branch_revision_id, sequence, revision_id in cur.fetchall():
            self.db_ancestry.add(revision_id)
            self.db_branch_revision_map[revision_id] = branch_revision_id
            if sequence is not None:
                self.db_history.append(revision_id)

    def retrieveBranchDetails(self):
        # NOMERGE: docstring!
        self.last_revision = self.bzr_branch.last_revision()
        self.bzr_ancestry = self.bzr_branch.repository.get_ancestry(
            self.last_revision)
        self.bzr_history = self.bzr_branch.revision_history()

    def syncInitialAncestry(self):
        # NOMERGE: doctsring!
        # NOMERGE: method too long and hard to read

        # If the database history is the same as the start of
        # the bzr history, then this branch has only been appended to.
        # If not then we need to clean out the db ancestry before
        # we get started adding stuff.
        rev_count = len(self.db_history)
        if self.bzr_history[:rev_count] == self.db_history:
            # Branch has only been appended to.
            return
        # NOMERGE: This should not be needed. If the rest of the logic is correct
        # in the method, it should be fast and make no change.

        self.trans_manager.begin()

        # Branch history has changed

        # NOMERGE: match_position is ill-named, this is the position of the
        # first non-match in the history
        match_position = min(len(self.bzr_history), rev_count)
        while match_position > 0 and (
            self.db_history[:match_position] != self.bzr_history[:match_position]):
            match_position -= 1
        # NOMERGE: This is (history length) x (removed history revisions).
        # Bad! Remove (history length) factor!

        # Remove the revisions from the db history that don't match
        branch_revision_set = getUtility(IBranchRevisionSet)
        removed = set()
        for rev_id in self.db_history[match_position:]:
            removed.add(rev_id)
            branch_revision_set.delete(self.db_branch_revision_map[rev_id])
            # NOMERGE BUG: should update db_ancestry as well.
        # NOMERGE: While we're optimising, can we do the equivalent of
        # "delete from branchrevision where id in (...)", postpone deletion.

        # Now realign our db_history.
        self.db_history = self.db_history[:match_position]
        # NOMERGE: this looks bogus, the last non-matching revision is not removed.

        # Now remove everything in the ancestry that shouldn't be there.
        to_remove = self.db_ancestry - set(self.bzr_ancestry) - removed
        for rev_id in to_remove:
            self.db_ancestry.remove(rev_id)
            branch_revision_set.delete(self.db_branch_revision_map[rev_id])
        # NOMERGE: While we're optimising, can we do the equivalent of
        # "delete from branchrevision where id in (...)".

        # The database and db_history, and db_ancestry are now all
        # in sync with the common parts of the branch.
        # NOMERGE BUG: do not commit until ancestry sync is complete!
        self.trans_manager.commit()

    def syncRevisions(self):
        """Import all the revisions added to the ancestry of the branch."""
        self.logger.info(
            "synchronizing revisions for branch: %s", self.bzr_branch.base)
        # Add new revisions to the database.
        added_ancestry = set(self.bzr_ancestry) - self.db_ancestry
        for revision_id in added_ancestry:
            if revision_id is None:
                continue
            # If the revision is a ghost, it won't appear in the repository.
            try:
                revision = self.bzr_branch.repository.get_revision(revision_id)
            except NoSuchRevision:
                continue
            # TODO: Sync revisions in batch for improved performance.
            # -- DavidAllouche 2007-02-22
            self.syncRevision(revision)

    def syncRevision(self, bzr_revision):
        """Import the revision with the given revision_id.

        :param bzr_revision: the revision to import
        :type bzr_revision: bzrlib.revision.Revision
        """
        revision_id = bzr_revision.revision_id
        self.logger.debug("synchronizing revision: %s", revision_id)

        # If did_something is True, new information was found and
        # loaded into the database.
        did_something = False

        self.trans_manager.begin()

        db_revision = getUtility(IRevisionSet).getByRevisionId(revision_id)
        if db_revision is not None:
            # Verify that the revision in the database matches the
            # revision from the branch.  Currently we just check that
            # the parent revision list matches.
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
                        'parent %s is listed multiple times in db' % parent_id)
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
            db_revision = getUtility(IRevisionSet).new(
                revision_id=revision_id,
                log_body=bzr_revision.message,
                revision_date=self._timestampToDatetime(bzr_revision.timestamp),
                revision_author=bzr_revision.committer,
                owner=self._admin,
                parent_ids=bzr_revision.parent_ids)
            did_something = True

        if did_something:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

    def getRevisions(self):
        """Generate revision IDs that make up the branch's ancestry.

        Generate a sequence of (sequence, revisionID) pairs to be inserted into
        the branchrevision (nee revisionnumber) table.
        """
        for (index, revision_id) in enumerate(self.bzr_history):
            # sequence numbers start from 1
            yield index + 1, revision_id
        history = set(self.bzr_history)
        for revision_id in self.bzr_ancestry:
            if revision_id is not None and revision_id not in history:
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

    def syncBranchRevisions(self):
        """Synchronise the revision numbers for the branch."""
        self.logger.info(
            "synchronizing revision numbers for branch: %s",
            self.bzr_branch.base)

        # now synchronise the BranchRevision objects
        branch_revision_set = getUtility(IBranchRevisionSet)
        for (sequence, revision_id) in self.getRevisions():
            self.syncBranchRevision(branch_revision_set, sequence, revision_id)

    def updateBranchStatus(self):
        """Update the branch-scanner status in the database Branch table."""
        # record that the branch has been updated.
        if len(self.bzr_history) > 0:
            last_revision = self.bzr_history[-1]
        else:
            last_revision = NULL_REVISION

        # FIXME: move that conditional logic down to updateScannedDetails.
        # -- DavidAllouche 2007-02-22
        revision_count = len(self.bzr_history)
        if (last_revision != self.db_branch.last_scanned_id) or \
               (revision_count != self.db_branch.revision_count):
            self.db_branch.updateScannedDetails(last_revision, revision_count)

    def syncBranchRevision(self, branch_revision_set, sequence, revision_id):
        """Import the revision number with the given sequence and revision_id

        :param sequence: the sequence number for this revision number
        :type sequence: int
        :param revision_id: GUID of the revision
        :type revision_id: str
        """
        did_something = False

        # If the sequence number is <= the db_history, then we have it already
        if sequence is not None and sequence <= len(self.db_history):
            return False
        # NOMERGE: this should not be needed if db_ancestry was updated correctly.

        # If sequence is None, and the revision_id is already in the
        # ancestry, then we have it already
        if sequence is None and revision_id in self.db_ancestry:
            return False

        # NOMORGE: We should not have to do this. Instead we can know directly
        # which are the RevisionNumbers we need to add to the database.

        # NOMERGE BUG: update the ancestry in a single transaction!
        # Probably call syncInitialAncestry from this method.

        # Otherwise we need to add it in.
        self.trans_manager.begin()

        db_revision = getUtility(IRevisionSet).getByRevisionId(revision_id)

        branch_revision_set.new(self.db_branch, sequence, db_revision)
        
        self.trans_manager.commit()

        return True
