# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database class for table Archive."""

__metaclass__ = type

__all__ = ['Archive', 'ArchiveSet']

import re

from lazr.lifecycle.event import ObjectCreatedEvent
from sqlobject import  (
    BoolCol, ForeignKey, IntCol, StringCol)
from sqlobject.sqlbuilder import SQLConstant
from storm.expr import Or, And, Select
from storm.locals import Count, Join
from storm.store import Store
from zope.component import getUtility
from zope.event import notify
from zope.interface import alsoProvides, implements
from zope.security.interfaces import Unauthorized

from canonical.archiveuploader.utils import re_issource, re_isadeb
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor, quote, quote_like, sqlvalues, SQLBase)
from lp.soyuz.adapters.packagelocation import PackageLocation
from canonical.launchpad.components.tokens import (
    create_unique_token_for_table)
from lp.soyuz.model.archivedependency import (
    ArchiveDependency)
from lp.soyuz.model.archiveauthtoken import ArchiveAuthToken
from lp.soyuz.model.archivesubscriber import (
    ArchiveSubscriber)
from lp.soyuz.model.build import Build
from lp.registry.model.distributionsourcepackagecache import (
    DistributionSourcePackageCache)
from lp.soyuz.model.distroseriespackagecache import (
    DistroSeriesPackageCache)
from lp.soyuz.model.files import (
    BinaryPackageFile, SourcePackageReleaseFile)
from canonical.launchpad.database.librarian import (
    LibraryFileAlias, LibraryFileContent)
from lp.soyuz.model.packagediff import PackageDiff
from lp.soyuz.model.publishedpackage import PublishedPackage
from lp.soyuz.model.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from lp.soyuz.model.queue import (
    PackageUpload, PackageUploadSource)
from lp.registry.model.teammembership import TeamParticipation
from lp.soyuz.interfaces.archive import (
    AlreadySubscribed, ArchiveDependencyError, ArchiveNotPrivate,
    ArchivePurpose, DistroSeriesNotFound, IArchive, IArchiveSet,
    IDistributionArchive, IPPA, MAIN_ARCHIVE_PURPOSES, PocketNotFound,
    SourceNotFound, default_name_by_purpose)
from lp.soyuz.interfaces.archiveauthtoken import (
    IArchiveAuthTokenSet)
from lp.soyuz.interfaces.archivepermission import (
    ArchivePermissionType, IArchivePermissionSet)
from lp.soyuz.interfaces.archivesubscriber import (
    ArchiveSubscriberStatus, IArchiveSubscriberSet, ArchiveSubscriptionError)
from lp.soyuz.interfaces.build import (
    BuildStatus, IBuildSet)
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.component import IComponentSet
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.person import PersonVisibility
from canonical.launchpad.interfaces.launchpad import (
    IHasOwner, ILaunchpadCelebrities, NotFoundError)
from lp.soyuz.interfaces.package import PackageUploadStatus
from lp.soyuz.interfaces.packagecopyrequest import (
    IPackageCopyRequestSet)
from lp.soyuz.interfaces.publishing import (
    PackagePublishingPocket, PackagePublishingStatus, IPublishingSet,
    ISourcePackagePublishingHistory)
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageNameSet)
from lp.soyuz.scripts.packagecopier import (
    CannotCopy, check_copy, do_copy)
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.url import urlappend
from canonical.launchpad.validators.name import valid_name
from lp.registry.interfaces.person import (
    validate_person_not_private_membership)


class Archive(SQLBase):
    implements(IArchive, IHasOwner, IHasBuildRecords)
    _table = 'Archive'
    _defaultOrder = 'id'

    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_person_not_private_membership, notNull=True)

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
        if not value:
            # The archive is transitioning from public to private.
            assert self.owner.visibility != PersonVisibility.PRIVATE, (
                "Private teams may not have public PPAs.")
        return value

    name = StringCol(
        dbName='name', notNull=True, storm_validator=_validate_archive_name)

    displayname = StringCol(dbName='displayname', notNull=True)

    description = StringCol(dbName='description', notNull=False, default=None)

    distribution = ForeignKey(
        foreignKey='Distribution', dbName='distribution', notNull=False)

    purpose = EnumCol(
        dbName='purpose', unique=False, notNull=True, schema=ArchivePurpose)

    enabled = BoolCol(dbName='enabled', notNull=True, default=True)

    publish = BoolCol(dbName='publish', notNull=True, default=True)

    private = BoolCol(dbName='private', notNull=True, default=False,
                      storm_validator=_validate_archive_privacy)

    require_virtualized = BoolCol(
        dbName='require_virtualized', notNull=True, default=True)

    authorized_size = IntCol(
        dbName='authorized_size', notNull=False, default=1024)

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

    @property
    def is_ppa(self):
        """See `IArchive`."""
        return self.purpose == ArchivePurpose.PPA

    @property
    def is_copy(self):
        """See `IArchive`."""
        return self.purpose == ArchivePurpose.COPY

    @property
    def is_main(self):
        """See `IArchive`."""
        return self.purpose in MAIN_ARCHIVE_PURPOSES

    @property
    def series_with_sources(self):
        """See `IArchive`."""
        cur = cursor()
        query = """SELECT DISTINCT distroseries FROM
                      SourcePackagePublishingHistory WHERE
                      SourcePackagePublishingHistory.archive = %s"""
        cur.execute(query % self.id)
        published_series_ids = [int(row[0]) for row in cur.fetchall()]
        return [s for s in self.distribution.serieses if s.id in
                published_series_ids]

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

    @property
    def expanded_archive_dependencies(self):
        """See `IArchive`."""
        archives = []
        if self.is_ppa:
            archives.append(self.distribution.main_archive)
        archives.append(self)
        archives.extend(
            [archive_dep.dependency for archive_dep in self.dependencies])
        return archives

    @property
    def archive_url(self):
        """See `IArchive`."""
        archive_postfixes = {
            ArchivePurpose.PRIMARY : '',
            ArchivePurpose.PARTNER : '-partner',
        }

        if self.is_ppa:
            if self.private:
                url = config.personalpackagearchive.private_base_url
            else:
                url = config.personalpackagearchive.base_url
            return urlappend(
                url, "/".join(
                    (self.owner.name, self.name, self.distribution.name)))

        try:
            postfix = archive_postfixes[self.purpose]
        except KeyError:
            raise AssertionError(
                "archive_url unknown for purpose: %s" % self.purpose)
        return urlappend(
            config.archivepublisher.base_url,
            self.distribution.name + postfix)

    @property
    def signing_key_fingerprint(self):
        if self.signing_key is not None:
            return self.signing_key.fingerprint

        return None

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        user=None):
        """See IHasBuildRecords"""
        # Ignore "user", since anyone already accessing this archive
        # will implicitly have permission to see it.
        return getUtility(IBuildSet).getBuildsForArchive(
            self, build_state, name, pocket)

    def getPublishedSources(self, name=None, version=None, status=None,
                            distroseries=None, pocket=None,
                            exact_match=False, created_since_date=None):
        """See `IArchive`."""
        clauses = ["""
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self)]
        clauseTables = ['SourcePackageRelease', 'SourcePackageName']
        orderBy = ['SourcePackageName.name',
                   '-SourcePackagePublishingHistory.id']

        if name is not None:
            if exact_match:
                clauses.append("""
                    SourcePackageName.name=%s
                """ % sqlvalues(name))
            else:
                clauses.append("""
                    SourcePackageName.name LIKE '%%' || %s || '%%'
                """ % quote_like(name))

        if version is not None:
            assert name is not None, (
                "'version' can be only used when name is set")
            clauses.append("""
                SourcePackageRelease.version = %s
            """ % sqlvalues(version))
        else:
            order_const = "debversion_sort_key(SourcePackageRelease.version)"
            desc_version_order = SQLConstant(order_const+" DESC")
            orderBy.insert(1, desc_version_order)

        if status is not None:
            try:
                status = tuple(status)
            except TypeError:
                status = (status,)
            clauses.append("""
                SourcePackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroseries is not None:
            clauses.append("""
                SourcePackagePublishingHistory.distroseries = %s
            """ % sqlvalues(distroseries))

        if pocket is not None:
            clauses.append("""
                SourcePackagePublishingHistory.pocket = %s
            """ % sqlvalues(pocket))

        if created_since_date is not None:
            clauses.append("""
                SourcePackagePublishingHistory.datecreated >= %s
            """ % sqlvalues(created_since_date))

        preJoins = [
            'sourcepackagerelease.creator',
            'sourcepackagerelease.dscsigningkey',
            'distroseries',
            'section',
            ]

        sources = SourcePackagePublishingHistory.select(
            ' AND '.join(clauses), clauseTables=clauseTables, orderBy=orderBy,
            prejoins=preJoins)

        return sources

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
                BinaryPackageRelease bpr, Build
            WHERE
                bpph.archive = %s AND
                bpph.status = %s AND
                bpph.binarypackagerelease = bpr.id AND
                bpr.build = Build.id AND
                Build.sourcepackagerelease = SourcePackageRelease.id)
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
                status = (status,)
            clauses.append("""
                SourcePackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroseries is not None:
            clauses.append("""
                SourcePackagePublishingHistory.distroseries = %s
            """ % sqlvalues(distroseries))

        clauseTables = ['SourcePackageRelease', 'SourcePackageName']

        order_const = "debversion_sort_key(SourcePackageRelease.version)"
        desc_version_order = SQLConstant(order_const+" DESC")
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
        result = store.find(
            (LibraryFileContent),
            SourcePackagePublishingHistory.archive == self.id,
            SourcePackagePublishingHistory.dateremoved == None,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                SourcePackageReleaseFile.sourcepackagereleaseID,
            SourcePackageReleaseFile.libraryfileID == LibraryFileAlias.id,
            LibraryFileAlias.contentID == LibraryFileContent.id)

        # We need to select distinct `LibraryFileContent`s because that how
        # they end up published in the archive disk. Duplications may happen
        # because of the publishing records join, the same `LibraryFileAlias`
        # gets logically re-published in several locations and the fact that
        # the same `LibraryFileContent` can be shared by multiple
        # `LibraryFileAlias.` (librarian-gc).
        result = result.config(distinct=True)
        size = sum([lfc.filesize for lfc in result])
        return size

    def _getBinaryPublishingBaseClauses (
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
            assert name is not None, (
                "'version' can be only used when name is set")
            clauses.append("""
                BinaryPackageRelease.version = %s
            """ % sqlvalues(version))
        else:
            order_const = "debversion_sort_key(BinaryPackageRelease.version)"
            desc_version_order = SQLConstant(order_const + " DESC")
            orderBy.insert(1, desc_version_order)

        if status is not None:
            try:
                status = tuple(status)
            except TypeError:
                status = (status,)
            clauses.append("""
                BinaryPackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroarchseries is not None:
            try:
                distroarchseries = tuple(distroarchseries)
            except TypeError:
                distroarchseries = (distroarchseries,)
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
            ' AND '.join(clauses) , clauseTables=clauseTables,
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
            no_nominated_arch_independents)

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
        result = store.find(
            (LibraryFileContent),
            BinaryPackagePublishingHistory.archive == self.id,
            BinaryPackagePublishingHistory.dateremoved == None,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageFile.binarypackagereleaseID,
            BinaryPackageFile.libraryfileID == LibraryFileAlias.id,
            LibraryFileAlias.contentID == LibraryFileContent.id)

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
            ArchivePurpose.COPY : True,
            ArchivePurpose.PARTNER : True,
            ArchivePurpose.PPA : True,
            ArchivePurpose.PRIMARY : False,
        }

        try:
            permission = purposeToPermissionMap[self.purpose]
        except KeyError:
            # Future proofing for when new archive types are added.
            permission = False

        return permission

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

    def findDepCandidateByName(self, distroarchseries, name):
        """See `IArchive`."""
        archives = [
            archive.id for archive in self.expanded_archive_dependencies]

        query = """
            binarypackagename = %s AND
            distroarchseries = %s AND
            archive IN %s AND
            packagepublishingstatus = %s
        """ % sqlvalues(name, distroarchseries, archives,
                        PackagePublishingStatus.PUBLISHED)

        return PublishedPackage.selectFirst(query, orderBy=['-id'])

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
                "Only one dependency record per archive is supported.")

        if dependency.is_ppa:
            if pocket is not PackagePublishingPocket.RELEASE:
                raise ArchiveDependencyError(
                    "Non-primary archives only support the RELEASE pocket.")
            if (component is not None and
                component.id is not getUtility(IComponentSet)['main'].id):
                raise ArchiveDependencyError(
                    "Non-primary archives only support the 'main' component.")

        return ArchiveDependency(
            archive=self, dependency=dependency, pocket=pocket,
            component=component)

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

    def getBuildCounters(self, include_needsbuild=True):
        """See `IArchiveSet`."""

        # First grab a count of each build state for all the builds in
        # this archive:
        store = Store.of(self)
        extra_exprs = []
        if not include_needsbuild:
            extra_exprs.append(Build.buildstate != BuildStatus.NEEDSBUILD)

        find_spec = (
            Build.buildstate,
            Count(Build.id)
            )
        result = store.using(Build).find(
            find_spec,
            Build.archive == self,
            *extra_exprs
            ).group_by(Build.buildstate).order_by(Build.buildstate)

        # Create a map for each count summary to a number of buildstates:
        count_map = {
            'failed': (
                BuildStatus.CHROOTWAIT,
                BuildStatus.FAILEDTOBUILD,
                BuildStatus.FAILEDTOUPLOAD,
                BuildStatus.MANUALDEPWAIT,
                ),
             # The 'pending' count is a list because we may append to it
             # later.
            'pending': [
                BuildStatus.BUILDING,
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
                BuildStatus.FULLYBUILT,
                BuildStatus.SUPERSEDED,
                ]
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

    def canUpload(self, user, component_or_package=None):
        """See `IArchive`."""
        assert not self.is_copy, "Uploads to copy archives are not allowed."
        if self.is_ppa:
            return user.inTeam(self.owner)
        else:
            return self._authenticate(
                user, component_or_package, ArchivePermissionType.UPLOAD)

    def canAdministerQueue(self, user, component):
        """See `IArchive`."""
        return self._authenticate(
            user, component, ArchivePermissionType.QUEUE_ADMIN)

    def _authenticate(self, user, component, permission):
        """Private helper method to check permissions."""
        permissions = self.getPermissions(user, component, permission)
        return permissions.count() > 0

    def newPackageUploader(self, person, source_package_name):
        """See `IArchive`."""
        permission_set = getUtility(IArchivePermissionSet)
        return permission_set.newPackageUploader(
            self, person, source_package_name)

    def newComponentUploader(self, person, component_name):
        """See `IArchive`."""
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

    def getFileByName(self, filename):
        """See `IArchive`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        base_clauses = (
            LibraryFileAlias.filename == filename,
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
                    to_series=None, include_binaries=False):
        """See `IArchive`."""
        # Find and validate the source package names in source_names.
        sources = []
        name_utility = getUtility(ISourcePackageNameSet)
        for name in source_names:
            try:
                source_package_name = name_utility[name]
            except NotFoundError, e:
                # Webservice-friendly exception.
                raise SourceNotFound(e)
            # Grabbing the item at index 0 ensures it's the most recent
            # publication.
            sources.append(
                from_archive.getPublishedSources(
                    name=name, exact_match=True)[0])

        return self._copySources(
            sources, to_pocket, to_series, include_binaries)

    def syncSource(self, source_name, version, from_archive, to_pocket,
                   to_series=None, include_binaries=False):
        """See `IArchive`."""
        # Find and validate the source package version required.
        try:
            source_package_name = getUtility(
                ISourcePackageNameSet)[source_name]
        except NotFoundError, e:
            # Webservice-friendly exception.
            raise SourceNotFound(e)

        source = from_archive.getPublishedSources(
            name=source_name, version=version, exact_match=True)

        self._copySources(source, to_pocket, to_series, include_binaries)

    def _copySources(self, sources, to_pocket, to_series=None,
                     include_binaries=False):
        """Private helper function to copy sources to this archive.

        It takes a list of SourcePackagePublishingHistory but the other args
        are strings.
        """
        # Convert the to_pocket string to its enum.
        try:
            pocket = PackagePublishingPocket.items[to_pocket.upper()]
        except KeyError, error:
            raise PocketNotFound(error)

        # Fail immediately if the destination pocket is not Release and
        # this archive is a PPA.
        if self.is_ppa and pocket != PackagePublishingPocket.RELEASE:
            raise CannotCopy(
                "Destination pocket must be 'release' for a PPA.")

        # Now convert the to_series string to a real distroseries.
        if to_series is not None:
            result = getUtility(IDistroSeriesSet).queryByName(
                self.distribution, to_series)
            if result is None:
                raise DistroSeriesNotFound(to_series)
            series = result
        else:
            series = None

        # Validate the copy.
        broken_copies = []
        for source in sources:
            try:
                check_copy(
                    source, self, series, pocket, include_binaries)
            except CannotCopy, reason:
                broken_copies.append("%s (%s)" % (source.displayname, reason))

        if len(broken_copies) != 0:
            raise CannotCopy("\n".join(broken_copies))

        # Perform the copy.
        copies = do_copy(
            sources, self, series, pocket, include_binaries)

        if len(copies) == 0:
            raise CannotCopy("Packages already copied.")

        # Return a list of string names of source packages that were copied.
        # We only return source package names, even when binaries were copied,
        # because that's the "Contract".
        return [
            copy.sourcepackagerelease.sourcepackagename.name
            for copy in copies
            if ISourcePackagePublishingHistory.providedBy(copy)]

    def newAuthToken(self, person, token=None, date_created=None):
        """See `IArchive`."""

        # First, ensure that a current subscription exists for the
        # person and archive:
        # XXX: noodles 2009-03-02 bug=336779: This can be removed once
        # newAuthToken() is moved into IArchiveView.
        subscription_set = getUtility(IArchiveSubscriberSet)
        subscriptions = subscription_set.getBySubscriber(person, archive=self)
        if subscriptions.count() == 0:
            raise Unauthorized(
                "You do not have a subscription for %s." % self.displayname)

        # Second, ensure that the current subscription does not already
        # have a token:
        token_set = getUtility(IArchiveAuthTokenSet)
        previous_token = token_set.getActiveTokenForArchiveAndPerson(
            self, person)
        if previous_token:
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
            require_virtualized=True):
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
                owner=owner, distribution=distribution, name=name,
                purpose=ArchivePurpose.PPA)
            if archive is not None:
                raise AssertionError(
                    "Person '%s' already has a PPA named '%s'." %
                    (owner.name, name))

        # Signing-key for the default PPA is reused when it's already present.
        signing_key = None
        if purpose == ArchivePurpose.PPA and owner.archive is not None:
            signing_key = owner.archive.signing_key

        new_archive = Archive(
            owner=owner, distribution=distribution, name=name,
            displayname=displayname, description=description,
            purpose=purpose, publish=publish, signing_key=signing_key,
            enabled=enabled, require_virtualized=require_virtualized)

        # Private teams cannot have public PPAs.
        if owner.visibility == PersonVisibility.PRIVATE:
            new_archive.buildd_secret = create_unique_token_for_table(
                20, Archive.buildd_secret)
            new_archive.private = True

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

    def getPPAsForUser(self, user):
        """See `IArchiveSet`."""
        query = """
            Archive.owner = Person.id AND
            TeamParticipation.team = Archive.owner AND
            TeamParticipation.person = %s AND
            Archive.purpose = %s
        """ % sqlvalues(user, ArchivePurpose.PPA)

        return Archive.select(
            query, clauseTables=['Person', 'TeamParticipation'],
            orderBy=['Person.displayname'])

    def getPPAsPendingSigningKey(self):
        """See `IArchiveSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = (
            Archive,
            Join(SourcePackagePublishingHistory,
                 SourcePackagePublishingHistory.archive == Archive.id),)
        results = store.using(*origin).find(
            Archive,
            Archive.signing_key == None,
            Archive.purpose == ArchivePurpose.PPA,
            Archive.enabled == True)
        results.order_by(Archive.date_created)
        return results.config(distinct=True)

    def getLatestPPASourcePublicationsForDistribution(self, distribution):
        """See `IArchiveSet`."""
        query = """
            SourcePackagePublishingHistory.archive = Archive.id AND
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            Archive.private = FALSE AND
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
            SELECT buildstate, count(id) FROM Build
            WHERE archive = %s AND distroarchseries = %s
            GROUP BY buildstate ORDER BY buildstate;
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
            Archive.private == True,
            Archive.purpose == ArchivePurpose.PPA)

    def getArchivesForDistribution(self, distribution, name=None,
                                   purposes=None, user=None):
        """See `IArchiveSet`."""
        extra_exprs = []

        # If a single purpose is passed in, convert it into a tuple,
        # otherwise assume a list was passed in.
        if purposes in ArchivePurpose:
            purposes = (purposes,)

        if purposes:
            extra_exprs.append(Archive.purpose.is_in(purposes))

        if name is not None:
            extra_exprs.append(Archive.name == name)

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
                extra_exprs.append(
                    Or(
                        Archive.private == False,
                        Archive.ownerID.is_in(user_teams_subselect)))

        else:
            # Anonymous user; filter to include only public archives in
            # the results.
            extra_exprs.append(Archive.private == False)


        query = Store.of(distribution).find(
            Archive,
            Archive.distribution == distribution,
            *extra_exprs)

        return query
