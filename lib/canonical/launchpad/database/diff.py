# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'StaticDiff', 'StaticDiffJob', 'StaticDiffJobSource']

from cStringIO import StringIO

from bzrlib.branch import Branch
from bzrlib.diff import show_diff_trees
from bzrlib.revisionspec import RevisionSpec
from sqlobject import ForeignKey, IntCol, StringCol
from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces.diff import (
    IDiff, IStaticDiff, IStaticDiffSource, IStaticDiffJob,
    IStaticDiffJobSource)
from canonical.launchpad.database.job import Job
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


class StaticDiffJob(SQLBase):

    implements(IStaticDiffJob)

    job = ForeignKey(foreignKey='Job', notNull=True)

    branch = ForeignKey(foreignKey='Branch', notNull=True)

    from_revision_spec = StringCol(notNull=True)

    to_revision_spec = StringCol(notNull=True)

    def __init__(self, **kwargs):
        kwargs['job']=Job()
        SQLBase.__init__(self, **kwargs)

    def destroySelf(self):
        SQLBase.destroySelf(self)
        self.job.destroySelf()

    def _get_revision_id(self, bzr_branch, spec_string):
        spec = RevisionSpec.from_string(spec_string)
        return spec.as_revision_id(bzr_branch)

    def run(self):
        """See IStaticDiffJob."""
        self.job.start()
        bzr_branch = Branch.open(self.branch.warehouse_url)
        from_revision_id=self._get_revision_id(
            bzr_branch, self.from_revision_spec)
        to_revision_id=self._get_revision_id(
            bzr_branch, self.to_revision_spec)
        static_diff = StaticDiff.acquire(
            from_revision_id, to_revision_id, bzr_branch.repository)
        self.job.complete()
        return static_diff


class StaticDiffJobSource:

    implements(IStaticDiffJobSource)
    @staticmethod
    def create(branch, from_revision_spec, to_revision_spec):
        return StaticDiffJob(
            branch=branch, from_revision_spec=from_revision_spec,
            to_revision_spec=to_revision_spec)
