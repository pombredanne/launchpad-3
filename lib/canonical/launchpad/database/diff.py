# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'StaticDiff', 'StaticDiffJob']

from cStringIO import StringIO

from bzrlib.branch import Branch
from bzrlib.diff import show_diff_trees
from bzrlib.revisionspec import RevisionSpec
from sqlobject import ForeignKey, IntCol, StringCol
from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IDiff, IStaticDiff, IStaticDiffJob
from canonical.launchpad.interfaces import ILibraryFileAliasSet


class Diff(SQLBase):

    implements(IDiff)

    diff_text = ForeignKey(foreignKey='LibraryFileAlias', notNull=True)

    diff_lines_count = IntCol()

    diffstat = StringCol()

    added_lines_count = IntCol()

    removed_lines_count = IntCol()

    @classmethod
    def fromFile(klass, diff_file, size):
        x = getUtility(ILibraryFileAliasSet).create('meeple',
            size, diff_file, 'text/x-diff')
        return klass(diff_text=x)


class StaticDiff(SQLBase):
    """A diff from one revision to another."""

    implements(IStaticDiff)

    from_revision_id = StringCol()

    to_revision_id = StringCol()

    diff = ForeignKey(foreignKey='Diff', notNull=True)


class StaticDiffJob(SQLBase):

    implements(IStaticDiffJob)

    branch = ForeignKey(foreignKey='Branch', notNull=True)

    from_revision_spec = StringCol(notNull=True)

    to_revision_spec = StringCol(notNull=True)

    def _get_revision_id(self, bzr_branch, spec_string):
        spec = RevisionSpec.from_string(spec_string)
        return spec.as_revision_id(bzr_branch)

    def run(self):
        """See IStaticDiffJob."""
        bzr_branch = Branch.open(self.branch.warehouse_url)
        from_revision_id=self._get_revision_id(
            bzr_branch, self.from_revision_spec)
        to_revision_id=self._get_revision_id(
            bzr_branch, self.to_revision_spec)
        from_tree = bzr_branch.repository.revision_tree(from_revision_id)
        to_tree = bzr_branch.repository.revision_tree(to_revision_id)
        diff_content = StringIO()
        show_diff_trees(from_tree, to_tree, diff_content, old_label='',
                        new_label='')
        size = diff_content.tell()
        if size == 0:
            diff_content.write(' ')
            size = 1
        diff_content.seek(0)
        diff = Diff.fromFile(diff_content, size)
        return StaticDiff(
            from_revision_id=from_revision_id, to_revision_id=to_revision_id,
            diff=diff)
