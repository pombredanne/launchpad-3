# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'PreviewDiff', 'StaticDiff']

from cStringIO import StringIO

from bzrlib.diff import show_diff_trees
from lazr.delegates import delegates
from sqlobject import ForeignKey, IntCol, StringCol
from storm.locals import Int, Reference, Storm, Unicode
from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces.diff import (
    IDiff, IPreviewDiff, IStaticDiff, IStaticDiffSource)
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

    def update(self, diff_content, diffstat, filename):
        """Update the diff content and diffstat."""
        alias = getUtility(ILibraryFileAliasSet).create(
            filename, len(diff_content), StringIO(diff_content),
            'text/x-diff')
        self.diff_text = alias
        self.diffstat = diffstat


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


class PreviewDiff(Storm):
    """See `IPreviewDiff`."""
    implements(IPreviewDiff)
    delegates(IDiff, context='diff')
    __storm_table__ = 'PreviewDiff'


    id = Int(primary=True)

    diff_id = Int(name='diff')
    diff = Reference(diff_id, 'Diff.id')

    source_revision_id = Unicode(allow_none=False)

    target_revision_id = Unicode(allow_none=False)

    dependent_revision_id = Unicode()

    conflicts = Unicode()

    branch_merge_proposal = Reference(
        "<primary key>", "BranchMergeProposal.preview_diff_id",
        on_remote=True)

    def update(self, diff_content, diffstat,
               source_revision_id, target_revision_id,
               dependent_revision_id, conflicts):
        self.source_revision_id = source_revision_id
        self.target_revision_id = target_revision_id
        if dependent_revision_id is None:
            self.dependent_revision_id = u'OOPS'
        else:
            self.dependent_revision_id = dependent_revision_id
        self.conflicts = conflicts

        self.diff.update(diff_content, diffstat, 'merge.diff')
