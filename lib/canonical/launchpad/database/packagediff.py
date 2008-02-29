# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'PackageDiff',
    'PackageDiffSet',
    ]

from zope.interface import implements
from sqlobject import ForeignKey

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    IPackageDiff, IPackageDiffSet)


class PackageDiff(SQLBase):
    """A Package Diff request."""

    implements(IPackageDiff)

    _defaultOrder = ['id']

    date_requested = UtcDateTimeCol(notNull=False, default=UTC_NOW)

    requester = ForeignKey(
        dbName='requester', foreignKey='Person', notNull=True)

    from_source = ForeignKey(
        dbName="from_source", foreignKey='SourcePackageRelease', notNull=True)

    to_source = ForeignKey(
        dbName="to_source", foreignKey='SourcePackageRelease', notNull=True)

    date_fulfilled = UtcDateTimeCol(notNull=False, default=None)

    diff_content = ForeignKey(
        dbName="diff_content", foreignKey='LibraryFileAlias',
        notNull=False, default=None)

    @property
    def title(self):
        """See `IPackageDiff`."""
        return 'Package diff from %s to %s' % (
            self.from_source.title, self.to_source.title)

    def performDiff(self):
        """See `IPackageDiff`."""
        pass


class PackageDiffSet:
    """This class is to deal with Distribution related stuff"""

    implements(IPackageDiffSet)

    def __iter__(self):
        """Return all `PackageDiff`s sorted by date_requested."""
        diffset = PackageDiff.select(orderBy=['-date_requested'])
        return iter(diffset)

    def get(self, diff_id):
        """See `IPackageDiffSet`."""
        return PackageDiff.get(diff_id)
