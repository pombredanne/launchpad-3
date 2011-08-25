# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Database class for table Archive."""

__metaclass__ = type

__all__ = [
    'Archive',
    'ArchiveSet',
    ]

from operator import attrgetter
import re

from lazr.lifecycle.event import ObjectCreatedEvent
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    StringCol,
    )
from sqlobject.sqlbuilder import SQLConstant
from storm.expr import (
    And,
    Desc,
    Or,
    Select,
    SQL,
    Sum,
    )
from storm.locals import (
    Count,
    Join,
    )
from storm.store import Store
from zope.component import getUtility
from zope.event import notify
from zope.interface import (
    alsoProvides,
    implements,
    )

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor,
    quote,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.components.tokens import (
    create_token,
    create_unique_token_for_table,
    )
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from canonical.launchpad.interfaces.lpstorm import (
    ISlaveStore,
    IStore,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.launchpad.webapp.url import urlappend
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.validators.name import valid_name
from lp.archivepublisher.debversion import Version
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archiveuploader.utils import (
    re_isadeb,
    re_issource,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.packagebuild import IPackageBuildSet
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.errors import NoSuchDistroSeries
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.person import (
    IPersonSet,
    OPEN_TEAM_POLICY,
    PersonVisibility,
    validate_person,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.bulk import load_related
from lp.services.features import getFeatureFlag
from lp.services.job.interfaces.job import JobStatus
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.soyuz.adapters.archivedependencies import expand_dependencies
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.enums import (
    archive_suffixes,
    ArchivePermissionType,
    ArchivePurpose,
    ArchiveStatus,
    ArchiveSubscriberStatus,
    PackageCopyPolicy,
    PackagePublishingStatus,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import (
    AlreadySubscribed,
    ArchiveDependencyError,
    ArchiveDisabled,
    ArchiveNotPrivate,
    CannotCopy,
    CannotRestrictArchitectures,
    CannotSwitchPrivacy,
    CannotUploadToPocket,
    CannotUploadToPPA,
    ComponentNotFound,
    default_name_by_purpose,
    ForbiddenByFeatureFlag,
    FULL_COMPONENT_SUPPORT,
    IArchive,
    IArchiveSet,
    IDistributionArchive,
    InsufficientUploadRights,
    InvalidComponent,
    InvalidExternalDependencies,
    InvalidPocketForPartnerArchive,
    InvalidPocketForPPA,
    IPPA,
    MAIN_ARCHIVE_PURPOSES,
    NoRightsForArchive,
    NoRightsForComponent,
    NoSuchPPA,
    NoTokensForTeams,
    PocketNotFound,
    validate_external_dependencies,
    VersionRequiresName,
    )
from lp.soyuz.interfaces.archivearch import IArchiveArchSet
from lp.soyuz.interfaces.archiveauthtoken import IArchiveAuthTokenSet
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.archivesubscriber import (
    ArchiveSubscriptionError,
    IArchiveSubscriberSet,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.buildrecords import (
    IHasBuildRecords,
    IncompatibleArguments,
    )
from lp.soyuz.interfaces.component import (
    IComponent,
    IComponentSet,
    )
from lp.soyuz.interfaces.packagecopyjob import IPlainPackageCopyJobSource
from lp.soyuz.interfaces.packagecopyrequest import IPackageCopyRequestSet
from lp.soyuz.interfaces.processor import IProcessorFamilySet
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    IPublishingSet,
    )
from lp.soyuz.model.archiveauthtoken import ArchiveAuthToken
from lp.soyuz.model.archivedependency import ArchiveDependency
from lp.soyuz.model.archivesubscriber import ArchiveSubscriber
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageRelease,
    BinaryPackageReleaseDownloadCount,
    )
from lp.soyuz.model.component import Component
from lp.soyuz.model.distributionsourcepackagecache import (
    DistributionSourcePackageCache,
    )
from lp.soyuz.model.distroseriespackagecache import DistroSeriesPackageCache
from lp.soyuz.model.files import (
    BinaryPackageFile,
    SourcePackageReleaseFile,
    )
from lp.soyuz.model.packagediff import PackageDiff
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.soyuz.model.queue import (
    PackageUpload,
    PackageUploadSource,
    )
from lp.soyuz.model.section import Section
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.soyuz.scripts.packagecopier import check_copy_permissions


def storm_validate_external_dependencies(archive, attr, value):
    assert attr == 'external_dependencies'
    errors = validate_external_dependencies(value)
    if len(errors) > 0:
        raise InvalidExternalDependencies(errors)
    return value


class Archive(SQLBase):
    implements(IArchive, IHasOwner, IHasBuildRecords)
    _table = 'Archive'
    _defaultOrder = 'id'

    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_person, notNull=True)

    def _validate_archive_name(self, attr, value):
        """Only allow renaming of COPY archives.

        Also assert the name is valid when set via an unproxied object.
        """
        if not self._SO_creating:
            assert self.is_copy, "Only COPY archives can be renamed."
        assert valid_name(value), "Invalid name given to unproxied object."
        return value

    def _validate_archive_privacy(self, attr, value):
        """Require private team owners to have private archives.

        If the owner of the archive is private, then the archive cannot be
        made public.
        """
        if value is False:
            # The archive is transitioning from private to public.
            assert self.owner.visibility != PersonVisibility.PRIVATE, (
                "Private teams may not have public PPAs.")

        # If the privacy is being changed ensure there are no sources
        # published.
        sources_count = self.getPublishedSources().count()
        if sources_count > 0:
            raise CannotSwitchPrivacy(
                "This archive has had %d sources published and therefore "
                "cannot have its privacy switched." % sources_count)

        return value

    name = StringCol(
        dbName='name', notNull=True, storm_validator=_validate_archive_name)

    displayname = StringCol(dbName='displayname', notNull=True)

    description = StringCol(dbName='description', notNull=False, default=None)

    distribution = ForeignKey(
        foreignKey='Distribution', dbName='distribution', notNull=False)

    purpose = EnumCol(
        dbName='purpose', unique=False, notNull=True, schema=ArchivePurpose)

    status = EnumCol(
        dbName="status", unique=False, notNull=True, schema=ArchiveStatus,
        default=ArchiveStatus.ACTIVE)

    _enabled = BoolCol(dbName='enabled', notNull=True, default=True)
    enabled = property(lambda x: x._enabled)

    publish = BoolCol(dbName='publish', notNull=True, default=True)

    _private = BoolCol(dbName='private', notNull=True, default=False,
                      storm_validator=_validate_archive_privacy)

    require_virtualized = BoolCol(
        dbName='require_virtualized', notNull=True, default=True)

    build_debug_symbols = BoolCol(
        dbName='build_debug_symbols', notNull=True, default=False)

    authorized_size = IntCol(
        dbName='authorized_size', notNull=False, default=2048)

    sources_cached = IntCol(
        dbName='sources_cached', notNull=False, default=0)

    binaries_cached = IntCol(
        dbName='binaries_cached', notNull=False, default=0)

    package_description_cache = StringCol(
        dbName='package_description_cache', notNull=False, default=None)

    buildd_secret = StringCol(dbName='buildd_secret', default=None)

    total_count = IntCol(dbName='total_count', notNull=True, default=0)

    pending_count = IntCol(dbName='pending_count', notNull=True, default=0)

    succeeded_count = IntCol(
        dbName='succeeded_count', notNull=True, default=0)

    building_count = IntCol(
        dbName='building_count', notNull=True, default=0)

    failed_count = IntCol(dbName='failed_count', notNull=True, default=0)

    date_created = UtcDateTimeCol(dbName='date_created')

    signing_key = ForeignKey(
        foreignKey='GPGKey', dbName='signing_key', notNull=False)

    relative_build_score = IntCol(
        dbName='relative_build_score', notNull=True, default=0)

    # This field is specifically and only intended for OEM migration to
    # Launchpad and should be re-examined in October 2010 to see if it
    # is still relevant.
    external_dependencies = StringCol(
        dbName='external_dependencies', notNull=False, default=None,
        storm_validator=storm_validate_external_dependencies)

    commercial = BoolCol(
        dbName='commercial', notNull=True, default=False)

    def _init(self, *args, **kw):
        """Provide the right interface for URL traversal."""
        SQLBase._init(self, *args, **kw)

        # Provide the additional marker interface depending on what type
        # of archive this is.  See also the browser:url declarations in
        # zcml/archive.zcml.
        if self.is_ppa:
            alsoProvides(self, IPPA)
        else:
            alsoProvides(self, IDistributionArchive)

    # Note: You may safely ignore lint when it complains about this
    # declaration.  As of Python 2.6, this is a perfectly valid way
    # of adding a setter
    @property
    def private(self):
        return self._private

    @private.setter
    def private(self, private):
        self._private = private
        if private:
            if not self.buildd_secret:
                self.buildd_secret = create_token(20)
        else:
            self.buildd_secret = None

    @property
    def title(self):
        """See `IArchive`."""
        return self.displayname

    @property
    def is_ppa(self):
        """See `IArchive`."""
        return self.purpose == ArchivePurpose.PPA

    @property
    def is_partner(self):
        """See `IArchive`."""
        return self.purpose == ArchivePurpose.PARTNER

    @property
    def is_copy(self):
        """See `IArchive`."""
        return self.purpose == ArchivePurpose.COPY

    @property
    def is_main(self):
        """See `IArchive`."""
        return self.purpose in MAIN_ARCHIVE_PURPOSES

    @property
    def is_active(self):
        """See `IArchive`."""
        return self.status == ArchiveStatus.ACTIVE

    @property
    def series_with_sources(self):
        """See `IArchive`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # Import DistroSeries here to avoid circular imports.
        from lp.registry.model.distroseries import DistroSeries

        distro_series = store.find(
            DistroSeries,
            DistroSeries.distribution == self.distribution,
            SourcePackagePublishingHistory.distroseries == DistroSeries.id,
            SourcePackagePublishingHistory.archive == self,
            SourcePackagePublishingHistory.status.is_in(
                active_publishing_status))

        distro_series.config(distinct=True)

        # Ensure the ordering is the same as presented by
        # Distribution.series
        return sorted(
            distro_series, key=lambda a: Version(a.version), reverse=True)

    @property
    def dependencies(self):
        query = """
            ArchiveDependency.dependency = Archive.id AND
            Archive.owner = Person.id AND
            ArchiveDependency.archive = %s
        """ % sqlvalues(self)
        clauseTables = ["Archive", "Person"]
        orderBy = ['Person.displayname']
        dependencies = ArchiveDependency.select(
            query, clauseTables=clauseTables, orderBy=orderBy)
        return dependencies

    @cachedproperty
    def debug_archive(self):
        """See `IArchive`."""
        if self.purpose == ArchivePurpose.PRIMARY:
            return getUtility(IArchiveSet).getByDistroPurpose(
                self.distribution, ArchivePurpose.DEBUG)
        else:
            return self

    @cachedproperty
    def default_component(self):
        """See `IArchive`."""
        if self.is_partner:
            return getUtility(IComponentSet)['partner']
        elif self.is_ppa:
            return getUtility(IComponentSet)['main']
        else:
            return None

    @property
    def archive_url(self):
        """See `IArchive`."""
        if self.is_ppa:
            if self.private:
                url = config.personalpackagearchive.private_base_url
            else:
                url = config.personalpackagearchive.base_url
            return urlappend(
                url, "/".join(
                    (self.owner.name, self.name, self.distribution.name)))

        db_pubconf = getUtility(
            IPublisherConfigSet).getByDistribution(self.distribution)
        if self.is_copy:
            url = urlappend(
                db_pubconf.copy_base_url,
                self.distribution.name + '-' + self.name)
            return urlappend(url, self.distribution.name)

        try:
            postfix = archive_suffixes[self.purpose]
        except KeyError:
            raise AssertionError(
                "archive_url unknown for purpose: %s" % self.purpose)
        return urlappend(
            db_pubconf.base_url, self.distribution.name + postfix)

    @property
    def signing_key_fingerprint(self):
        if self.signing_key is not None:
            return self.signing_key.fingerprint

        return None

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        arch_tag=None, user=None, binary_only=True):
        """See IHasBuildRecords"""
        # Ignore "user", since anyone already accessing this archive
        # will implicitly have permission to see it.

        if binary_only:
            return getUtility(IBinaryPackageBuildSet).getBuildsForArchive(
                self, build_state, name, pocket, arch_tag)
        else:
            if arch_tag is not None or name is not None:
                raise IncompatibleArguments(
                    "The 'arch_tag' and 'name' parameters can be used only "
                    "with binary_only=True.")
            return getUtility(IPackageBuildSet).getBuildsForArchive(
                self, status=build_state, pocket=pocket)

    def getPublishedSources(self, name=None, version=None, status=None,
                            distroseries=None, pocket=None,
                            exact_match=False, created_since_date=None,
                            eager_load=False):
        """See `IArchive`."""
        # clauses contains literal sql expressions for things that don't work
        # easily in storm : this method was migrated from sqlobject but some
        # callers are problematic. (Migrate them and test to see).
        clauses = []
        storm_clauses = [
            SourcePackagePublishingHistory.archiveID == self.id,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                SourcePackageRelease.id,
            SourcePackageRelease.sourcepackagenameID ==
                SourcePackageName.id,
            ]
        orderBy = [
            SourcePackageName.name,
            Desc(SourcePackagePublishingHistory.id),
            ]

        if name is not None:
            if type(name) in (str, unicode):
                if exact_match:
                    storm_clauses.append(SourcePackageName.name == name)
                else:
                    clauses.append(
                        "SourcePackageName.name LIKE '%%%%' || %s || '%%%%'"
                        % quote_like(name))
            elif len(name) != 0:
                clauses.append(
                    "SourcePackageName.name IN %s"
                    % sqlvalues(name))

        if version is not None:
            if name is None:
                raise VersionRequiresName(
                    "The 'version' parameter can be used only together with"
                    " the 'name' parameter.")
            storm_clauses.append(SourcePackageRelease.version == version)
        else:
            orderBy.insert(1, Desc(SourcePackageRelease.version))

        if status is not None:
            try:
                status = tuple(status)
            except TypeError:
                status = (status, )
            clauses.append(
                "SourcePackagePublishingHistory.status IN %s "
                % sqlvalues(status))

        if distroseries is not None:
            storm_clauses.append(
                SourcePackagePublishingHistory.distroseriesID ==
                    distroseries.id)

        if pocket is not None:
            try:
                pockets = tuple(pocket)
            except TypeError:
                pockets = (pocket,)
            storm_clauses.append(
                "SourcePackagePublishingHistory.pocket IN %s " %
                   sqlvalues(pockets))

        if created_since_date is not None:
            clauses.append(
                "SourcePackagePublishingHistory.datecreated >= %s"
                % sqlvalues(created_since_date))

        store = Store.of(self)
        if clauses:
            storm_clauses.append(SQL(' AND '.join(clauses)))
        resultset = store.find(SourcePackagePublishingHistory,
            *storm_clauses).order_by(
            *orderBy)
        if not eager_load:
            return resultset

        # Its not clear that this eager load is necessary or sufficient, it
        # replaces a prejoin that had pathological query plans.
        def eager_load(rows):
            # \o/ circular imports.
            from lp.registry.model.distroseries import DistroSeries
            from lp.registry.model.gpgkey import GPGKey
            ids = set(map(attrgetter('distroseriesID'), rows))
            ids.discard(None)
            if ids:
                list(store.find(DistroSeries, DistroSeries.id.is_in(ids)))
            ids = set(map(attrgetter('sectionID'), rows))
            ids.discard(None)
            if ids:
                list(store.find(Section, Section.id.is_in(ids)))
            ids = set(map(attrgetter('sourcepackagereleaseID'), rows))
            ids.discard(None)
            if not ids:
                return
            releases = list(store.find(
                SourcePackageRelease, SourcePackageRelease.id.is_in(ids)))
            ids = set(map(attrgetter('creatorID'), releases))
            ids.discard(None)
            if ids:
                list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(ids))
            ids = set(map(attrgetter('dscsigningkeyID'), releases))
            ids.discard(None)
            if ids:
                list(store.find(GPGKey, GPGKey.id.is_in(ids)))
        return DecoratedResultSet(resultset, pre_iter_hook=eager_load)

    def getSourcesForDeletion(self, name=None, status=None,
            distroseries=None):
        """See `IArchive`."""
        clauses = ["""
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
        """ % sqlvalues(self)]

        has_published_binaries_clause = """
            EXISTS (SELECT TRUE FROM
                BinaryPackagePublishingHistory bpph,
                BinaryPackageRelease bpr, BinaryPackageBuild
            WHERE
                bpph.archive = %s AND
                bpph.status = %s AND
                bpph.binarypackagerelease = bpr.id AND
                bpr.build = BinaryPackageBuild.id AND
                BinaryPackageBuild.source_package_release =
                    SourcePackageRelease.id)
        """ % sqlvalues(self, PackagePublishingStatus.PUBLISHED)

        source_deletable_states = (
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            )
        clauses.append("""
           (%s OR SourcePackagePublishingHistory.status IN %s)
        """ % (has_published_binaries_clause,
               quote(source_deletable_states)))

        if status is not None:
            try:
                status = tuple(status)
            except TypeError:
                status = (status, )
            clauses.append("""
                SourcePackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroseries is not None:
            clauses.append("""
                SourcePackagePublishingHistory.distroseries = %s
            """ % sqlvalues(distroseries))

        clauseTables = ['SourcePackageRelease', 'SourcePackageName']

        order_const = "SourcePackageRelease.version"
        desc_version_order = SQLConstant(order_const + " DESC")
        orderBy = ['SourcePackageName.name', desc_version_order,
                   '-SourcePackagePublishingHistory.id']

        if name is not None:
            clauses.append("""
                    SourcePackageName.name LIKE '%%' || %s || '%%'
                """ % quote_like(name))

        preJoins = ['sourcepackagerelease']
        sources = SourcePackagePublishingHistory.select(
            ' AND '.join(clauses), clauseTables=clauseTables, orderBy=orderBy,
            prejoins=preJoins)

        return sources

    @property
    def number_of_sources(self):
        """See `IArchive`."""
        return self.getPublishedSources(
            status=PackagePublishingStatus.PUBLISHED).count()

    @property
    def sources_size(self):
        """See `IArchive`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result = store.find((
            LibraryFileAlias.filename,
            LibraryFileContent.sha1,
            LibraryFileContent.filesize),
            SourcePackagePublishingHistory.archive == self.id,
            SourcePackagePublishingHistory.dateremoved == None,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                SourcePackageReleaseFile.sourcepackagereleaseID,
            SourcePackageReleaseFile.libraryfileID == LibraryFileAlias.id,
            LibraryFileAlias.contentID == LibraryFileContent.id)

        # Note: we can't use the LFC.sha1 instead of LFA.filename above
        # because some archives publish the same file content with different
        # names in the archive, so although the duplication will be removed
        # in the librarian by the librarian-gc, we do not (yet) remove
        # this duplication in the pool when the filenames are different.

        # We need to select distinct on the (filename, filesize) result
        # so that we only count duplicate files (with the same filename)
        # once (ie. the same tarball used for different distroseries) as
        # we do avoid this duplication in the pool when the names are
        # the same.
        result = result.config(distinct=True)

        # Using result.sum(LibraryFileContent.filesize) throws errors when
        # the result is empty, so instead:
        return sum(result.values(LibraryFileContent.filesize))

    def _getBinaryPublishingBaseClauses(
        self, name=None, version=None, status=None, distroarchseries=None,
        pocket=None, exact_match=False):
        """Base clauses and clauseTables for binary publishing queries.

        Returns a list of 'clauses' (to be joined in the callsite) and
        a list of clauseTables required according the given arguments.
        """
        clauses = ["""
            BinaryPackagePublishingHistory.archive = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id
        """ % sqlvalues(self)]
        clauseTables = ['BinaryPackageRelease', 'BinaryPackageName']
        orderBy = ['BinaryPackageName.name',
                   '-BinaryPackagePublishingHistory.id']

        if name is not None:
            if exact_match:
                clauses.append("""
                    BinaryPackageName.name=%s
                """ % sqlvalues(name))
            else:
                clauses.append("""
                    BinaryPackageName.name LIKE '%%' || %s || '%%'
                """ % quote_like(name))

        if version is not None:
            if name is None:
                raise VersionRequiresName(
                    "The 'version' parameter can be used only together with"
                    " the 'name' parameter.")

            clauses.append("""
                BinaryPackageRelease.version = %s
            """ % sqlvalues(version))
        else:
            order_const = "BinaryPackageRelease.version"
            desc_version_order = SQLConstant(order_const + " DESC")
            orderBy.insert(1, desc_version_order)

        if status is not None:
            try:
                status = tuple(status)
            except TypeError:
                status = (status, )
            clauses.append("""
                BinaryPackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroarchseries is not None:
            try:
                distroarchseries = tuple(distroarchseries)
            except TypeError:
                distroarchseries = (distroarchseries, )
            # XXX cprov 20071016: there is no sqlrepr for DistroArchSeries
            # uhmm, how so ?
            das_ids = "(%s)" % ", ".join(str(d.id) for d in distroarchseries)
            clauses.append("""
                BinaryPackagePublishingHistory.distroarchseries IN %s
            """ % das_ids)

        if pocket is not None:
            clauses.append("""
                BinaryPackagePublishingHistory.pocket = %s
            """ % sqlvalues(pocket))

        return clauses, clauseTables, orderBy

    def getAllPublishedBinaries(self, name=None, version=None, status=None,
                                distroarchseries=None, pocket=None,
                                exact_match=False):
        """See `IArchive`."""
        clauses, clauseTables, orderBy = self._getBinaryPublishingBaseClauses(
            name=name, version=version, status=status, pocket=pocket,
            distroarchseries=distroarchseries, exact_match=exact_match)

        all_binaries = BinaryPackagePublishingHistory.select(
            ' AND '.join(clauses), clauseTables=clauseTables,
            orderBy=orderBy)

        return all_binaries

    def getPublishedOnDiskBinaries(self, name=None, version=None, status=None,
                                   distroarchseries=None, pocket=None,
                                   exact_match=False):
        """See `IArchive`."""
        clauses, clauseTables, orderBy = self._getBinaryPublishingBaseClauses(
            name=name, version=version, status=status, pocket=pocket,
            distroarchseries=distroarchseries, exact_match=exact_match)

        clauses.append("""
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = DistroSeries.id
        """)
        clauseTables.extend(['DistroSeries', 'DistroArchSeries'])

        # Retrieve only the binaries published for the 'nominated architecture
        # independent' (usually i386) in the distroseries in question.
        # It includes all architecture-independent binaries only once and the
        # architecture-specific built for 'nominatedarchindep'.
        nominated_arch_independent_clause = ["""
            DistroSeries.nominatedarchindep =
                BinaryPackagePublishingHistory.distroarchseries
        """]
        nominated_arch_independent_query = ' AND '.join(
            clauses + nominated_arch_independent_clause)
        nominated_arch_independents = BinaryPackagePublishingHistory.select(
            nominated_arch_independent_query, clauseTables=clauseTables)

        # Retrieve all architecture-specific binary publications except
        # 'nominatedarchindep' (already included in the previous query).
        no_nominated_arch_independent_clause = ["""
            DistroSeries.nominatedarchindep !=
                BinaryPackagePublishingHistory.distroarchseries AND
            BinaryPackageRelease.architecturespecific = true
        """]
        no_nominated_arch_independent_query = ' AND '.join(
            clauses + no_nominated_arch_independent_clause)
        no_nominated_arch_independents = (
            BinaryPackagePublishingHistory.select(
            no_nominated_arch_independent_query, clauseTables=clauseTables))

        # XXX cprov 20071016: It's not possible to use the same ordering
        # schema returned by self._getBinaryPublishingBaseClauses.
        # It results in:
        # ERROR:  missing FROM-clause entry for table "binarypackagename"
        unique_binary_publications = nominated_arch_independents.union(
            no_nominated_arch_independents).orderBy("id")

        return unique_binary_publications

    @property
    def number_of_binaries(self):
        """See `IArchive`."""
        return self.getPublishedOnDiskBinaries(
            status=PackagePublishingStatus.PUBLISHED).count()

    @property
    def binaries_size(self):
        """See `IArchive`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        clauses = [
            BinaryPackagePublishingHistory.archive == self.id,
            BinaryPackagePublishingHistory.dateremoved == None,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageFile.binarypackagereleaseID,
            BinaryPackageFile.libraryfileID == LibraryFileAlias.id,
            LibraryFileAlias.contentID == LibraryFileContent.id,
            ]
        result = store.find(LibraryFileContent, *clauses)

        # See `IArchive.sources_size`.
        result = result.config(distinct=True)
        size = sum([lfc.filesize for lfc in result])
        return size

    @property
    def estimated_size(self):
        """See `IArchive`."""
        size = self.sources_size + self.binaries_size
        # 'cruft' represents the increase in the size of the archive
        # indexes related to each publication. We assume it is around 1K
        # but that's over-estimated.
        cruft = (
            self.number_of_sources + self.number_of_binaries) * 1024
        return size + cruft

    def allowUpdatesToReleasePocket(self):
        """See `IArchive`."""
        purposeToPermissionMap = {
            ArchivePurpose.COPY: True,
            ArchivePurpose.PARTNER: True,
            ArchivePurpose.PPA: True,
            ArchivePurpose.PRIMARY: False,
        }

        try:
            permission = purposeToPermissionMap[self.purpose]
        except KeyError:
            # Future proofing for when new archive types are added.
            permission = False

        return permission

    def getComponentsForSeries(self, distroseries):
        """See `IArchive`."""
        # DistroSeries.components and Archive.default_component are
        # cachedproperties, so this is fairly cheap.
        if self.purpose in FULL_COMPONENT_SUPPORT:
            return distroseries.components
        else:
            return [self.default_component]

    def updateArchiveCache(self):
        """See `IArchive`."""
        # Compiled regexp to remove puntication.
        clean_text = re.compile('(,|;|:|\.|\?|!)')

        # XXX cprov 20080402 bug=207969: The set() is only used because we
        # have a limitation in our FTI setup, it only indexes the first 2500
        # chars of the target columns. When such limitation
        # gets fixed we should probably change it to a normal list and
        # benefit of the FTI rank for ordering.
        cache_contents = set()

        def add_cache_content(content):
            """Sanitise and add contents to the cache."""
            content = clean_text.sub(' ', content)
            terms = [term.lower() for term in content.strip().split()]
            for term in terms:
                cache_contents.add(term)

        # Cache owner name and displayname.
        add_cache_content(self.owner.name)
        add_cache_content(self.owner.displayname)

        # Cache source package name and its binaries information, binary
        # names and summaries.
        sources_cached = DistributionSourcePackageCache.select(
            "archive = %s" % sqlvalues(self), prejoins=["distribution"])
        for cache in sources_cached:
            add_cache_content(cache.distribution.name)
            add_cache_content(cache.name)
            add_cache_content(cache.binpkgnames)
            add_cache_content(cache.binpkgsummaries)

        # Cache distroseries names with binaries.
        binaries_cached = DistroSeriesPackageCache.select(
            "archive = %s" % sqlvalues(self), prejoins=["distroseries"])
        for cache in binaries_cached:
            add_cache_content(cache.distroseries.name)

        # Collapse all relevant terms in 'package_description_cache' and
        # update the package counters.
        self.package_description_cache = " ".join(cache_contents)
        self.sources_cached = sources_cached.count()
        self.binaries_cached = binaries_cached.count()

    def findDepCandidates(self, distro_arch_series, pocket, component,
                          source_package_name, dep_name):
        """See `IArchive`."""
        deps = expand_dependencies(
            self, distro_arch_series, pocket, component, source_package_name)
        archive_clause = Or([And(
            BinaryPackagePublishingHistory.archiveID == archive.id,
            BinaryPackagePublishingHistory.pocket == pocket,
            Component.name.is_in(components))
            for (archive, not_used, pocket, components) in deps])

        store = ISlaveStore(BinaryPackagePublishingHistory)
        return store.find(
            BinaryPackagePublishingHistory,
            BinaryPackageName.name == dep_name,
            BinaryPackageRelease.binarypackagename == BinaryPackageName.id,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.distroarchseries ==
                distro_arch_series,
            BinaryPackagePublishingHistory.status ==
                PackagePublishingStatus.PUBLISHED,
            BinaryPackagePublishingHistory.componentID == Component.id,
            archive_clause).order_by(
                Desc(BinaryPackagePublishingHistory.id))

    def getArchiveDependency(self, dependency):
        """See `IArchive`."""
        return ArchiveDependency.selectOneBy(
            archive=self, dependency=dependency)

    def removeArchiveDependency(self, dependency):
        """See `IArchive`."""
        dependency = self.getArchiveDependency(dependency)
        if dependency is None:
            raise AssertionError("This dependency does not exist.")
        dependency.destroySelf()

    def addArchiveDependency(self, dependency, pocket, component=None):
        """See `IArchive`."""
        if dependency == self:
            raise ArchiveDependencyError(
                "An archive should not depend on itself.")

        a_dependency = self.getArchiveDependency(dependency)
        if a_dependency is not None:
            raise ArchiveDependencyError(
                "This dependency is already registered.")
        if not check_permission('launchpad.View', dependency):
            raise ArchiveDependencyError(
                "You don't have permission to use this dependency.")
            return
        if dependency.private and not self.private:
            raise ArchiveDependencyError(
                "Public PPAs cannot depend on private ones.")

        if dependency.is_ppa:
            if pocket is not PackagePublishingPocket.RELEASE:
                raise ArchiveDependencyError(
                    "Non-primary archives only support the RELEASE pocket.")
            if (component is not None and
                component != dependency.default_component):
                raise ArchiveDependencyError(
                    "Non-primary archives only support the '%s' component." %
                    dependency.default_component.name)

        return ArchiveDependency(
            archive=self, dependency=dependency, pocket=pocket,
            component=component)

    def _addArchiveDependency(self, dependency, pocket, component=None):
        """See `IArchive`."""
        if isinstance(component, basestring):
            try:
                component = getUtility(IComponentSet)[component]
            except NotFoundError as e:
                raise ComponentNotFound(e)
        return self.addArchiveDependency(dependency, pocket, component)

    def getPermissions(self, user, item, perm_type):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.checkAuthenticated(user, self, perm_type, item)

    def getPermissionsForPerson(self, person):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.permissionsForPerson(self, person)

    def getUploadersForPackage(self, source_package_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.uploadersForPackage(self, source_package_name)

    def getUploadersForComponent(self, component_name=None):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.uploadersForComponent(self, component_name)

    def getQueueAdminsForComponent(self, component_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.queueAdminsForComponent(self, component_name)

    def getComponentsForQueueAdmin(self, person):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.componentsForQueueAdmin(self, person)

    def hasAnyPermission(self, person):
        """See `IArchive`."""
        # Avoiding circular imports.
        from lp.soyuz.model.archivepermission import ArchivePermission

        any_perm_on_archive = Store.of(self).find(
            TeamParticipation,
            ArchivePermission.archive == self.id,
            TeamParticipation.person == person.id,
            TeamParticipation.teamID == ArchivePermission.personID,
            )
        return not any_perm_on_archive.is_empty()

    def getBuildCounters(self, include_needsbuild=True):
        """See `IArchiveSet`."""

        # First grab a count of each build state for all the builds in
        # this archive:
        store = Store.of(self)
        extra_exprs = []
        if not include_needsbuild:
            extra_exprs.append(
                BuildFarmJob.status != BuildStatus.NEEDSBUILD)

        find_spec = (
            BuildFarmJob.status,
            Count(BinaryPackageBuild.id),
            )
        result = store.using(
            BinaryPackageBuild, PackageBuild, BuildFarmJob).find(
            find_spec,
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.archive == self,
            PackageBuild.build_farm_job == BuildFarmJob.id,
            *extra_exprs).group_by(BuildFarmJob.status).order_by(
                BuildFarmJob.status)

        # Create a map for each count summary to a number of buildstates:
        count_map = {
            'failed': (
                BuildStatus.CHROOTWAIT,
                BuildStatus.FAILEDTOBUILD,
                BuildStatus.FAILEDTOUPLOAD,
                BuildStatus.MANUALDEPWAIT,
                ),
            'pending': [
                BuildStatus.BUILDING,
                BuildStatus.UPLOADING,
                ],
            'succeeded': (
                BuildStatus.FULLYBUILT,
                ),
            'superseded': (
                BuildStatus.SUPERSEDED,
                ),
             # The 'total' count is a list because we may append to it
             # later.
            'total': [
                BuildStatus.CHROOTWAIT,
                BuildStatus.FAILEDTOBUILD,
                BuildStatus.FAILEDTOUPLOAD,
                BuildStatus.MANUALDEPWAIT,
                BuildStatus.BUILDING,
                BuildStatus.UPLOADING,
                BuildStatus.FULLYBUILT,
                BuildStatus.SUPERSEDED,
                ],
            }

        # If we were asked to include builds with the state NEEDSBUILD,
        # then include those builds in the 'pending' and total counts.
        if include_needsbuild:
            count_map['pending'].append(BuildStatus.NEEDSBUILD)
            count_map['total'].append(BuildStatus.NEEDSBUILD)

        # Initialize all the counts in the map to zero:
        build_counts = dict((count_type, 0) for count_type in count_map)

        # For each count type that we want to return ('failed', 'total'),
        # there may be a number of corresponding buildstate counts.
        # So for each buildstate count in the result set...
        for buildstate, count in result:
            # ...go through the count map checking which counts this
            # buildstate belongs to and add it to the aggregated
            # count.
            for count_type, build_states in count_map.items():
                if buildstate in build_states:
                    build_counts[count_type] += count

        return build_counts

    def getBuildSummariesForSourceIds(self, source_ids):
        """See `IArchive`."""
        publishing_set = getUtility(IPublishingSet)
        return publishing_set.getBuildStatusSummariesForSourceIdsAndArchive(
            source_ids,
            archive=self)

    def checkArchivePermission(self, user, component_or_package=None):
        """See `IArchive`."""
        # PPA access is immediately granted if the user is in the PPA
        # team.
        if self.is_ppa:
            if user.inTeam(self.owner):
                return True
            else:
                # If the user is not in the PPA team, default to using
                # the main component for further ACL checks.  This is
                # not ideal since PPAs don't use components, but when
                # packagesets replace them for main archive uploads this
                # interface will no longer require them because we can
                # then relax the database constraint on
                # ArchivePermission.
                component_or_package = self.default_component

        # Flatly refuse uploads to copy archives, at least for now.
        if self.is_copy:
            return False

        # Otherwise any archive, including PPAs, uses the standard
        # ArchivePermission entries.
        return self._authenticate(
            user, component_or_package, ArchivePermissionType.UPLOAD)

    def canUploadSuiteSourcePackage(self, person, suitesourcepackage):
        """See `IArchive`."""
        sourcepackage = suitesourcepackage.sourcepackage
        pocket = suitesourcepackage.pocket
        distroseries = sourcepackage.distroseries
        sourcepackagename = sourcepackage.sourcepackagename
        component = sourcepackage.latest_published_component
        # strict_component is True because the source package already
        # exists (otherwise we couldn't have a suitesourcepackage
        # object) and nascentupload passes True as a matter of policy
        # when the package exists.
        reason = self.checkUpload(
            person, distroseries, sourcepackagename, component, pocket,
            strict_component=True)
        return reason is None

    def checkUploadToPocket(self, distroseries, pocket):
        """See `IArchive`."""
        if self.is_partner:
            if pocket not in (
                PackagePublishingPocket.RELEASE,
                PackagePublishingPocket.PROPOSED):
                return InvalidPocketForPartnerArchive()
        elif self.is_ppa:
            if pocket != PackagePublishingPocket.RELEASE:
                return InvalidPocketForPPA()
        elif self.is_copy:
            # Any pocket is allowed for COPY archives, otherwise it can
            # make the buildd-manager throw exceptions when dispatching
            # existing builds after a series is released.
            return
        else:
            # Uploads to the partner archive are allowed in any distroseries
            # state.
            # XXX julian 2005-05-29 bug=117557:
            # This is a greasy hack until bug #117557 is fixed.
            if not distroseries.canUploadToPocket(pocket):
                return CannotUploadToPocket(distroseries, pocket)

    def _checkUpload(self, person, distroseries, sourcepackagename, component,
                    pocket, strict_component=True):
        """See `IArchive`."""
        if isinstance(component, basestring):
            component = getUtility(IComponentSet)[component]
        if isinstance(sourcepackagename, basestring):
            sourcepackagename = getUtility(
                ISourcePackageNameSet)[sourcepackagename]
        reason = self.checkUpload(person, distroseries, sourcepackagename,
            component, pocket, strict_component)
        if reason is not None:
            raise reason
        return True

    def checkUpload(self, person, distroseries, sourcepackagename, component,
                    pocket, strict_component=True):
        """See `IArchive`."""
        reason = self.checkUploadToPocket(distroseries, pocket)
        if reason is not None:
            return reason
        return self.verifyUpload(
            person, sourcepackagename, component, distroseries,
            strict_component)

    def verifyUpload(self, person, sourcepackagename, component,
                     distroseries, strict_component=True):
        """See `IArchive`."""
        if not self.enabled:
            return ArchiveDisabled(self.displayname)

        # For PPAs...
        if self.is_ppa:
            if not self.checkArchivePermission(person):
                return CannotUploadToPPA()
            else:
                return None

        if sourcepackagename is not None:
            # Check whether user may upload because they hold a permission for
            #   - the given source package directly
            #   - a package set in the correct distro series that includes the
            #     given source package
            source_allowed = self.checkArchivePermission(person,
                                                         sourcepackagename)
            set_allowed = self.isSourceUploadAllowed(
                sourcepackagename, person, distroseries)
            if source_allowed or set_allowed:
                return None

        if not self.getComponentsForUploader(person):
            # XXX: JamesWestby 2010-08-01 bug=612351: We have to use
            # is_empty() as we don't get an SQLObjectResultSet back, and
            # so __nonzero__ isn't defined on it, and a straight bool
            # check wouldn't do the right thing.
            if self.getPackagesetsForUploader(person).is_empty():
                return NoRightsForArchive()
            else:
                return InsufficientUploadRights()

        if (component is not None
            and strict_component
            and not self.checkArchivePermission(person, component)):
            return NoRightsForComponent(component)

        return None

    def canAdministerQueue(self, user, component):
        """See `IArchive`."""
        return self._authenticate(
            user, component, ArchivePermissionType.QUEUE_ADMIN)

    def _authenticate(self, user, component, permission):
        """Private helper method to check permissions."""
        permissions = self.getPermissions(user, component, permission)
        return bool(permissions)

    def newPackageUploader(self, person, source_package_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.newPackageUploader(
            self, person, source_package_name)

    def newPackagesetUploader(self, person, packageset, explicit=False):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.newPackagesetUploader(
            self, person, packageset, explicit)

    def newComponentUploader(self, person, component_name):
        """See `IArchive`."""
        if self.is_ppa:
            if IComponent.providedBy(component_name):
                name = component_name.name
            elif isinstance(component_name, basestring):
                name = component_name
            else:
                name = None

            if name != self.default_component.name:
                raise InvalidComponent(
                    "Component for PPAs should be '%s'" %
                    self.default_component.name)

        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.newComponentUploader(
            self, person, component_name)

    def newQueueAdmin(self, person, component_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.newQueueAdmin(self, person, component_name)

    def deletePackageUploader(self, person, source_package_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.deletePackageUploader(
            self, person, source_package_name)

    def deleteComponentUploader(self, person, component_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.deleteComponentUploader(
            self, person, component_name)

    def deleteQueueAdmin(self, person, component_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.deleteQueueAdmin(self, person, component_name)

    def getUploadersForPackageset(self, packageset, direct_permissions=True):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.uploadersForPackageset(
            self, packageset, direct_permissions)

    def deletePackagesetUploader(self, person, packageset, explicit=False):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.deletePackagesetUploader(
            self, person, packageset, explicit)

    def getComponentsForUploader(self, person):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.componentsForUploader(self, person)

    def getPackagesetsForUploader(self, person):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.packagesetsForUploader(self, person)

    def getPackagesetsForSourceUploader(self, sourcepackagename, person):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.packagesetsForSourceUploader(
            self, sourcepackagename, person)

    def getPackagesetsForSource(
        self, sourcepackagename, direct_permissions=True):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.packagesetsForSource(
            self, sourcepackagename, direct_permissions)

    def isSourceUploadAllowed(
        self, sourcepackagename, person, distroseries=None):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.isSourceUploadAllowed(
            self, sourcepackagename, person, distroseries)

    def getFileByName(self, filename):
        """See `IArchive`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        base_clauses = (
            LibraryFileAlias.filename == filename,
            LibraryFileAlias.content != None,
            )

        if re_issource.match(filename):
            clauses = (
                SourcePackagePublishingHistory.archive == self.id,
                SourcePackagePublishingHistory.sourcepackagereleaseID ==
                    SourcePackageReleaseFile.sourcepackagereleaseID,
                SourcePackageReleaseFile.libraryfileID ==
                    LibraryFileAlias.id,
                )
        elif re_isadeb.match(filename):
            clauses = (
                BinaryPackagePublishingHistory.archive == self.id,
                BinaryPackagePublishingHistory.binarypackagereleaseID ==
                    BinaryPackageFile.binarypackagereleaseID,
                BinaryPackageFile.libraryfileID == LibraryFileAlias.id,
                )
        elif filename.endswith('_source.changes'):
            clauses = (
                SourcePackagePublishingHistory.archive == self.id,
                SourcePackagePublishingHistory.sourcepackagereleaseID ==
                    PackageUploadSource.sourcepackagereleaseID,
                PackageUploadSource.packageuploadID == PackageUpload.id,
                PackageUpload.status == PackageUploadStatus.DONE,
                PackageUpload.changesfileID == LibraryFileAlias.id,
                )
        else:
            raise NotFoundError(filename)

        def do_query():
            result = store.find((LibraryFileAlias), *(base_clauses + clauses))
            result = result.config(distinct=True)
            result.order_by(LibraryFileAlias.id)
            return result.first()

        archive_file = do_query()

        if archive_file is None:
            # If a diff.gz wasn't found in the source-files domain, try in
            # the PackageDiff domain.
            if filename.endswith('.diff.gz'):
                clauses = (
                    SourcePackagePublishingHistory.archive == self.id,
                    SourcePackagePublishingHistory.sourcepackagereleaseID ==
                        PackageDiff.to_sourceID,
                    PackageDiff.diff_contentID == LibraryFileAlias.id,
                    )
                package_diff_file = do_query()
                if package_diff_file is not None:
                    return package_diff_file

            raise NotFoundError(filename)

        return archive_file

    def getBinaryPackageRelease(self, name, version, archtag):
        """See `IArchive`."""
        from lp.soyuz.model.distroarchseries import DistroArchSeries

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        results = store.find(
            BinaryPackageRelease,
            BinaryPackageRelease.binarypackagename == name,
            BinaryPackageRelease.version == version,
            BinaryPackageBuild.id == BinaryPackageRelease.buildID,
            DistroArchSeries.id == BinaryPackageBuild.distro_arch_series_id,
            DistroArchSeries.architecturetag == archtag,
            BinaryPackagePublishingHistory.archive == self,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id).config(distinct=True)
        if results.count() > 1:
            return None
        return results.one()

    def getBinaryPackageReleaseByFileName(self, filename):
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            BinaryPackageRelease,
            BinaryPackageFile.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackageFile.libraryfileID == LibraryFileAlias.id,
            LibraryFileAlias.filename == filename,
            BinaryPackagePublishingHistory.archive == self,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            ).order_by(Desc(BinaryPackagePublishingHistory.id)).first()

    def requestPackageCopy(self, target_location, requestor, suite=None,
        copy_binaries=False, reason=None):
        """See `IArchive`."""
        if suite is None:
            distroseries = self.distribution.currentseries
            pocket = PackagePublishingPocket.RELEASE
        else:
            # Note: a NotFoundError will be raised if it is not found.
            distroseries, pocket = self.distribution.getDistroSeriesAndPocket(
                suite)

        source_location = PackageLocation(self, self.distribution,
                                          distroseries, pocket)

        return getUtility(IPackageCopyRequestSet).new(
            source_location, target_location, requestor, copy_binaries,
            reason)

    def syncSources(self, source_names, from_archive, to_pocket,
                    to_series=None, include_binaries=False, person=None):
        """See `IArchive`."""
        # Find and validate the source package names in source_names.
        sources = self._collectLatestPublishedSources(
            from_archive, source_names)
        self._copySources(
            sources, to_pocket, to_series, include_binaries,
            person=person)

    def _validateAndFindSource(self, from_archive, source_name, version):
        # Check to see if the source package exists, and raise a useful error
        # if it doesn't.
        getUtility(ISourcePackageNameSet)[source_name]
        # Find and validate the source package version required.
        source = from_archive.getPublishedSources(
            name=source_name, version=version, exact_match=True).first()
        return source

    def syncSource(self, source_name, version, from_archive, to_pocket,
                   to_series=None, include_binaries=False, person=None):
        """See `IArchive`."""
        source = self._validateAndFindSource(
            from_archive, source_name, version)

        self._copySources(
            [source], to_pocket, to_series, include_binaries,
            person=person)

    def _checkCopyPackageFeatureFlags(self):
        """Prevent copyPackage(s) if these conditions are not met."""
        if not getFeatureFlag(u"soyuz.copypackage.enabled"):
            raise ForbiddenByFeatureFlag
        if (self.is_ppa and
            not getFeatureFlag(u"soyuz.copypackageppa.enabled")):
            # We have no way of giving feedback about failed jobs yet,
            # so this is disabled for now.
            raise ForbiddenByFeatureFlag(
                "Not enabled for copying to PPAs yet.")

    def copyPackage(self, source_name, version, from_archive, to_pocket,
                    person, to_series=None, include_binaries=False):
        """See `IArchive`."""
        self._checkCopyPackageFeatureFlags()

        # Asynchronously copy a package using the job system.
        pocket = self._text_to_pocket(to_pocket)
        series = self._text_to_series(to_series)
        # Upload permission checks, this will raise CannotCopy as
        # necessary.
        sourcepackagename = getUtility(ISourcePackageNameSet)[source_name]
        check_copy_permissions(
            person, self, series, pocket, [sourcepackagename])

        self._validateAndFindSource(from_archive, source_name, version)
        job_source = getUtility(IPlainPackageCopyJobSource)
        job_source.create(
            package_name=source_name, source_archive=from_archive,
            target_archive=self, target_distroseries=series,
            target_pocket=pocket,
            package_version=version, include_binaries=include_binaries,
            copy_policy=PackageCopyPolicy.INSECURE, requester=person)

    def copyPackages(self, source_names, from_archive, to_pocket,
                     person, to_series=None, include_binaries=None):
        """See `IArchive`."""
        self._checkCopyPackageFeatureFlags()

        sources = self._collectLatestPublishedSources(
            from_archive, source_names)
        if not sources:
            raise CannotCopy(
                "None of the supplied package names are published")

        # Bulk-load the sourcepackagereleases so that the list
        # comprehension doesn't generate additional queries. The
        # sourcepackagenames themselves will already have been loaded when
        # generating the list of source publications in "sources".
        load_related(
            SourcePackageRelease, sources, ["sourcepackagereleaseID"])
        sourcepackagenames = [source.sourcepackagerelease.sourcepackagename
                              for source in sources]

        # Now do a mass check of permissions.
        pocket = self._text_to_pocket(to_pocket)
        series = self._text_to_series(to_series)
        check_copy_permissions(
            person, self, series, pocket, sourcepackagenames)

        # If we get this far then we can create the PackageCopyJob.
        copy_tasks = []
        for source in sources:
            task = (
                source.sourcepackagerelease.sourcepackagename.name,
                source.sourcepackagerelease.version,
                from_archive,
                self,
                PackagePublishingPocket.RELEASE
                )
            copy_tasks.append(task)

        job_source = getUtility(IPlainPackageCopyJobSource)
        job_source.createMultiple(
            series, copy_tasks, person,
            copy_policy=PackageCopyPolicy.MASS_SYNC,
            include_binaries=include_binaries)

    def _collectLatestPublishedSources(self, from_archive, source_names):
        """Private helper to collect the latest published sources for an
        archive.

        :raises NoSuchSourcePackageName: If any of the source_names do not
            exist.
        """
        # XXX bigjools bug=810421
        # This code is inefficient.  It should try to bulk load all the
        # sourcepackagenames and publications instead of iterating.
        sources = []
        for name in source_names:
            # Check to see if the source package exists. This will raise
            # a NoSuchSourcePackageName exception if the source package
            # doesn't exist.
            getUtility(ISourcePackageNameSet)[name]
            # Grabbing the item at index 0 ensures it's the most recent
            # publication.
            published_sources = from_archive.getPublishedSources(
                name=name, exact_match=True,
                status=(PackagePublishingStatus.PUBLISHED,
                        PackagePublishingStatus.PENDING))
            first_source = published_sources.first()
            if first_source is not None:
                sources.append(first_source)
        return sources

    def _text_to_series(self, to_series):
        if to_series is not None:
            result = getUtility(IDistroSeriesSet).queryByName(
                self.distribution, to_series)
            if result is None:
                raise NoSuchDistroSeries(to_series)
            series = result
        else:
            series = None

        return series

    def _text_to_pocket(self, to_pocket):
        # Convert the to_pocket string to its enum.
        try:
            pocket = PackagePublishingPocket.items[to_pocket.upper()]
        except KeyError:
            raise PocketNotFound(to_pocket.upper())

        return pocket

    def _copySources(self, sources, to_pocket, to_series=None,
                     include_binaries=False, person=None):
        """Private helper function to copy sources to this archive.

        It takes a list of SourcePackagePublishingHistory but the other args
        are strings.
        """
        # Circular imports.
        from lp.soyuz.scripts.packagecopier import do_copy

        pocket = self._text_to_pocket(to_pocket)
        # Fail immediately if the destination pocket is not Release and
        # this archive is a PPA.
        if self.is_ppa and pocket != PackagePublishingPocket.RELEASE:
            raise CannotCopy(
                "Destination pocket must be 'release' for a PPA.")

        # Now convert the to_series string to a real distroseries.
        series = self._text_to_series(to_series)

        # Perform the copy, may raise CannotCopy. Don't do any further
        # permission checking: this method is protected by
        # launchpad.Append, which is mostly more restrictive than archive
        # permissions, except that it also allows ubuntu-security to
        # copy packages they wouldn't otherwise be able to.
        do_copy(
            sources, self, series, pocket, include_binaries, person=person,
            check_permissions=False)

    def getAuthToken(self, person):
        """See `IArchive`."""

        token_set = getUtility(IArchiveAuthTokenSet)
        return token_set.getActiveTokenForArchiveAndPerson(self, person)

    def newAuthToken(self, person, token=None, date_created=None):
        """See `IArchive`."""

        # Bail if the archive isn't private
        if not self.private:
            raise ArchiveNotPrivate("Archive must be private.")

        # Tokens can only be created for individuals.
        if person.is_team:
            raise NoTokensForTeams(
                "Subscription tokens can be created for individuals only.")

        # Ensure that the current subscription does not already have a token
        if self.getAuthToken(person) is not None:
            raise ArchiveSubscriptionError(
                "%s already has a token for %s." % (
                    person.displayname, self.displayname))

        # Now onto the actual token creation:
        if token is None:
            token = create_unique_token_for_table(20, ArchiveAuthToken.token)
        archive_auth_token = ArchiveAuthToken()
        archive_auth_token.archive = self
        archive_auth_token.person = person
        archive_auth_token.token = token
        if date_created is not None:
            archive_auth_token.date_created = date_created
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.add(archive_auth_token)
        return archive_auth_token

    def newSubscription(self, subscriber, registrant, date_expires=None,
                        description=None):
        """See `IArchive`."""

        # We do not currently allow subscriptions for non-private archives:
        if self.private is False:
            raise ArchiveNotPrivate(
                "Only private archives can have subscriptions.")

        # Ensure there is not already a current subscription for subscriber:
        subscriptions = getUtility(IArchiveSubscriberSet).getBySubscriber(
            subscriber, archive=self)
        if subscriptions.count() > 0:
            raise AlreadySubscribed(
            "%s already has a current subscription for '%s'." % (
                subscriber.displayname, self.displayname))

        subscription = ArchiveSubscriber()
        subscription.archive = self
        subscription.registrant = registrant
        subscription.subscriber = subscriber
        subscription.date_expires = date_expires
        subscription.description = description
        subscription.status = ArchiveSubscriberStatus.CURRENT
        subscription.date_created = UTC_NOW
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.add(subscription)

        # Notify any listeners that a new subscription was created.
        # This is used currently for sending email notifications.
        notify(ObjectCreatedEvent(subscription))

        return subscription

    @property
    def num_pkgs_building(self):
        """See `IArchive`."""
        store = Store.of(self)

        base_query = (
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.archive == self,
            PackageBuild.build_farm_job == BuildFarmJob.id)
        sprs_building = store.find(
            BinaryPackageBuild.source_package_release_id,
            BuildFarmJob.status == BuildStatus.BUILDING,
            *base_query)
        sprs_waiting = store.find(
            BinaryPackageBuild.source_package_release_id,
            BuildFarmJob.status == BuildStatus.NEEDSBUILD,
            *base_query)

        # A package is not counted as waiting if it already has at least
        # one build building.
        pkgs_building_count = sprs_building.count()
        pkgs_waiting_count = sprs_waiting.difference(sprs_building).count()

        return pkgs_building_count, pkgs_waiting_count

    def getSourcePackageReleases(self, build_status=None):
        """See `IArchive`."""
        store = Store.of(self)

        extra_exprs = []
        if build_status is not None:
            extra_exprs = [
                PackageBuild.build_farm_job == BuildFarmJob.id,
                BuildFarmJob.status == build_status,
                ]

        result_set = store.find(
            SourcePackageRelease,
            (BinaryPackageBuild.source_package_release_id ==
                SourcePackageRelease.id),
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.archive == self,
            *extra_exprs)

        result_set.config(distinct=True).order_by(SourcePackageRelease.id)
        return result_set

    def updatePackageDownloadCount(self, bpr, day, country, count):
        """See `IArchive`."""
        store = Store.of(self)
        entry = store.find(
            BinaryPackageReleaseDownloadCount, archive=self,
            binary_package_release=bpr, day=day, country=country).one()
        if entry is None:
            entry = BinaryPackageReleaseDownloadCount(
                archive=self, binary_package_release=bpr, day=day,
                country=country, count=count)
        else:
            entry.count += count

    def getPackageDownloadTotal(self, bpr):
        """See `IArchive`."""
        store = Store.of(self)
        count = store.find(
            Sum(BinaryPackageReleaseDownloadCount.count),
            BinaryPackageReleaseDownloadCount.archive == self,
            BinaryPackageReleaseDownloadCount.binary_package_release == bpr,
            ).one()
        return count or 0

    def getPackageDownloadCount(self, bpr, day, country):
        """See `IArchive`."""
        return Store.of(self).find(
            BinaryPackageReleaseDownloadCount, archive=self,
            binary_package_release=bpr, day=day, country=country).one()

    def _setBuildStatuses(self, status):
        """Update the pending Build Jobs' status for this archive."""

        query = """
            UPDATE Job SET status = %s
            FROM BinaryPackageBuild, PackageBuild, BuildFarmJob,
                 BuildPackageJob, BuildQueue
            WHERE
                BinaryPackageBuild.package_build = PackageBuild.id
                -- insert self.id here
                AND PackageBuild.archive = %s
                AND BuildPackageJob.build = BinaryPackageBuild.id
                AND BuildPackageJob.job = BuildQueue.job
                AND Job.id = BuildQueue.job
                -- Build is in state BuildStatus.NEEDSBUILD (0)
                AND PackageBuild.build_farm_job = BuildFarmJob.id
                AND BuildFarmJob.status = %s;
        """ % sqlvalues(status, self, BuildStatus.NEEDSBUILD)

        store = Store.of(self)
        store.execute(query)

    def enable(self):
        """See `IArchive`."""
        assert self._enabled == False, "This archive is already enabled."
        self._enabled = True
        self._setBuildStatuses(JobStatus.WAITING)

    def disable(self):
        """See `IArchive`."""
        assert self._enabled == True, "This archive is already disabled."
        self._enabled = False
        self._setBuildStatuses(JobStatus.SUSPENDED)

    def delete(self, deleted_by):
        """See `IArchive`."""
        assert self.status not in (
            ArchiveStatus.DELETING, ArchiveStatus.DELETED,
            "This archive is already deleted.")

        # Set all the publications to DELETED.
        statuses = (
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED)
        sources = list(self.getPublishedSources(status=statuses))
        getUtility(IPublishingSet).requestDeletion(
            sources, removed_by=deleted_by,
            removal_comment="Removed when deleting archive")

        # Mark the archive's status as DELETING so the repository can be
        # removed by the publisher.
        self.status = ArchiveStatus.DELETING
        if self.enabled:
            self.disable()

    def getFilesAndSha1s(self, source_files):
        """See `IArchive`."""
        return dict(Store.of(self).find(
            (LibraryFileAlias.filename, LibraryFileContent.sha1),
            SourcePackagePublishingHistory.archive == self,
            SourcePackageRelease.id ==
                SourcePackagePublishingHistory.sourcepackagereleaseID,
            SourcePackageReleaseFile.sourcepackagerelease ==
                SourcePackageRelease.id,
            LibraryFileAlias.id == SourcePackageReleaseFile.libraryfileID,
            LibraryFileAlias.filename.is_in(source_files),
            LibraryFileContent.id == LibraryFileAlias.contentID).config(
                distinct=True))

    def _getEnabledRestrictedFamilies(self):
        """Retrieve the restricted architecture families this archive can
        build on."""
        # Main archives are always allowed to build on restricted
        # architectures.
        if self.is_main:
            return getUtility(IProcessorFamilySet).getRestricted()
        archive_arch_set = getUtility(IArchiveArchSet)
        restricted_families = archive_arch_set.getRestrictedFamilies(self)
        return [family for (family, archive_arch) in restricted_families
                if archive_arch is not None]

    def _setEnabledRestrictedFamilies(self, value):
        """Set the restricted architecture families this archive can
        build on."""
        # Main archives are always allowed to build on restricted
        # architectures.
        if self.is_main:
            proc_family_set = getUtility(IProcessorFamilySet)
            if set(value) != set(proc_family_set.getRestricted()):
                raise CannotRestrictArchitectures("Main archives can not "
                        "be restricted to certain architectures")
        archive_arch_set = getUtility(IArchiveArchSet)
        restricted_families = archive_arch_set.getRestrictedFamilies(self)
        for (family, archive_arch) in restricted_families:
            if family in value and archive_arch is None:
                archive_arch_set.new(self, family)
            if family not in value and archive_arch is not None:
                Store.of(self).remove(archive_arch)

    enabled_restricted_families = property(_getEnabledRestrictedFamilies,
                                           _setEnabledRestrictedFamilies)

    def enableRestrictedFamily(self, family):
        """See `IArchive`."""
        restricted = set(self.enabled_restricted_families)
        restricted.add(family)
        self.enabled_restricted_families = restricted

    @classmethod
    def validatePPA(self, person, proposed_name, private=False):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        if private:
            # NOTE: This duplicates the policy in lp/soyuz/configure.zcml
            # which says that one needs 'launchpad.Commercial' permission to
            # set 'private', and the logic in `AdminByCommercialTeamOrAdmins`
            # which determines who is granted launchpad.Commercial
            # permissions.
            commercial = getUtility(ILaunchpadCelebrities).commercial_admin
            admin = getUtility(ILaunchpadCelebrities).admin
            if not person.inTeam(commercial) and not person.inTeam(admin):
                return (
                    '%s is not allowed to make private PPAs' % (person.name,))
        if person.isTeam() and (
            person.subscriptionpolicy in OPEN_TEAM_POLICY):
            return "Open teams cannot have PPAs."
        if proposed_name is not None and proposed_name == ubuntu.name:
            return (
                "A PPA cannot have the same name as its distribution.")
        if proposed_name is None:
            proposed_name = 'ppa'
        try:
            person.getPPAByName(proposed_name)
        except NoSuchPPA:
            return None
        else:
            text = "You already have a PPA named '%s'." % proposed_name
            if person.isTeam():
                text = "%s already has a PPA named '%s'." % (
                    person.displayname, proposed_name)
            return text

    def getPockets(self):
        """See `IArchive`."""
        if self.is_ppa:
            return [PackagePublishingPocket.RELEASE]

        # Cast to a list so we don't trip up with the security proxy not
        # understandiung EnumItems.
        return list(PackagePublishingPocket.items)

    def getOverridePolicy(self):
        """See `IArchive`."""
        # Circular imports.
        from lp.soyuz.adapters.overrides import UbuntuOverridePolicy
        # XXX StevenK: bug=785004 2011-05-19 Return PPAOverridePolicy() for
        # a PPA that overrides the component/pocket to main/RELEASE.
        if self.purpose in MAIN_ARCHIVE_PURPOSES:
            return UbuntuOverridePolicy()
        return None


class ArchiveSet:
    implements(IArchiveSet)
    title = "Archives registered in Launchpad"

    def get(self, archive_id):
        """See `IArchiveSet`."""
        return Archive.get(archive_id)

    def getPPAByDistributionAndOwnerName(self, distribution, person_name,
                                         ppa_name):
        """See `IArchiveSet`"""
        query = """
            Archive.purpose = %s AND
            Archive.distribution = %s AND
            Person.id = Archive.owner AND
            Archive.name = %s AND
            Person.name = %s
        """ % sqlvalues(
                ArchivePurpose.PPA, distribution, ppa_name, person_name)

        return Archive.selectOne(query, clauseTables=['Person'])

    def _getDefaultArchiveNameByPurpose(self, purpose):
        """Return the default for a archive in a given purpose.

        The default names are:

         * PRIMARY: 'primary';
         * PARTNER: 'partner';
         * PPA: 'ppa'.

        :param purpose: queried `ArchivePurpose`.

        :raise: `AssertionError` If the given purpose is not in this list,
            i.e. doesn't have a default name.

        :return: the name text to be used as name.
        """
        if purpose not in default_name_by_purpose.keys():
            raise AssertionError(
                "'%s' purpose has no default name." % purpose.name)

        return default_name_by_purpose[purpose]

    def getByDistroPurpose(self, distribution, purpose, name=None):
        """See `IArchiveSet`."""
        if purpose == ArchivePurpose.PPA:
            raise AssertionError(
                "This method should not be used to lookup PPAs. "
                "Use 'getPPAByDistributionAndOwnerName' instead.")

        if name is None:
            name = self._getDefaultArchiveNameByPurpose(purpose)

        return Archive.selectOneBy(
            distribution=distribution, purpose=purpose, name=name)

    def getByDistroAndName(self, distribution, name):
        """See `IArchiveSet`."""
        return Archive.selectOne("""
            Archive.distribution = %s AND
            Archive.name = %s AND
            Archive.purpose != %s
            """ % sqlvalues(distribution, name, ArchivePurpose.PPA))

    def _getDefaultDisplayname(self, name, owner, distribution, purpose):
        """See `IArchive`."""
        if purpose == ArchivePurpose.PPA:
            if name == default_name_by_purpose.get(purpose):
                displayname = 'PPA for %s' % owner.displayname
            else:
                displayname = 'PPA named %s for %s' % (
                    name, owner.displayname)
            return displayname

        if purpose == ArchivePurpose.COPY:
            displayname = "Copy archive %s for %s" % (
                name, owner.displayname)
            return displayname

        return '%s for %s' % (purpose.title, distribution.title)

    def new(self, purpose, owner, name=None, displayname=None,
            distribution=None, description=None, enabled=True,
            require_virtualized=True, private=False):
        """See `IArchiveSet`."""
        if distribution is None:
            distribution = getUtility(ILaunchpadCelebrities).ubuntu

        if name is None:
            name = self._getDefaultArchiveNameByPurpose(purpose)

        # Deny Archives names equal their distribution names. This conflict
        # results in archives with awkward repository URLs
        if name == distribution.name:
            raise AssertionError(
                'Archives cannot have the same name as their distribution.')

        # If displayname is not given, create a default one.
        if displayname is None:
            displayname = self._getDefaultDisplayname(
                name=name, owner=owner, distribution=distribution,
                purpose=purpose)

        # Copy archives are to be instantiated with the 'publish' flag turned
        # off.
        if purpose == ArchivePurpose.COPY:
            publish = False
        else:
            publish = True

        # For non-PPA archives we enforce unique names within the context of a
        # distribution.
        if purpose != ArchivePurpose.PPA:
            archive = Archive.selectOne(
                "Archive.distribution = %s AND Archive.name = %s" %
                sqlvalues(distribution, name))
            if archive is not None:
                raise AssertionError(
                    "archive '%s' exists already in '%s'." %
                    (name, distribution.name))
        else:
            archive = Archive.selectOneBy(
                owner=owner, name=name, purpose=ArchivePurpose.PPA)
            if archive is not None:
                raise AssertionError(
                    "Person '%s' already has a PPA named '%s'." %
                    (owner.name, name))

        # Signing-key for the default PPA is reused when it's already present.
        signing_key = None
        if purpose == ArchivePurpose.PPA:
            if owner.archive is not None:
                signing_key = owner.archive.signing_key
            else:
                # owner.archive is a cached property and we've just cached it.
                del get_property_cache(owner).archive

        new_archive = Archive(
            owner=owner, distribution=distribution, name=name,
            displayname=displayname, description=description,
            purpose=purpose, publish=publish, signing_key=signing_key,
            require_virtualized=require_virtualized)

        # Upon creation archives are enabled by default.
        if enabled == False:
            new_archive.disable()

        if purpose == ArchivePurpose.DEBUG:
            if distribution.main_archive is not None:
                del get_property_cache(
                    distribution.main_archive).debug_archive

        # Private teams cannot have public PPAs.
        if owner.visibility == PersonVisibility.PRIVATE:
            new_archive.buildd_secret = create_unique_token_for_table(
                20, Archive.buildd_secret)
            new_archive.private = True
        else:
            new_archive.private = private

        return new_archive

    def __iter__(self):
        """See `IArchiveSet`."""
        return iter(Archive.select())

    def getNumberOfPPASourcesForDistribution(self, distribution):
        cur = cursor()
        query = """
             SELECT SUM(sources_cached) FROM Archive
             WHERE purpose = %s AND private = FALSE AND
                   distribution = %s
        """ % sqlvalues(ArchivePurpose.PPA, distribution)
        cur.execute(query)
        size = cur.fetchall()[0][0]
        if size is None:
            return 0
        return int(size)

    def getNumberOfPPABinariesForDistribution(self, distribution):
        cur = cursor()
        query = """
             SELECT SUM(binaries_cached) FROM Archive
             WHERE purpose = %s AND private = FALSE AND
                   distribution = %s
        """ % sqlvalues(ArchivePurpose.PPA, distribution)
        cur.execute(query)
        size = cur.fetchall()[0][0]
        if size is None:
            return 0
        return int(size)

    def getPPAOwnedByPerson(self, person, name=None, statuses=None,
                            has_packages=False):
        """See `IArchiveSet`."""
        # See Person._members which also directly queries this.
        store = Store.of(person)
        clause = [
            Archive.purpose == ArchivePurpose.PPA,
            Archive.owner == person]
        if name is not None:
            clause.append(Archive.name == name)
        if statuses is not None:
            clause.append(Archive.status.is_in(statuses))
        if has_packages:
            clause.append(
                    SourcePackagePublishingHistory.archive == Archive.id)
        result = store.find(Archive, *clause).order_by(Archive.id).first()
        if name is not None and result is None:
            raise NoSuchPPA(name)
        return result

    def getPPAsForUser(self, user):
        """See `IArchiveSet`."""
        # Avoiding circular imports.
        from lp.soyuz.model.archivepermission import ArchivePermission

        # If there's no user logged in, then there's no archives.
        if user is None:
            return []
        store = Store.of(user)
        direct_membership = store.find(
            Archive,
            Archive.purpose == ArchivePurpose.PPA,
            TeamParticipation.team == Archive.ownerID,
            TeamParticipation.person == user,
            )
        third_party_upload_acl = store.find(
            Archive,
            Archive.purpose == ArchivePurpose.PPA,
            ArchivePermission.archiveID == Archive.id,
            TeamParticipation.person == user,
            TeamParticipation.team == ArchivePermission.personID,
            )

        result = direct_membership.union(third_party_upload_acl)
        result.order_by(Archive.displayname)

        return result

    def getPPAsPendingSigningKey(self):
        """See `IArchiveSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = (
            Archive,
            Join(SourcePackagePublishingHistory,
                 SourcePackagePublishingHistory.archive == Archive.id),
            )
        results = store.using(*origin).find(
            Archive,
            Archive.signing_key == None,
            Archive.purpose == ArchivePurpose.PPA,
            Archive._enabled == True)
        results.order_by(Archive.date_created)
        return results.config(distinct=True)

    def getLatestPPASourcePublicationsForDistribution(self, distribution):
        """See `IArchiveSet`."""
        query = """
            SourcePackagePublishingHistory.archive = Archive.id AND
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            Archive.private = FALSE AND
            Archive.enabled = TRUE AND
            DistroSeries.distribution = %s AND
            Archive.purpose = %s
        """ % sqlvalues(distribution, ArchivePurpose.PPA)

        return SourcePackagePublishingHistory.select(
            query, limit=5, clauseTables=['Archive', 'DistroSeries'],
            orderBy=['-datecreated', '-id'])

    def getMostActivePPAsForDistribution(self, distribution):
        """See `IArchiveSet`."""
        cur = cursor()
        query = """
             SELECT a.id, count(*) as C
             FROM Archive a, SourcePackagePublishingHistory spph
             WHERE
                 spph.archive = a.id AND
                 a.private = FALSE AND
                 spph.datecreated >= now() - INTERVAL '1 week' AND
                 a.distribution = %s AND
                 a.purpose = %s
             GROUP BY a.id
             ORDER BY C DESC, a.id
             LIMIT 5
        """ % sqlvalues(distribution, ArchivePurpose.PPA)

        cur.execute(query)

        most_active = []
        for archive_id, number_of_uploads in cur.fetchall():
            archive = Archive.get(int(archive_id))
            the_dict = {'archive': archive, 'uploads': number_of_uploads}
            most_active.append(the_dict)

        return most_active

    def getBuildCountersForArchitecture(self, archive, distroarchseries):
        """See `IArchiveSet`."""
        cur = cursor()
        query = """
            SELECT BuildFarmJob.status, count(BuildFarmJob.id) FROM
            BinaryPackageBuild, PackageBuild, BuildFarmJob
            WHERE
                BinaryPackageBuild.package_build = PackageBuild.id AND
                PackageBuild.build_farm_job = BuildFarmJob.id AND
                PackageBuild.archive = %s AND
                BinaryPackageBuild.distro_arch_series = %s
            GROUP BY BuildFarmJob.status ORDER BY BuildFarmJob.status;
        """ % sqlvalues(archive, distroarchseries)
        cur.execute(query)
        result = cur.fetchall()

        status_map = {
            'failed': (
                BuildStatus.CHROOTWAIT,
                BuildStatus.FAILEDTOBUILD,
                BuildStatus.FAILEDTOUPLOAD,
                BuildStatus.MANUALDEPWAIT,
                ),
            'pending': (
                BuildStatus.BUILDING,
                BuildStatus.UPLOADING,
                BuildStatus.NEEDSBUILD,
                ),
            'succeeded': (
                BuildStatus.FULLYBUILT,
                ),
            }

        status_and_counters = {}

        # Set 'total' counter
        status_and_counters['total'] = sum(
            [counter for status, counter in result])

        # Set each counter according 'status_map'
        for key, status in status_map.iteritems():
            status_and_counters[key] = 0
            for status_value, status_counter in result:
                status_values = [item.value for item in status]
                if status_value in status_values:
                    status_and_counters[key] += status_counter

        return status_and_counters

    def getPrivatePPAs(self):
        """See `IArchiveSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            Archive,
            Archive._private == True,
            Archive.purpose == ArchivePurpose.PPA)

    def getCommercialPPAs(self):
        """See `IArchiveSet`."""
        store = IStore(Archive)
        return store.find(
            Archive,
            Archive.commercial == True,
            Archive.purpose == ArchivePurpose.PPA)

    def getArchivesForDistribution(self, distribution, name=None,
                                   purposes=None, user=None,
                                   exclude_disabled=True):
        """See `IArchiveSet`."""
        extra_exprs = []

        # If a single purpose is passed in, convert it into a tuple,
        # otherwise assume a list was passed in.
        if purposes in ArchivePurpose:
            purposes = (purposes, )

        if purposes:
            extra_exprs.append(Archive.purpose.is_in(purposes))

        if name is not None:
            extra_exprs.append(Archive.name == name)

        public_archive = And(Archive._private == False,
                             Archive._enabled == True)

        if user is not None:
            admins = getUtility(ILaunchpadCelebrities).admin
            if not user.inTeam(admins):
                # Enforce privacy-awareness for logged-in, non-admin users,
                # so that they can only see the private archives that they're
                # allowed to see.

                # Create a subselect to capture all the teams that are
                # owners of archives AND the user is a member of:
                user_teams_subselect = Select(
                    TeamParticipation.teamID,
                    where=And(
                       TeamParticipation.personID == user.id,
                       TeamParticipation.teamID == Archive.ownerID))

                # Append the extra expression to capture either public
                # archives, or archives owned by the user, or archives
                # owned by a team of which the user is a member:
                # Note: 'Archive.ownerID == user.id'
                # is unnecessary below because there is a TeamParticipation
                # entry showing that each person is a member of the "team"
                # that consists of themselves.

                # FIXME: Include private PPA's if user is an uploader
                extra_exprs.append(
                    Or(public_archive,
                       Archive.ownerID.is_in(user_teams_subselect)))
        else:
            # Anonymous user; filter to include only public archives in
            # the results.
            extra_exprs.append(public_archive)

        if exclude_disabled:
            extra_exprs.append(Archive._enabled == True)

        query = Store.of(distribution).find(
            Archive,
            Archive.distribution == distribution,
            *extra_exprs)

        return query.order_by(Archive.name)

    def getPublicationsInArchives(self, source_package_name, archive_list,
                                  distribution):
        """See `IArchiveSet`."""
        archive_ids = [archive.id for archive in archive_list]

        store = Store.of(source_package_name)

        # Return all the published source pubs for the given name in the
        # given list of archives. Note: importing DistroSeries here to
        # avoid circular imports.
        from lp.registry.model.distroseries import DistroSeries
        results = store.find(
            SourcePackagePublishingHistory,
            Archive.id.is_in(archive_ids),
            SourcePackagePublishingHistory.archive == Archive.id,
            (SourcePackagePublishingHistory.status ==
                PackagePublishingStatus.PUBLISHED),
            (SourcePackagePublishingHistory.sourcepackagerelease ==
                SourcePackageRelease.id),
            SourcePackageRelease.sourcepackagename == source_package_name,
            SourcePackagePublishingHistory.distroseries == DistroSeries.id,
            DistroSeries.distribution == distribution,
            )

        return results.order_by(SourcePackagePublishingHistory.id)
