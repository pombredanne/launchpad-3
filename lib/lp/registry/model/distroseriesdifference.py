# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database classes for a difference between two distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesDifference',
    ]

from itertools import chain
from operator import itemgetter

import apt_pkg
from debian.changelog import (
    Changelog,
    Version,
    )
from lazr.enum import DBItem
from sqlobject import StringCol
from storm.exceptions import NotOneError
from storm.expr import (
    And,
    Column,
    Desc,
    Table,
    )
from storm.locals import (
    Int,
    Reference,
    )
from storm.zope.interfaces import IResultSet
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import DBEnum
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from lp.services.messages.model.message import Message
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.errors import (
    DistroSeriesDifferenceError,
    MultipleParentsForDerivedSeriesError,
    NotADerivedSeriesError,
    )
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceCommentSource,
    )
from lp.registry.interfaces.distroseriesparent import IDistroSeriesParentSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.distroseriesdifferencecomment import (
    DistroSeriesDifferenceComment,
    )
from lp.registry.model.gpgkey import GPGKey
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database import bulk
from lp.services.database.stormbase import StormBase
from lp.services.propertycache import (
    cachedproperty,
    clear_property_cache,
    get_property_cache,
    )
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageDiffStatus,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.packagediff import IPackageDiffSet
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.distroseriessourcepackagerelease import (
    DistroSeriesSourcePackageRelease,
    )
from lp.soyuz.model.packageset import Packageset
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


def most_recent_publications(dsds, in_parent, statuses, match_version=False):
    """The most recent publications for the given `DistroSeriesDifference`s.

    Returns an `IResultSet` that yields two columns: `SourcePackageName.id`
    and `SourcePackagePublishingHistory`.

    :param dsds: An iterable of `DistroSeriesDifference` instances.
    :param in_parent: A boolean indicating if we should look in the parent
        series' archive instead of the derived series' archive.
    """
    columns = (
        DistroSeriesDifference.source_package_name_id,
        SourcePackagePublishingHistory,
        )
    conditions = And(
        DistroSeriesDifference.id.is_in(dsd.id for dsd in dsds),
        SourcePackagePublishingHistory.archiveID == Archive.id,
        SourcePackagePublishingHistory.sourcepackagereleaseID == (
            SourcePackageRelease.id),
        SourcePackagePublishingHistory.status.is_in(statuses),
        SourcePackageRelease.sourcepackagenameID == (
            DistroSeriesDifference.source_package_name_id),
        )
    # Check in the parent archive or the child?
    if in_parent:
        conditions = And(
            conditions,
            DistroSeries.id == DistroSeriesDifference.parent_series_id,
            Archive.distributionID == DistroSeries.distributionID,
            Archive.purpose == ArchivePurpose.PRIMARY,
            )
    else:
        conditions = And(
            conditions,
            DistroSeries.id == DistroSeriesDifference.derived_series_id,
            Archive.distributionID == DistroSeries.distributionID,
            Archive.purpose == ArchivePurpose.PRIMARY,
            )
    # Do we match on DistroSeriesDifference.(parent_)source_version?
    if match_version:
        if in_parent:
            version_column = DistroSeriesDifference.parent_source_version
        else:
            version_column = DistroSeriesDifference.source_version
        conditions = And(
            conditions,
            SourcePackageRelease.version == version_column,
            )
    # The sort order is critical so that the DISTINCT ON clause selects the
    # most recent publication (i.e. the one with the highest id).
    order_by = (
        DistroSeriesDifference.source_package_name_id,
        Desc(SourcePackagePublishingHistory.id),
        )
    distinct_on = (
        DistroSeriesDifference.source_package_name_id,
        )
    store = IStore(SourcePackagePublishingHistory)
    return store.find(
        columns, conditions).order_by(*order_by).config(distinct=distinct_on)


def most_recent_comments(dsds):
    """The most recent comments for the given `DistroSeriesDifference`s.

    Returns an `IResultSet` that yields a single column of
        `DistroSeriesDifferenceComment`.

    :param dsds: An iterable of `DistroSeriesDifference` instances.
    """
    columns = (
        DistroSeriesDifferenceComment,
        Message,
        )
    conditions = And(
        DistroSeriesDifferenceComment
            .distro_series_difference_id.is_in(dsd.id for dsd in dsds),
        Message.id == DistroSeriesDifferenceComment.message_id)
    order_by = (
        DistroSeriesDifferenceComment.distro_series_difference_id,
        Desc(DistroSeriesDifferenceComment.id),
        )
    distinct_on = (
        DistroSeriesDifferenceComment.distro_series_difference_id,
        )
    store = IStore(DistroSeriesDifferenceComment)
    comments = store.find(
        columns, conditions).order_by(*order_by).config(distinct=distinct_on)
    return DecoratedResultSet(comments, itemgetter(0))


def packagesets(dsds, in_parent):
    """Return the packagesets for the given dsds inside the parent or
    the derived `DistroSeries`.

    Returns a dict with the corresponding packageset list for each dsd id.

    :param dsds: An iterable of `DistroSeriesDifference` instances.
    :param in_parent: A boolean indicating if we should look in the parent
        series' archive instead of the derived series' archive.
    """
    if len(dsds) == 0:
        return {}

    PackagesetSources = Table("PackageSetSources")
    FlatPackagesetInclusion = Table("FlatPackagesetInclusion")

    tables = IStore(Packageset).using(
        DistroSeriesDifference, Packageset,
        PackagesetSources, FlatPackagesetInclusion)
    results = tables.find(
        (DistroSeriesDifference.id, Packageset),
        Column("packageset", PackagesetSources) == (
            Column("child", FlatPackagesetInclusion)),
        Packageset.distroseries_id == (
            DistroSeriesDifference.parent_series_id if in_parent else
            DistroSeriesDifference.derived_series_id),
        Column("parent", FlatPackagesetInclusion) == Packageset.id,
        Column("sourcepackagename", PackagesetSources) == (
            DistroSeriesDifference.source_package_name_id),
        DistroSeriesDifference.id.is_in(dsd.id for dsd in dsds))
    results = results.order_by(
        Column("sourcepackagename", PackagesetSources),
        Packageset.name)

    grouped = {}
    for dsd_id, packageset in results:
        if dsd_id in grouped:
            grouped[dsd_id].append(packageset)
        else:
            grouped[dsd_id] = [packageset]

    return grouped


class DistroSeriesDifference(StormBase):
    """See `DistroSeriesDifference`."""
    implements(IDistroSeriesDifference)
    classProvides(IDistroSeriesDifferenceSource)
    __storm_table__ = 'DistroSeriesDifference'

    id = Int(primary=True)

    derived_series_id = Int(name='derived_series', allow_none=False)
    derived_series = Reference(
        derived_series_id, 'DistroSeries.id')

    parent_series_id = Int(name='parent_series', allow_none=False)
    parent_series = Reference(parent_series_id, 'DistroSeries.id')

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
    source_version = StringCol(dbName='source_version', notNull=False)
    parent_source_version = StringCol(dbName='parent_source_version',
                                      notNull=False)
    base_version = StringCol(dbName='base_version', notNull=False)

    @staticmethod
    def new(derived_series, source_package_name, parent_series=None):
        """See `IDistroSeriesDifferenceSource`."""
        if parent_series is None:
            try:
                dsps = getUtility(IDistroSeriesParentSet)
                dsp = dsps.getByDerivedSeries(
                    derived_series).one()
            except NotOneError:
                raise MultipleParentsForDerivedSeriesError()
            else:
                if dsp is None:
                    raise NotADerivedSeriesError()
                else:
                    parent_series = dsp.parent_series

        store = IMasterStore(DistroSeriesDifference)
        diff = DistroSeriesDifference()
        diff.derived_series = derived_series
        diff.parent_series = parent_series
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
        difference_type=None,
        source_package_name_filter=None,
        status=None,
        child_version_higher=False,
        parent_series=None):
        """See `IDistroSeriesDifferenceSource`."""
        if difference_type is None:
            difference_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS
        if status is None:
            status = (
                DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
                )
        elif isinstance(status, DBItem):
            status = (status, )

        conditions = [
            DistroSeriesDifference.derived_series == distro_series,
            DistroSeriesDifference.difference_type == difference_type,
            DistroSeriesDifference.status.is_in(status),
            DistroSeriesDifference.source_package_name ==
                SourcePackageName.id,
        ]

        if parent_series:
            conditions.extend([
               DistroSeriesDifference.parent_series == parent_series.id])

        if source_package_name_filter:
            conditions.extend([
               SourcePackageName.name == source_package_name_filter])

        if child_version_higher:
            conditions.extend([
                DistroSeriesDifference.source_version >
                    DistroSeriesDifference.parent_source_version])

        differences = IStore(DistroSeriesDifference).find(
            DistroSeriesDifference,
            And(*conditions)).order_by(SourcePackageName.name)

        def eager_load(dsds):
            active_statuses = (
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING,
                )
            source_pubs = dict(
                most_recent_publications(
                    dsds, statuses=active_statuses,
                    in_parent=False, match_version=False))
            parent_source_pubs = dict(
                most_recent_publications(
                    dsds, statuses=active_statuses,
                    in_parent=True, match_version=False))
            source_pubs_for_release = dict(
                most_recent_publications(
                    dsds, statuses=active_statuses,
                    in_parent=False, match_version=True))
            parent_source_pubs_for_release = dict(
                most_recent_publications(
                    dsds, statuses=active_statuses,
                    in_parent=True, match_version=True))

            latest_comment_by_dsd_id = dict(
                (comment.distro_series_difference_id, comment)
                for comment in most_recent_comments(dsds))
            latest_comments = latest_comment_by_dsd_id.values()

            # SourcePackageReleases of the parent and source pubs are often
            # referred to.
            sprs = bulk.load_related(
                SourcePackageRelease, chain(
                    source_pubs.itervalues(),
                    parent_source_pubs.itervalues(),
                    source_pubs_for_release.itervalues(),
                    parent_source_pubs_for_release.itervalues()),
                ("sourcepackagereleaseID",))

            # Get packagesets and parent_packagesets for each DSD.
            dsd_packagesets = packagesets(dsds, in_parent=False)
            dsd_parent_packagesets = packagesets(dsds, in_parent=True)

            for dsd in dsds:
                spn_id = dsd.source_package_name_id
                cache = get_property_cache(dsd)
                cache.source_pub = source_pubs.get(spn_id)
                cache.parent_source_pub = parent_source_pubs.get(spn_id)
                cache.packagesets = dsd_packagesets.get(dsd.id)
                cache.parent_packagesets = dsd_parent_packagesets.get(dsd.id)
                if spn_id in source_pubs_for_release:
                    spph = source_pubs_for_release[spn_id]
                    cache.source_package_release = (
                        DistroSeriesSourcePackageRelease(
                            dsd.derived_series,
                            spph.sourcepackagerelease))
                else:
                    cache.source_package_release = None
                if spn_id in parent_source_pubs_for_release:
                    spph = parent_source_pubs_for_release[spn_id]
                    cache.parent_source_package_release = (
                        DistroSeriesSourcePackageRelease(
                            dsd.parent_series, spph.sourcepackagerelease))
                else:
                    cache.parent_source_package_release = None
                cache.latest_comment = latest_comment_by_dsd_id.get(dsd.id)

            # SourcePackageRelease.uploader can end up getting the requester
            # for a source package recipe build.
            sprbs = bulk.load_related(
                SourcePackageRecipeBuild, sprs,
                ("source_package_recipe_build_id",))

            # SourcePackageRelease.uploader can end up getting the owner of
            # the DSC signing key.
            gpgkeys = bulk.load_related(GPGKey, sprs, ("dscsigningkeyID",))

            # Load DistroSeriesDifferenceComment owners,
            # SourcePackageRecipeBuild requesters and GPGKey owners.
            person_ids = set().union(
                (dsdc.message.ownerID for dsdc in latest_comments),
                (sprb.requester_id for sprb in sprbs),
                (gpgkey.ownerID for gpgkey in gpgkeys))
            uploaders = getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                person_ids, need_validity=True)
            list(uploaders)

            # Load SourcePackageNames.
            bulk.load_related(
                SourcePackageName, dsds, ("source_package_name_id",))

        return DecoratedResultSet(
            differences, pre_iter_hook=eager_load)

    @staticmethod
    def getByDistroSeriesNameAndParentSeries(distro_series,
                                             source_package_name,
                                             parent_series):
        """See `IDistroSeriesDifferenceSource`."""

        return IStore(DistroSeriesDifference).find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == distro_series,
            DistroSeriesDifference.parent_series == parent_series,
            DistroSeriesDifference.source_package_name == (
                SourcePackageName.id),
            SourcePackageName.name == source_package_name).one()

    @staticmethod
    def getSimpleUpgrades(distro_series):
        """See `IDistroSeriesDifferenceSource`.

        Eager-load related `ISourcePackageName` records.
        """
        differences = IStore(DistroSeriesDifference).find(
            (DistroSeriesDifference, SourcePackageName),
            DistroSeriesDifference.derived_series == distro_series,
            DistroSeriesDifference.difference_type ==
                DistroSeriesDifferenceType.DIFFERENT_VERSIONS,
            DistroSeriesDifference.status ==
                DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            DistroSeriesDifference.parent_source_version !=
                DistroSeriesDifference.base_version,
            DistroSeriesDifference.source_version ==
                DistroSeriesDifference.base_version,
            SourcePackageName.id ==
                DistroSeriesDifference.source_package_name_id)
        return DecoratedResultSet(differences, itemgetter(0))

    @staticmethod
    def collateDifferencesByParentArchive(differences):
        by_archive = dict()
        for difference in differences:
            archive = difference.parent_series.main_archive
            if archive in by_archive:
                by_archive[archive].append(difference)
            else:
                by_archive[archive] = [difference]
        return by_archive

    @cachedproperty
    def source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub()

    @cachedproperty
    def parent_source_pub(self):
        """See `IDistroSeriesDifference`."""
        return self._getLatestSourcePub(for_parent=True)

    def _getLatestSourcePub(self, for_parent=False):
        """Helper to keep source_pub/parent_source_pub DRY."""
        distro_series = self.derived_series
        if for_parent:
            distro_series = self.parent_series

        pubs = distro_series.getPublishedSources(
            self.source_package_name, include_pending=True)

        # The most recent published source is the first one.
        try:
            return pubs[0]
        except IndexError:
            return None

    @cachedproperty
    def base_source_pub(self):
        """See `IDistroSeriesDifference`."""
        if self.base_version is not None:
            parent = self.parent_series
            result = parent.main_archive.getPublishedSources(
                name=self.source_package_name.name,
                version=self.base_version).first()
            if result is None:
                # If the base version isn't in the parent, it may be
                # published in the child distroseries.
                child = self.derived_series
                result = child.main_archive.getPublishedSources(
                    name=self.source_package_name.name,
                    version=self.base_version).first()
            return result
        return None

    @property
    def owner(self):
        """See `IDistroSeriesDifference`."""
        return self.derived_series.owner

    @property
    def title(self):
        """See `IDistroSeriesDifference`."""
        parent_name = self.parent_series.displayname
        return ("Difference between distroseries '%(parent_name)s' and "
                "'%(derived_name)s' for package '%(pkg_name)s' "
                "(%(parent_version)s/%(source_version)s)" % {
                    'parent_name': parent_name,
                    'derived_name': self.derived_series.displayname,
                    'pkg_name': self.source_package_name.name,
                    'parent_version': self.parent_source_version,
                    'source_version': self.source_version,
                    })

    def getAncestry(self, spr):
        """Return the version ancestry for the given SPR, or None."""
        if spr.changelog is None:
            return None
        versions = set()
        # It would be nicer to use .versions() here, but it won't catch the
        # ValueError from malformed versions, and we don't want them leaking
        # into the ancestry.
        for raw_version in Changelog(spr.changelog.read())._raw_versions():
            try:
                version = Version(raw_version)
            except ValueError:
                continue
            versions.add(version)
        return versions

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

    @cachedproperty
    def packagesets(self):
        """See `IDistroSeriesDifference`."""
        if self.derived_series is not None:
            return list(getUtility(IPackagesetSet).setsIncludingSource(
                self.source_package_name, self.derived_series))
        else:
            return []

    @cachedproperty
    def parent_packagesets(self):
        """See `IDistroSeriesDifference`."""
        return list(getUtility(IPackagesetSet).setsIncludingSource(
            self.source_package_name, self.parent_series))

    @property
    def package_diff_status(self):
        """See `IDistroSeriesDifference`."""
        if self.package_diff is None:
            return None
        else:
            return self.package_diff.status

    @property
    def parent_package_diff_status(self):
        """See `IDistroSeriesDifference`."""
        if self.parent_package_diff is None:
            return None
        else:
            return self.parent_package_diff.status

    @cachedproperty
    def parent_source_package_release(self):
        return self._package_release(
            self.parent_series, self.parent_source_version)

    @cachedproperty
    def source_package_release(self):
        return self._package_release(
            self.derived_series, self.source_version)

    def _package_release(self, distro_series, version):
        statuses = (
            PackagePublishingStatus.PUBLISHED,
            PackagePublishingStatus.PENDING)
        pubs = distro_series.main_archive.getPublishedSources(
            name=self.source_package_name.name,
            version=version,
            status=statuses,
            distroseries=distro_series,
            exact_match=True)

        # Get the most recent publication (pubs are ordered by
        # (name, id)).
        pub = IResultSet(pubs).first()
        if pub is None:
            return None
        else:
            return DistroSeriesSourcePackageRelease(
                distro_series, pub.sourcepackagerelease)

    def update(self, manual=False):
        """See `IDistroSeriesDifference`."""
        # Updating is expected to be a heavy operation (not called
        # during requests). We clear the cache beforehand - even though
        # it is not currently necessary - so that in the future it
        # won't cause a hard-to find bug if a script ever creates a
        # difference, copies/publishes a new version and then calls
        # update() (like the tests for this method do).
        clear_property_cache(self)
        self._updateType()
        updated = self._updateVersionsAndStatus(manual=manual)
        if updated is True:
            self._setPackageDiffs()
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

    def _updateVersionsAndStatus(self, manual):
        """Helper for the update() interface method.

        Check whether the status of this difference should be updated.

        :param manual: Boolean, True if this is a user-requested change.
            This overrides auto-blacklisting.
        """
        # XXX 2011-05-20 bigjools bug=785657
        # This method needs updating to use some sort of state
        # transition dictionary instead of this crazy mess of
        # conditions.

        updated = False
        new_source_version = new_parent_source_version = None
        if self.source_pub:
            new_source_version = self.source_pub.source_package_version
            if self.source_version is None or apt_pkg.VersionCompare(
                    self.source_version, new_source_version) != 0:
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
            if self.parent_source_version is None or apt_pkg.VersionCompare(
                    self.parent_source_version,
                    new_parent_source_version) != 0:
                self.parent_source_version = new_parent_source_version
                updated = True

        if not self.source_pub or not self.parent_source_pub:
            # This is unlikely to happen in reality but return early so
            # that bad data cannot make us OOPS.
            return updated

        # If this difference was resolved but now the versions don't match
        # then we re-open the difference.
        if self.status == DistroSeriesDifferenceStatus.RESOLVED:
            if apt_pkg.VersionCompare(
                self.source_version, self.parent_source_version) < 0:
                # Higher parent version.
                updated = True
                self.status = DistroSeriesDifferenceStatus.NEEDS_ATTENTION
            elif (
                apt_pkg.VersionCompare(
                    self.source_version, self.parent_source_version) > 0
                and not manual):
                # The child was updated with a higher version so it's
                # auto-blacklisted.
                updated = True
                self.status = DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT
        # If this difference was needing attention, or the current version
        # was blacklisted and the versions now match we resolve it. Note:
        # we don't resolve it if this difference was blacklisted for all
        # versions.
        elif self.status in (
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT):
            if apt_pkg.VersionCompare(
                    self.source_version, self.parent_source_version) == 0:
                updated = True
                self.status = DistroSeriesDifferenceStatus.RESOLVED
            elif (
                apt_pkg.VersionCompare(
                    self.source_version, self.parent_source_version) < 0
                and not manual):
                # If the derived version is lower than the parent's, we
                # ensure the diff status is blacklisted.
                self.status = DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT

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

        ancestry = self.getAncestry(self.source_pub.sourcepackagerelease)
        parent_ancestry = self.getAncestry(
            self.parent_source_pub.sourcepackagerelease)

        # If the ancestry for the parent and the descendant is available, we
        # can reliably work out the most recent common ancestor using set
        # arithmetic.
        if ancestry is not None and parent_ancestry is not None:
            intersection = ancestry.intersection(parent_ancestry)
            if len(intersection) > 0:
                self.base_version = unicode(max(intersection))
                return True
        return False

    def _setPackageDiffs(self):
        """Set package diffs if they exist."""
        if self.base_version is None or self.base_source_pub is None:
            self.package_diff = None
            self.parent_package_diff = None
            return
        pds = getUtility(IPackageDiffSet)
        if self.source_pub is None:
            self.package_diff = None
        else:
            self.package_diff = pds.getDiffBetweenReleases(
                self.base_source_pub.sourcepackagerelease,
                self.source_pub.sourcepackagerelease)
        if self.parent_source_pub is None:
            self.parent_package_diff = None
        else:
            self.parent_package_diff = pds.getDiffBetweenReleases(
                self.base_source_pub.sourcepackagerelease,
                self.parent_source_pub.sourcepackagerelease)

    def addComment(self, commenter, comment):
        """See `IDistroSeriesDifference`."""
        return getUtility(IDistroSeriesDifferenceCommentSource).new(
            self, commenter, comment)

    @cachedproperty
    def latest_comment(self):
        """See `IDistroSeriesDifference`."""
        return self.getComments().first()

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
        self.update(manual=True)

    def requestPackageDiffs(self, requestor):
        """See `IDistroSeriesDifference`."""
        if (self.base_source_pub is None or self.source_pub is None or
            self.parent_source_pub is None):
            raise DistroSeriesDifferenceError(
                "A derived, parent and base version are required to "
                "generate package diffs.")
        if self.status == DistroSeriesDifferenceStatus.RESOLVED:
            raise DistroSeriesDifferenceError(
                "Can not generate package diffs for a resolved difference.")
        base_spr = self.base_source_pub.sourcepackagerelease
        derived_spr = self.source_pub.sourcepackagerelease
        parent_spr = self.parent_source_pub.sourcepackagerelease
        if self.source_version != self.base_version:
            self.package_diff = base_spr.requestDiffTo(
                requestor, to_sourcepackagerelease=derived_spr)
        if self.parent_source_version != self.base_version:
            self.parent_package_diff = base_spr.requestDiffTo(
                requestor, to_sourcepackagerelease=parent_spr)
