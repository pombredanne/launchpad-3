# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database classes for a difference between two distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesDifference',
    ]

from lazr.enum import DBItem
from storm.expr import Desc
from storm.locals import (
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
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
from lp.registry.model.distroseriesdifferencecomment import (
    DistroSeriesDifferenceComment)


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

    parent_package_diff_id = Int(
        name='parent_package_diff', allow_none=True)
    parent_package_diff = Reference(
        parent_package_diff_id, 'PackageDiff.id')

    status = DBEnum(name='status', allow_none=False,
                    enum=DistroSeriesDifferenceStatus)
    difference_type = DBEnum(name='difference_type', allow_none=False,
                             enum=DistroSeriesDifferenceType)
    source_version = Unicode(name='source_version', allow_none=True)
    parent_source_version = Unicode(name='parent_source_version',
                                    allow_none=True)

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

        source_pub = diff.source_pub
        if source_pub is not None:
            diff.source_version = source_pub.source_package_version
        parent_source_pub = diff.parent_source_pub
        if parent_source_pub is not None:
            diff.parent_source_version = (
                parent_source_pub.source_package_version)

        return store.add(diff)

    @staticmethod
    def getForDistroSeries(
        distro_series,
        difference_type=DistroSeriesDifferenceType.DIFFERENT_VERSIONS,
        status=None):
        """See `IDistroSeriesDifferenceSource`."""
        if status is None:
            status = (
                DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
                )
        elif isinstance(status, DBItem):
            status = (status, )

        return IStore(DistroSeriesDifference).find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == distro_series,
            DistroSeriesDifference.difference_type == difference_type,
            DistroSeriesDifference.status.is_in(status))

    @property
    def source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub()

    @property
    def parent_source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub(for_parent=True)

    @property
    def owner(self):
        """See `IDistroSeriesDifference`."""
        return self.derived_series.owner

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

    def updateStatusAndType(self):
        """See `IDistroSeriesDifference`."""
        source_pub = self.source_pub
        parent_source_pub = self.parent_source_pub
        if source_pub is None:
            new_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        elif parent_source_pub is None:
            new_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        else:
            new_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS

        updated = False
        if new_type != self.difference_type:
            updated = True
            self.difference_type = new_type

        # Check if its changed first and un-blacklist.
        self.source_version = source_pub.source_package_version
        self.parent_source_version = parent_source_pub.source_package_version
        if self.status == DistroSeriesDifferenceStatus.RESOLVED:
            if self.source_version != self.parent_source_version:
                updated = True
                self.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
        else:
            if self.source_version == self.parent_source_version:
                updated = True
                self.status = DistroSeriesDifferenceStatus.RESOLVED

        return updated

    def addComment(self, owner, comment):
        """See `IDistroSeriesDifference`."""
        return getUtility(IDistroSeriesDifferenceCommentSource).new(
            self, owner, comment)

    def getComments(self):
        """See `IDistroSeriesDifference`."""
        DSDComment = DistroSeriesDifferenceComment
        comments = IStore(DSDComment).find(
            DistroSeriesDifferenceComment,
            DSDComment.distro_series_difference == self)
        return comments.order_by(Desc(DSDComment.id))
