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

__metaclass__ = type
__all__ = ["BzrSync"]


class BzrSync:

    def __init__(self, branch_id):
        self.db_branch = Branch.get(branch_id)
        self.bzr_branch = BzrBranch.open(self.db_branch.url)
        self.bzr_history = self.bzr_branch.revision_history()
        self._admins = Person.selectOneBy(name="admins")
        self._seen_ids = {}

    def syncHistory(self, doparents=True):
        result = False
        if doparents:
            pending_parents = []
        else:
            pending_parents = None
        for revision_id in self.bzr_history:
            result |= self.syncRevision(revision_id, pending_parents)
        if pending_parents:
            self.syncPendingParents(pending_parents)
        return result

    def syncRevision(self, revision_id, pending_parents=None):
        if revision_id in self._seen_ids:
            return False
        self._seen_ids[revision_id] = True
        result = False
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
            result = True
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
                result = True
        return result

    def syncPendingParents(self, pending_parents, recurse=True):
        if recurse:
            pending_parents = list(pending_parents)
            sync_pending_parents = pending_parents
        else:
            sync_pending_parents = None
        while pending_parents:
            revision_id, parent_id = pending_parents.pop(0)
            self.syncRevision(parent_id, sync_pending_parents)
            db_revision = Revision.selectOneBy(revision_id=revision_id)
            db_parent = Revision.selectOneBy(revision_id=parent_id)
            if not RevisionParent.selectOneBy(revisionID=db_revision.id,
                                              parentID=db_parent.id):
                RevisionParent(revision=db_revision.id, parent=db_parent.id)


def main():
    txnManager = initZopeless(dbuser="importd")
    txnManager.begin()
    branch_id = int(sys.argv[1])
    BzrSync(branch_id).syncHistory()
    txnManager.commit()
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
