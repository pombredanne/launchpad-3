#!/usr/bin/python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""
This module/script is able to import data from a bzr branch
into the Launchpad database.
"""

__metaclass__ = type
__all__ = ["BzrSync"]


import sys
import os
import logging
from datetime import datetime
from pytz import UTC
from sqlobject import SQLObjectNotFound

from bzrlib.branch import Branch as BzrBranch
from bzrlib.errors import NoSuchRevision

from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.database import (
    Person, Branch, Revision, RevisionNumber, RevisionParent, RevisionAuthor)
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from zope.component import getUtility


class BzrSync:
    """Class to import bzr branches into the database

    The purpose of this class is to import data from a bzr branch
    into the Launchpad database.
    """

    def __init__(self, trans_manager, branch_id, logger=None):
        self.trans_manager = trans_manager
        try:
            self.db_branch = Branch.get(branch_id)
        except SQLObjectNotFound:
            raise KeyError, "Branch not found"
        self.bzr_branch = BzrBranch.open(self.db_branch.url)
        self.bzr_history = self.bzr_branch.revision_history()
        self._seen_ids = set()
        self._admin = getUtility(ILaunchpadCelebrities).admin

        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

    def syncHistory(self, doparents=True):
        """Load all revisions for the branch history

        If doparents is true, synchronize also parents not in the history.
        """

        self.logger.info("Synchronizing history for branch: %s"
                         % self.db_branch.url)

        # Keep track if something was actually loaded in the database.
        didsomething = False

        if doparents:
            pending_parents = []
        else:
            pending_parents = None

        for revision_id in self.bzr_history:
            didsomething |= self.syncRevision(revision_id, pending_parents)
        if pending_parents:
            didsomething |= self.syncPendingParents(pending_parents)

        return didsomething

    def syncRevision(self, revision_id, pending_parents=None):
        """Load revision with the given revision_id

        If pending_parents is a list, information about the revision
        parents will be appended to the list, so that they may be
        processed later by syncPendingParents().
        """

        # Prevent the same revision from being synchronized twice.
        # This may happen when processing parents, for instance.
        if revision_id in self._seen_ids:
            return False
        self._seen_ids.add(revision_id)
        
        self.logger.info("Synchronizing revision: %s" % revision_id)

        # If didsomething is True, new information was found and
        # loaded into the database.
        didsomething = False

        try:
            bzr_revision = self.bzr_branch.get_revision(revision_id)
        except NoSuchRevision:
            return didsomething

        self.trans_manager.begin()

        db_revision = Revision.selectOneBy(revision_id=revision_id)
        if not db_revision:
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
            didsomething = True

        if pending_parents is not None:
            # Caller requested to be informed about pending parents.
            # Provide information about them. Notice that the database
            # scheme was changed to not use the parent_id as a foreign
            # key, so they could be loaded right here, and just loading
            # the revision themselves postponed to avoid recursion.
            seen_parent_ids = set()
            for sequence, parent_id in enumerate(bzr_revision.parent_ids):
                if parent_id not in seen_parent_ids:
                    seen_parent_ids.add(parent_id)
                    pending_parents.append((revision_id, sequence, parent_id))

        if revision_id in self.bzr_history:
            # Revision is in history, so append it to the RevisionNumber
            # table as well, if not yet there.
            bzr_revno = self.bzr_history.index(revision_id) + 1
            db_revno = RevisionNumber.selectOneBy(revisionID=db_revision.id,
                                                  branchID=self.db_branch.id)
            if not db_revno or db_revno.sequence != bzr_revno:
                if db_revno:
                    db_revno.destroySelf()
                db_revno = RevisionNumber(sequence=bzr_revno,
                                          revision=db_revision.id,
                                          branch=self.db_branch.id)
                didsomething = True

        if didsomething:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

        return didsomething

    def syncPendingParents(self, pending_parents, recurse=True):
        """Load parents with the information provided by syncRevision()

        If recurse is true, parents of parents will be loaded as well.
        """
        # Keep track if something was actually loaded in the database.
        didsomething = False

        if recurse:
            pending_parents = list(pending_parents)
            sync_pending_parents = pending_parents
        else:
            sync_pending_parents = None

        while pending_parents:
            # Pop each element from the pending_parents queue and process it.
            # If recurse is True, syncRevision() may append additional
            # items to the list, which will be processed as well.
            revision_id, sequence, parent_id = pending_parents.pop(0)
            didsomething |= self.syncRevision(parent_id, sync_pending_parents)
            db_revision = Revision.selectOneBy(revision_id=revision_id)
            db_parent = RevisionParent.selectOneBy(revisionID=db_revision.id,
                                                   parent_id=parent_id)
            if db_parent:
                assert db_parent.sequence == sequence, (
                    "Revision %r already has parent %r  with index %d. But we"
                    " tried to import this parent again with index %d."
                    % (db_revision.revision_id, parent_id,
                       db_parent.sequence, sequence))
            else:
                self.trans_manager.begin()
                RevisionParent(revision=db_revision.id, parent_id=parent_id,
                               sequence=sequence)
                self.trans_manager.commit()
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
        bzrsync = BzrSync(trans_manager, branch_id, logger)
    except KeyError, e:
        # Branch not found
        logger.error(unicode(e.args[0]))
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
