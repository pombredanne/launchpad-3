# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'StaticDiff', 'StaticDiffJob']

from bzrlib.branch import Branch
from sqlobject import ForeignKey, IntCol, StringCol
from zope.interface import implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IDiff, IStaticDiff, IStaticDiffJob

class Diff(SQLBase):

    implements(IDiff)

    diff_text = ForeignKey(foreignKey='LibraryFileAlias', notNull=True)

    diff_lines_count = IntCol()

    diffstat = StringCol()

    added_lines_count = IntCol()

    removed_lines_count = IntCol()


class StaticDiff(SQLBase):
    """A diff from one revision to another."""

    implements(IStaticDiff)

    from_revision_id = StringCol()

    to_revision_id = StringCol()


class StaticDiffJob(SQLBase):

    implements(IStaticDiffJob)

    def run(self):
        """See IStaticDiffJob."""
        bzr_branch = Branch.open(self.branch.warehouse_url)
        return StaticDiff()
