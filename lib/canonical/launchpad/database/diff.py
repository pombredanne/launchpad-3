# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'StaticDiffReference']

from sqlobject import ForeignKey, IntCol, StringCol
from zope.interface import implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IDiff, IStaticDiffReference

class Diff(SQLBase):

    implements(IDiff)

    diff_text = ForeignKey(foreignKey='LibraryFileAlias', notNull=True)

    diff_lines_count = IntCol()

    diffstat = StringCol()

    added_lines_count = IntCol()

    removed_lines_count = IntCol()


class StaticDiffReference(SQLBase):

    implements(IStaticDiffReference)
