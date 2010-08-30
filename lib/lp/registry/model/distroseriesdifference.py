# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database classes for a difference between two distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesDifference',
    ]

from datetime import datetime

from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.exceptions import NotADerivedSeriesError
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceCommentSource,
    )


class DistroSeriesDifference(Storm):
    """See `DistroSeriesDifference`."""
    implements(IDistroSeriesDifference)
    classProvides(IDistroSeriesDifferenceSource)
    __storm_table__ = 'DistroSeriesDifference'

    id = Int(primary=True)

    derived_series_id = Int(name='derived_series', allow_none=False)
    derived_series = Reference(
        derived_series_id, 'DistroSeries.id')

    source_package_name_id = Int(
        name='source_package_name', allow_none=False)
    source_package_name = Reference(
        source_package_name_id, 'SourcePackageName.id')

    package_diff_id = Int(
        name='package_diff', allow_none=True)
    package_diff = Reference(
        package_diff_id, 'PackageDiff.id')

    status = DBEnum(name='status', allow_none=False,
                    enum=DistroSeriesDifferenceStatus)
    difference_type = DBEnum(name='difference_type', allow_none=False,
                             enum=DistroSeriesDifferenceType)

    @staticmethod
    def new(derived_series, source_package_name, difference_type,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION):
        """See `IDistroSeriesDifferenceSource`."""
        if derived_series.parent_series is None:
            raise NotADerivedSeriesError()

        store = IMasterStore(DistroSeriesDifference)
        diff = DistroSeriesDifference()
        diff.derived_series = derived_series
        diff.source_package_name = source_package_name
        diff.status = status
        diff.difference_type = difference_type

        return store.add(diff)

    @property
    def source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub()

    @property
    def parent_source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub(for_parent=True)

    @property
    def title(self):
        """See `IDistroSeriesDifference`."""
        parent_name = self.derived_series.parent_series.displayname
        return ("Difference between distroseries '%(parent_name)s' and "
                "'%(derived_name)s' for package '%(pkg_name)s' "
                "(%(parent_version)s/%(source_version)s)" % {
                    'parent_name': parent_name,
                    'derived_name': self.derived_series.displayname,
                    'pkg_name': self.source_package_name.name,
                    'parent_version': self.parent_source_version,
                    'source_version': self.source_version,
                    })

    def _getLatestSourcePub(self, for_parent=False):
        """Helper to keep source_pub/parent_source_pub DRY."""
        distro_series = self.derived_series
        if for_parent:
            distro_series = self.derived_series.parent_series

        pubs = distro_series.getPublishedSources(
            self.source_package_name, include_pending=True)

        # The most recent published source is the first one.
        if pubs:
            return pubs[0]
        else:
            return None

    @property
    def source_version(self):
        """See `IDistroSeriesDifference`."""
        if self.source_pub:
            return self.source_pub.source_package_version
        return ''

    @property
    def parent_source_version(self):
        """See `IDistroSeriesDifference`."""
        if self.parent_source_pub:
            return self.parent_source_pub.source_package_version
        return ''

    def updateStatusAndType(self):
        """See `IDistroSeriesDifference`."""
        if self.source_pub is None:
            new_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        elif self.parent_source_pub is None:
            new_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        else:
            new_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS

        updated = False
        if new_type != self.difference_type:
            updated = True
            self.difference_type = new_type

        version = self.source_version
        parent_version = self.parent_source_version
        if self.status == DistroSeriesDifferenceStatus.RESOLVED:
            if version != parent_version:
                updated = True
                self.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
        else:
            if version == parent_version:
                updated = True
                self.status = DistroSeriesDifferenceStatus.RESOLVED

        return updated

    def addComment(self, owner, comment):
        """See `IDistroSeriesDifference`."""
        return getUtility(IDistroSeriesDifferenceCommentSource).new(
            self, owner, comment)

    def getComments(self):
        """See `IDistroSeriesDifference`."""
        comment_source = getUtility(IDistroSeriesDifferenceCommentSource)
        return comment_source.getForDifference(self)
