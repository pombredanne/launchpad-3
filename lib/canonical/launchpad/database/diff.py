# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'StaticDiff',]

from cStringIO import StringIO

from bzrlib.branch import Branch
from bzrlib.diff import show_diff_trees
from bzrlib.revisionspec import RevisionSpec
from sqlobject import ForeignKey, IntCol, StringCol
from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IDiff, IStaticDiff, IStaticDiffSource)
from canonical.launchpad.interfaces import ILibraryFileAliasSet


class Diff(SQLBase):

    implements(IDiff)

    diff_text = ForeignKey(foreignKey='LibraryFileAlias', notNull=True)

    diff_lines_count = IntCol()

    diffstat = StringCol()

    added_lines_count = IntCol()

    removed_lines_count = IntCol()

    @classmethod
    def fromTrees(klass, from_tree, to_tree):
        diff_content = StringIO()
        show_diff_trees(from_tree, to_tree, diff_content, old_label='',
                        new_label='')
        size = diff_content.tell()
        if size == 0:
            diff_content.write(' ')
            size = 1
        diff_content.seek(0)
        x = getUtility(ILibraryFileAliasSet).create('meeple',
            size, diff_content, 'text/x-diff')
        return klass(diff_text=x)


class StaticDiff(SQLBase):
    """A diff from one revision to another."""

    implements(IStaticDiff)

    classProvides(IStaticDiffSource)

    from_revision_id = StringCol()

    to_revision_id = StringCol()

    diff = ForeignKey(foreignKey='Diff', notNull=True)

    @classmethod
    def acquire(klass, from_revision_id, to_revision_id, repository):
        existing_diff = klass.selectOneBy(
            from_revision_id=from_revision_id, to_revision_id=to_revision_id)
        if existing_diff is not None:
            return existing_diff
        from_tree = repository.revision_tree(from_revision_id)
        to_tree = repository.revision_tree(to_revision_id)
        diff = Diff.fromTrees(from_tree, to_tree)
        return klass(
            from_revision_id=from_revision_id, to_revision_id=to_revision_id,
            diff=diff)

    def destroySelf(self):
        diff = self.diff
        SQLBase.destroySelf(self)
        diff.destroySelf()
