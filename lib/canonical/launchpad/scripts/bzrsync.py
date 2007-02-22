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
        self.logger.info("Synchronizing branch: %s", self.bzr_branch.base)
        self.planDatabaseChanges()
        self.syncRevisions()
        self.trans_manager.begin()
        self.syncBranchRevisions()
        self.trans_manager.commit()
        self.trans_manager.begin()
        self.updateBranchStatus()
        self.trans_manager.commit()

    def retrieveDatabaseAncestry(self):
        """Since the ancestry of some branches is into the tens of thousands
        we don't want to materialise BranchRevision instances for each of these
        in the SQLObject cache, so keep a simple map here."""
        # NOMERGE: move that into the content class, add interface.
        self.logger.info("Retrieving ancestry from database.")
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
        self.logger.info("Retrieving ancestry from bzrlib.")
        self.last_revision = self.bzr_branch.last_revision()
        # Make bzr_ancestry a set for consistency with db_ancestry, but keep
        # the ordered ancestry around for database insertions.
        bzr_ancestry_ordered = \
            self.bzr_branch.repository.get_ancestry(self.last_revision)
        first_ancestor = bzr_ancestry_ordered.pop(0)
        assert first_ancestor is None, 'history horizons are not supported'
        self.bzr_ancestry = set(bzr_ancestry_ordered)
        self.bzr_history = self.bzr_branch.revision_history()

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
            if db_history[common_len - 1] == bzr_history[common_len - 1]:
                if db_history[:common_len] == bzr_history[:common_len]:
                    break
            common_len -= 1

        # Revision added or removed from the branch's history.
        removed_history = db_history[common_len:]
        added_history = bzr_history[common_len:]

        # Revisions added or removed from the branch's ancestry.
        added_ancestry = bzr_ancestry.difference(db_ancestry)
        removed_ancestry = db_ancestry.difference(bzr_ancestry)

        # We must delete BranchRevision rows for all revisions which were
        # removed from the ancestry or from the history.
        self.branchrevisions_to_delete = set(
            db_branch_revision_map[revid]
            for revid in set(removed_history).union(removed_ancestry))

        # We must insert BranchRevision rows for all revisions which were added
        # to the ancestry or to the history.
        self.branchrevisions_to_insert = list(
            self.getRevisions(added_ancestry.union(added_history)))

        # We must insert, or check for consistency, all revisions which were
        # added to the ancestry.
        self.revisions_to_insert_or_check = added_ancestry

    def syncRevisions(self):
        """Import all the revisions added to the ancestry of the branch."""
        self.logger.info("Inserting or checking %d revisions.",
            len(self.revisions_to_insert_or_check))
        # Add new revisions to the database.
        for revision_id in self.revisions_to_insert_or_check:
            # If the revision is a ghost, it won't appear in the repository.
            try:
                revision = self.bzr_branch.repository.get_revision(revision_id)
            except NoSuchRevision:
                continue
            # TODO: Sync revisions in batch for improved performance.
            # -- DavidAllouche 2007-02-22
            self.trans_manager.begin()
            self.syncOneRevision(revision)
            self.trans_manager.commit()

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
            self.logger.debug("Inserting revision: %s", revision_id)
            revision_date = self._timestampToDatetime(bzr_revision.timestamp)
            db_revision = revision_set.new(
                revision_id=revision_id,
                log_body=bzr_revision.message,
                revision_date=revision_date,
                revision_author=bzr_revision.committer,
                owner=self._admin,
                parent_ids=bzr_revision.parent_ids)

    def getRevisions(self, limit=None):
        """Generate revision IDs that make up the branch's ancestry.

        Generate a sequence of (sequence, revision-id) pairs to be inserted
        into the branchrevision (nee revisionnumber) table.

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

    def syncBranchRevisions(self):
        """Synchronise the revision numbers for the branch."""
        branch_revision_set = getUtility(IBranchRevisionSet)
        revision_set = getUtility(IRevisionSet)

        # Delete BranchRevision records.
        self.logger.info("Deleting %d branchrevision records.",
            len(self.branchrevisions_to_delete))
        for branchrevision in sorted(self.branchrevisions_to_delete):
            branch_revision_set.delete(branchrevision)

        # Insert BranchRevision records.
        self.logger.info("Inserting %d branchrevision records.",
            len(self.branchrevisions_to_insert))
        for sequence, revision_id in self.branchrevisions_to_insert:
            db_revision = revision_set.getByRevisionId(revision_id)
            branch_revision_set.new(self.db_branch, sequence, db_revision)

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
        if (last_revision != self.db_branch.last_scanned_id) or \
               (revision_count != self.db_branch.revision_count):
            self.db_branch.updateScannedDetails(last_revision, revision_count)
