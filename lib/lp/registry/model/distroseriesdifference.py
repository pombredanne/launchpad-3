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
from lp.archivepublisher.debversion import Version
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.errors import (
    DistroSeriesDifferenceError,
    NotADerivedSeriesError,
    )
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceCommentSource,
    )
from lp.registry.model.distroseriesdifferencecomment import (
    DistroSeriesDifferenceComment,
    )
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.propertycache import (
    cachedproperty,
    clear_property_cache,
    )
from lp.soyuz.enums import PackageDiffStatus


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
    base_version = Unicode(name='base_version', allow_none=True)

    @staticmethod
    def new(derived_series, source_package_name):
        """See `IDistroSeriesDifferenceSource`."""
        if derived_series.parent_series is None:
            raise NotADerivedSeriesError()

        store = IMasterStore(DistroSeriesDifference)
        diff = DistroSeriesDifference()
        diff.derived_series = derived_series
        diff.source_package_name = source_package_name

        # The status and type is set to default values - they will be
        # updated appropriately during the update() call.
        diff.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
        diff.difference_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS
        diff.update()

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

    @staticmethod
    def getByDistroSeriesAndName(distro_series, source_package_name):
        """See `IDistroSeriesDifferenceSource`."""
        return IStore(DistroSeriesDifference).find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == distro_series,
            DistroSeriesDifference.source_package_name == (
                SourcePackageName.id),
            SourcePackageName.name == source_package_name).one()

    @cachedproperty
    def source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub()

    @cachedproperty
    def parent_source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub(for_parent=True)

    @cachedproperty
    def base_source_pub(self):
        """See `IDistroSeriesDifference`."""
        if self.base_version is not None:
            pubs = self.derived_series.main_archive.getPublishedSources(
                name=self.source_package_name.name,
                version=self.base_version,
                distroseries=self.derived_series)
            # We know there is a base version published in the distroseries'
            # main archive.
            return pubs.first()

        return None

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

    def _getPackageDiffURL(self, package_diff):
        """Check status and return URL if appropriate."""
        if package_diff is None or (
            package_diff.status != PackageDiffStatus.COMPLETED):
            return None

        return package_diff.diff_content.getURL()

    @property
    def package_diff_url(self):
        """See `IDistroSeriesDifference`."""
        return self._getPackageDiffURL(self.package_diff)

    @property
    def parent_package_diff_url(self):
        """See `IDistroSeriesDifference`."""
        return self._getPackageDiffURL(self.parent_package_diff)

    def _getLatestSourcePub(self, for_parent=False):
        """Helper to keep source_pub/parent_source_pub DRY."""
        distro_series = self.derived_series
        if for_parent:
            distro_series = self.derived_series.parent_series

        pubs = distro_series.getPublishedSources(
            self.source_package_name, include_pending=True)

        # The most recent published source is the first one.
        return pubs.first()

    def update(self):
        """See `IDistroSeriesDifference`."""
        # Updating is expected to be a heavy operation (not called
        # during requests). We clear the cache beforehand - even though
        # it is not currently necessary - so that in the future it
        # won't cause a hard-to find bug if a script ever creates a
        # difference, copies/publishes a new version and then calls
        # update() (like the tests for this method do).
        clear_property_cache(self)
        self._updateType()
        updated = self._updateVersionsAndStatus()
        return updated

    def _updateType(self):
        """Helper for update() interface method.

        Check whether the presence of a source in the derived or parent
        series has changed (which changes the type of difference).
        """
        if self.source_pub is None:
            new_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        elif self.parent_source_pub is None:
            new_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        else:
            new_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS

        if new_type != self.difference_type:
            self.difference_type = new_type

    def _updateVersionsAndStatus(self):
        """Helper for the update() interface method.

        Check whether the status of this difference should be updated.
        """
        updated = False
        new_source_version = new_parent_source_version = None
        if self.source_pub:
            new_source_version = self.source_pub.source_package_version
            if self.source_version != new_source_version:
                self.source_version = new_source_version
                updated = True
                # If the derived version has change and the previous version
                # was blacklisted, then we remove the blacklist now.
                if self.status == (
                    DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT):
                    self.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
        if self.parent_source_pub:
            new_parent_source_version = (
                self.parent_source_pub.source_package_version)
            if self.parent_source_version != new_parent_source_version:
                self.parent_source_version = new_parent_source_version
                updated = True

        # If this difference was resolved but now the versions don't match
        # then we re-open the difference.
        if self.status == DistroSeriesDifferenceStatus.RESOLVED:
            if self.source_version != self.parent_source_version:
                updated = True
                self.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
        # If this difference was needing attention, or the current version
        # was blacklisted and the versions now match we resolve it. Note:
        # we don't resolve it if this difference was blacklisted for all
        # versions.
        elif self.status in (
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT):
            if self.source_version == self.parent_source_version:
                updated = True
                self.status = DistroSeriesDifferenceStatus.RESOLVED

        if self._updateBaseVersion():
            updated = True

        return updated

    def _updateBaseVersion(self):
        """Check for the most-recently published common version.

        Return whether the record was updated or not.
        """
        if self.difference_type != (
            DistroSeriesDifferenceType.DIFFERENT_VERSIONS):
            return False

        # Find all source package releases for the derived and parent
        # series and get the most recent common version.
        derived_sprs = self.source_pub.meta_sourcepackage.distinctreleases
        derived_versions = [
            Version(spr.version) for spr in derived_sprs]

        parent_sourcepkg = self.parent_source_pub.meta_sourcepackage
        parent_sprs = parent_sourcepkg.distinctreleases
        parent_versions = [
            Version(spr.version) for spr in parent_sprs]

        common_versions = list(
            set(derived_versions).intersection(parent_versions))
        if common_versions:
            common_versions.sort()
            self.base_version = unicode(common_versions.pop())
            return True

        if self.base_version is None:
            return False
        else:
            self.base_version = None
            return True

    def addComment(self, commenter, comment):
        """See `IDistroSeriesDifference`."""
        return getUtility(IDistroSeriesDifferenceCommentSource).new(
            self, commenter, comment)

    def getComments(self):
        """See `IDistroSeriesDifference`."""
        DSDComment = DistroSeriesDifferenceComment
        comments = IStore(DSDComment).find(
            DistroSeriesDifferenceComment,
            DSDComment.distro_series_difference == self)
        return comments.order_by(Desc(DSDComment.id))

    def blacklist(self, all=False):
        """See `IDistroSeriesDifference`."""
        if all:
            self.status = DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS
        else:
            self.status = DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT

    def unblacklist(self):
        """See `IDistroSeriesDifference`."""
        self.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
        self.update()

    def requestPackageDiffs(self, requestor):
        """See `IDistroSeriesDifference`."""
        if (self.base_source_pub is None or self.source_pub is None or
            self.parent_source_pub is None):
            raise DistroSeriesDifferenceError(
                "A derived, parent and base version are required to "
                "generate package diffs.")
        base_spr = self.base_source_pub.sourcepackagerelease
        derived_spr = self.source_pub.sourcepackagerelease
        parent_spr = self.parent_source_pub.sourcepackagerelease
        self.package_diff = base_spr.requestDiffTo(
            requestor, to_sourcepackagerelease=derived_spr)
        self.parent_package_diff = base_spr.requestDiffTo(
            requestor, to_sourcepackagerelease=parent_spr)
