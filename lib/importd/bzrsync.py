#!/usr/bin/python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

import sys
import os
from datetime import datetime
from pytz import UTC

from bzrlib.branch import Branch as BzrBranch
from bzrlib.errors import NoSuchRevision

from canonical.lp import initZopeless
from canonical.launchpad.database import (
    Person, Branch, Revision, RevisionNumber, RevisionParent, RevisionAuthor)


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
            try:
                bzr_revision = self.bzr_branch.get_revision(revision_id)
            except NoSuchRevision:
                return didsomehting
            revision_date = datetime.fromtimestamp(bzr_revision.timestamp +
                                                   bzr_revision.timezone,
                                                   tz=UTC)
            db_author = RevisionAuthor.selectOneBy(name=bzr_revision.committer)
            if not db_author:
                db_author = RevisionAuthor(name=bzr_revision.committer)
            db_revision = Revision(revision_id=revision_id,
                                   log_body=bzr_revision.message,
                                   revision_date=revision_date,
                                   revision_author=db_author.id,
                                   owner=self._admins.id)
            if pending_parents is not None:
                for sequence, parent_id in enumerate(bzr_revision.parent_ids):
                    pending_parents.append((revision_id, sequence, parent_id))
            didsomething = True
        if revision_id in self.bzr_history:
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
        didsomething = False
        if recurse:
            pending_parents = list(pending_parents)
            sync_pending_parents = pending_parents
        else:
            sync_pending_parents = None
        while pending_parents:
            revision_id, sequence, parent_id = pending_parents.pop(0)
            didsomething |= self.syncRevision(parent_id, sync_pending_parents)
            db_revision = Revision.selectOneBy(revision_id=revision_id)
            db_parent = RevisionParent.selectOneBy(revisionID=db_revision.id,
                                                   parent_id=parent_id)
            if db_parent:
                assert db_parent.sequence == sequence, \
                    "This revision was previously imported with this parent" \
                    " in a different position. Something is VERY wrong!"
            else:
                self.trans_manager.begin()
                RevisionParent(revision=db_revision.id, parent_id=parent_id,
                               sequence=sequence)
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
