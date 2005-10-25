#!/usr/bin/python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

import sys
import os
from datetime import datetime
from pytz import UTC

from bzrlib.branch import Branch as BzrBranch

from canonical.lp import initZopeless
from canonical.launchpad.database import (
    Person, Branch, Revision, RevisionNumber, RevisionParent)

from importd.bzrsync import BzrSync


__metaclass__ = type
__all__ = ["BzrSync"]


class BzrSync:

    def __init__(self, trans_manager, branch_id):
        self.trans_manager = trans_manager
        self.db_branch = Branch.get(branch_id)
        self.bzr_branch = BzrBranch.open(self.db_branch.url)
        self.bzr_history = self.bzr_branch.revision_history()
        self._seen_ids = {}
        self._admins = Person.selectOneBy(name="admins")
        assert self._admins

    def syncHistory(self, doparents=True):
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
        if revision_id in self._seen_ids:
            return False
        self._seen_ids[revision_id] = True
        didsomething = False
        self.trans_manager.begin()
        db_revision = Revision.selectOneBy(revision_id=revision_id)
        if not db_revision:
            # Do we want a fixed offset timezone instead?
            bzr_revision = self.bzr_branch.get_revision(revision_id)
            revision_date = datetime.fromtimestamp(bzr_revision.timestamp +
                                                   bzr_revision.timezone,
                                                   tz=UTC)
            db_revision = Revision(revision_id=revision_id,
                                   log_body=bzr_revision.message,
                                   revision_date=revision_date,
                                   owner=self._admins.id,
                                   diff_adds=None, diff_deletes=None)
            didsomething = True
            if pending_parents is not None:
                for parent_id in bzr_revision.parent_ids:
                    pending_parents.append((revision_id, parent_id))
        if revision_id in self.bzr_history:
            bzr_revno = self.bzr_history.index(revision_id) + 1
            db_revno = RevisionNumber.selectOneBy(revisionID=db_revision.id,
                                                  branchID=self.db_branch.id)
            if not db_revno or db_revno.rev_no != bzr_revno:
                if db_revno:
                    db_revno.destroySelf()
                db_revno = RevisionNumber(rev_no=bzr_revno,
                                          revision=db_revision.id,
                                          branch=self.db_branch.id)
                didsomething = True
        if didsomething:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()
        return didsomething

    def syncPendingParents(self, pending_parents, recurse=True):
        didsomething = False
        if recurse:
            pending_parents = list(pending_parents)
            sync_pending_parents = pending_parents
        else:
            sync_pending_parents = None
        while pending_parents:
            revision_id, parent_id = pending_parents.pop(0)
            didsomething |= self.syncRevision(parent_id, sync_pending_parents)
            db_revision = Revision.selectOneBy(revision_id=revision_id)
            db_parent = Revision.selectOneBy(revision_id=parent_id)
            if not RevisionParent.selectOneBy(revisionID=db_revision.id,
                                              parentID=db_parent.id):
                self.trans_manager.begin()
                RevisionParent(revision=db_revision.id, parent=db_parent.id)
                self.trans_manager.commit()
                didsomething = True
        return didsomething


def main():
    trans_manager = initZopeless(dbuser="importd")
    branch_id = int(sys.argv[1])
    BzrSync(trans_manager, branch_id).syncHistory()
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
