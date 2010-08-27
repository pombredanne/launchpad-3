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
    Unicode,
    )
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

    last_package_diff_id = Int(
        name='last_package_diff', allow_none=True)
    last_package_diff = Reference(
        last_package_diff_id, 'PackageDiff.id')

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

        diff.activity_log = u""
        diff.appendActivityLog(
            "Initial parent/derived versions: %s" % diff._getVersions())
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
    def activity_log(self):
        """See `IDistroSeriesDifference`."""
        return u""

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

    def _getVersions(self):
        """Helper method returning versions string."""
        src_pub_ver = parent_src_pub_ver = "-"
        if self.source_pub:
            src_pub_ver = self.source_pub.source_package_version
        if self.parent_source_pub is not None:
            parent_src_pub_ver = self.parent_source_pub.source_package_version
        return parent_src_pub_ver + "/" + src_pub_ver

    def appendActivityLog(self, message, user=None):
        """See `IDistroSeriesDifference`."""
        username = " "
        if user is not None:
            username += user.name

        self.activity_log += (
            "%(datestamp)s%(username)s: %(message)s\n" % {
            'datestamp': datetime.strftime(datetime.now(), "%Y-%m-%d"),
            'username': username,
            'message': message,
            })

    def updateDifferenceType(self):
        """See `IDistroSeriesDifference`."""
        if self.source_pub is None:
            new_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        elif self.parent_source_pub is None:
            new_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        else:
            new_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS

        if new_type == self.difference_type:
            return False

        self.difference_type = new_type
        self.appendActivityLog(
            "Difference type changed to '%s'. Parent/derived versions: %s" % (
                new_type.title,
                self._getVersions(),
                ))
        return True
