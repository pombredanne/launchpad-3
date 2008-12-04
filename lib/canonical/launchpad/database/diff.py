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

from canonical.launchpad.interfaces.diff import (
    IDiff, IStaticDiff, IStaticDiffSource)
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


class Diff(SQLBase):
    """See `IDiff`."""

    implements(IDiff)

    diff_text = ForeignKey(foreignKey='LibraryFileAlias')

    diff_lines_count = IntCol()

    diffstat = StringCol()

    added_lines_count = IntCol()

    removed_lines_count = IntCol()

    @property
    def text(self):
        if self.diff_text is None:
            return ''
        else:
            self.diff_text.open()
            try:
                return self.diff_text.read()
            finally:
                self.diff_text.close()

    @classmethod
    def fromTrees(klass, from_tree, to_tree):
        """Create a Diff from two Bazaar trees.

        :from_tree: The old tree in the diff.
        :to_tree: The new tree in the diff.
        """
        diff_content = StringIO()
        show_diff_trees(from_tree, to_tree, diff_content, old_label='',
                        new_label='')
        size = diff_content.tell()
        diff_content.seek(0)
        return klass.fromFile(diff_content, size)

    @classmethod
    def fromFile(klass, diff_content, size):
        """Create a Diff from a textual diff.

        :diff_content: The diff text
        :size: The number of bytes in the diff text.
        """
        if size == 0:
            diff_text = None
        else:
            diff_text = getUtility(ILibraryFileAliasSet).create(
                'static.diff', size, diff_content, 'text/x-diff')
        return klass(diff_text=diff_text)


class StaticDiff(SQLBase):
    """A diff from one revision to another."""

    implements(IStaticDiff)

    classProvides(IStaticDiffSource)

    from_revision_id = StringCol()

    to_revision_id = StringCol()

    diff = ForeignKey(foreignKey='Diff', notNull=True)

    @classmethod
    def acquire(klass, from_revision_id, to_revision_id, repository):
        """See `IStaticDiffSource`."""
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

    @classmethod
    def acquireFromText(klass, from_revision_id, to_revision_id, text):
        """See `IStaticDiffSource`."""
        existing_diff = klass.selectOneBy(
            from_revision_id=from_revision_id, to_revision_id=to_revision_id)
        if existing_diff is not None:
            return existing_diff
        diff = Diff.fromFile(StringIO(text), len(text))
        return klass(
            from_revision_id=from_revision_id, to_revision_id=to_revision_id,
            diff=diff)

    def destroySelf(self):
        diff = self.diff
        SQLBase.destroySelf(self)
        diff.destroySelf()
