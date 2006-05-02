#!/usr/bin/python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Import version control metadata from a Bazaar2 branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    ]

import sys
import os
import logging
from datetime import datetime

from pytz import UTC
from zope.component import getUtility
from bzrlib.branch import Branch as BzrBranch
from bzrlib.errors import NoSuchRevision

from sqlobject import AND
from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.database import (
    Person, Branch, Revision, RevisionNumber, RevisionParent, RevisionAuthor)
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBranchSet, NotFoundError)


class RevisionModifiedError(Exception):
    """An error indicating that a revision has been modified."""
    pass


class BzrSync:
    """Import version control metadata from Bazaar2 branches into the database.
    """

    def __init__(self, trans_manager, branch_id, branch_url=None, logger=None):
        self.trans_manager = trans_manager
        branchset = getUtility(IBranchSet)
        # Will raise NotFoundError when the branch is not found.
        self.db_branch = branchset[branch_id]
        if branch_url is None:
            branch_url = self.db_branch.url
        self.bzr_branch = BzrBranch.open(branch_url)
        self.bzr_history = self.bzr_branch.revision_history()
        self._admin = getUtility(ILaunchpadCelebrities).admin
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

    def syncHistory(self):
        """Import all revisions in the branch's revision-history."""
        # Keep track if something was actually loaded in the database.
        didsomething = False

        self.logger.info(
            "synchronizing ancestry for branch: %s", self.bzr_branch.base)

        # synchronise Revision objects
        ancestry = self.bzr_branch.repository.get_ancestry(
            self.bzr_branch.last_revision())
        for revision_id in ancestry:
            didsomething |= self.syncRevision(revision_id)

        self.logger.info(
            "synchronizing revision numbers for branch: %s",
            self.bzr_branch.base)

        # now synchronise the RevisionNumber objects
        for (index, revision_id) in enumerate(self.bzr_history):
            # sequence numbers start from 1
            sequence = index + 1
            didsomething |= self.syncRevisionNumber(sequence, revision_id)

        # finally truncate any further revision numbers (if they exist):
        self.trans_manager.begin()
        if self.truncateHistory():
            self.trans_manager.commit()
            didsomething = True
        else:
            self.trans_manager.abort()

        return didsomething

    def syncRevision(self, revision_id):
        """Import the revision with the given revision_id.

        :param revision_id: GUID of the revision to import.
        :type revision_id: str
        """
        if revision_id is None:
            return False

        self.logger.debug("synchronizing revision: %s", revision_id)

        # If didsomething is True, new information was found and
        # loaded into the database.
        didsomething = False

        # If the revision is a ghost, it won't exist in the branch's
        # repository.
        try:
            bzr_revision = self.bzr_branch.repository.get_revision(revision_id)
        except NoSuchRevision:
            return didsomething

        self.trans_manager.begin()

        db_revision = Revision.selectOneBy(revision_id=revision_id)
        if db_revision is not None:
            # Verify that the revision in the database matches the
            # revision from the branch.  Currently we just, check that
            # the parent revision list matches.
            db_parents = shortlist(RevisionParent.selectBy(
                revisionID=db_revision.id, orderBy='sequence'))
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
            timestamp = bzr_revision.timestamp
            if bzr_revision.timezone:
                timestamp += bzr_revision.timezone
            revision_date = datetime.fromtimestamp(timestamp, tz=UTC)
            db_author = RevisionAuthor.selectOneBy(name=bzr_revision.committer)
            if not db_author:
                db_author = RevisionAuthor(name=bzr_revision.committer)
            db_revision = Revision(revision_id=revision_id,
                                   log_body=bzr_revision.message,
                                   revision_date=revision_date,
                                   revision_author=db_author.id,
                                   owner=self._admin.id)
            seen_parents = set()
            for sequence, parent_id in enumerate(bzr_revision.parent_ids):
                if parent_id in seen_parents:
                    continue
                seen_parents.add(parent_id)
                RevisionParent(revision=db_revision.id, sequence=sequence,
                               parent_id=parent_id)
            didsomething = True
            
        if didsomething:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

        return didsomething

    def syncRevisionNumber(self, sequence, revision_id):
        """Import the revision number with the given sequence and revision_id

        :param sequence: the sequence number for this revision number
        :type sequence: int
        :param revision_id: GUID of the revision
        :type revision_id: str
        """
        didsomething = False

        self.trans_manager.begin()

        db_revision = Revision.selectOneBy(revision_id=revision_id)
        assert db_revision is not None, (
            "revision %s has not been imported" % revision_id)
        db_revno = RevisionNumber.selectOneBy(
            sequence=sequence, branchID=self.db_branch.id)

        # If the database revision history has diverged, so we
        # truncate the database history from this point on.  The
        # replacement revision numbers will be created in their place.
        if db_revno is not None and db_revno.revision != db_revision:
            didsomething |= self.truncateHistory(sequence)
            db_revno = None

        if db_revno is None:
            db_revno = RevisionNumber(
                sequence=sequence,
                revision=db_revision.id,
                branch=self.db_branch.id)
            didsomething = True

        if didsomething:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

        return didsomething

    def truncateHistory(self, from_rev=None):
        """Remove excess RevisionNumber rows.

        :param fromrev: truncate from this revision on (defaults to
            truncating revisions past the current revision number).
        :type fromrev:  int or None

        If the revision history for the branch has changed, some of
        the RevisionNumber objects will no longer be valid.  These
        objects must be removed before the replacement RevisionNumbers
        can be created in the database.

        This function is expected to be called from within a transaction.
        """
        if from_rev is None:
            from_rev = len(self.bzr_history) + 1

        self.logger.debug("Truncating revision numbers from %d on", from_rev)
        revnos = RevisionNumber.select(AND(
            RevisionNumber.q.branchID == self.db_branch.id,
            RevisionNumber.q.sequence >= from_rev))
        didsomething = False
        for revno in revnos:
            revno.destroySelf()
            didsomething = True

        return didsomething


def main(branch_id):
    # Load branch with the given branch_id.
    trans_manager = initZopeless(dbuser="importd")
    status = 0

    # Prepare logger
    class Formatter(logging.Formatter):
        def format(self, record):
            if record.levelno != logging.INFO:
                record.prefix = record.levelname.lower()+": "
            else:
                record.prefix = ""
            return logging.Formatter.format(self, record)
    formatter = Formatter("%(prefix)s%(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger = logging.getLogger("BzrSync")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    try:
        bzrsync = BzrSync(trans_manager, branch_id, logger=logger)
    except NotFoundError:
        logger.error("Branch not found: %d" % branch_id)
        status = 1
    else:
        bzrsync.syncHistory()
    return status

if __name__ == '__main__':
    execute_zcml_for_scripts()

    if len(sys.argv) != 2:
        sys.exit("Usage: bzrsync.py <branch_id>")
    branch_id = int(sys.argv[1])
    status = main(branch_id)
    sys.exit(status)
