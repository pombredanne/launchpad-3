# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution release."""

__metaclass__ = type

__all__ = [
    'DistroRelease',
    'DistroReleaseSet',
    ]

from cStringIO import StringIO

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, MultipleJoin, IntCol, SQLObjectNotFound,
    RelatedJoin)

from canonical.database.sqlbase import (
    SQLBase, sqlvalues, flush_database_updates, cursor, flush_database_caches)
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.lp.dbschema import (
    PackagePublishingStatus, BugTaskStatus, EnumCol, DistributionReleaseStatus,
    DistroReleaseQueueStatus, PackagePublishingPocket, SpecificationSort)

from canonical.launchpad.interfaces import (
    IDistroRelease, IDistroReleaseSet, ISourcePackageName,
    IPublishedPackageSet, IHasBuildRecords, NotFoundError,
    IBinaryPackageName, ILibraryFileAliasSet)

from canonical.database.constants import DEFAULT, UTC_NOW

from canonical.launchpad.database.binarypackagename import (
    BinaryPackageName)
from canonical.launchpad.database.distroreleasebinarypackage import (
    DistroReleaseBinaryPackage)
from canonical.launchpad.database.distroreleasesourcepackagerelease import (
    DistroReleaseSourcePackageRelease)
from canonical.launchpad.database.distroreleasepackagecache import (
    DistroReleasePackageCache)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishing, SourcePackagePublishing,
    BinaryPackagePublishingHistory, SourcePackagePublishingHistory)
from canonical.launchpad.database.distroarchrelease import DistroArchRelease
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.distroreleaselanguage import (
    DistroReleaseLanguage, DummyDistroReleaseLanguage)
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.bugtask import BugTaskSet, BugTask
from canonical.launchpad.database.binarypackagerelease import (
        BinaryPackageRelease)
from canonical.launchpad.database.component import Component
from canonical.launchpad.database.section import Section
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.specification import Specification
from canonical.launchpad.database.queue import DistroReleaseQueue
from canonical.launchpad.helpers import shortlist


class DistroRelease(SQLBase):
    """A particular release of a distribution."""
    implements(IDistroRelease, IHasBuildRecords)

    _table = 'DistroRelease'
    _defaultOrder = ['distribution', 'version']

    distribution = ForeignKey(dbName='distribution',
                              foreignKey='Distribution', notNull=True)
    bugtasks = MultipleJoin('BugTask', joinColumn='distrorelease')
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    releasestatus = EnumCol(notNull=True, schema=DistributionReleaseStatus)
    datereleased = UtcDateTimeCol(notNull=False, default=None)
    parentrelease =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroRelease', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    lucilleconfig = StringCol(notNull=False, default=None)
    changeslist = StringCol(notNull=False, default=None)
    nominatedarchindep = ForeignKey(
        dbName='nominatedarchindep',foreignKey='DistroArchRelease',
        notNull=False, default=None)
    datelastlangpack = UtcDateTimeCol(dbName='datelastlangpack', notNull=False,
        default=None)
    messagecount = IntCol(notNull=True, default=0)
    binarycount = IntCol(notNull=True, default=DEFAULT)
    sourcecount = IntCol(notNull=True, default=DEFAULT)

    architectures = MultipleJoin(
        'DistroArchRelease', joinColumn='distrorelease',
        orderBy='architecturetag')
    binary_package_caches = MultipleJoin('DistroReleasePackageCache',
        joinColumn='distrorelease', orderBy='name')

    components = RelatedJoin(
        'Component', joinColumn='distrorelease', otherColumn='component',
        intermediateTable='ComponentSelection')
    sections = RelatedJoin(
        'Section', joinColumn='distrorelease', otherColumn='section',
        intermediateTable='SectionSelection')

    @property
    def packagings(self):
        packagings = list(Packaging.selectBy(distroreleaseID=self.id))
        packagings.sort(key=lambda a:a.sourcepackagename.name)
        return packagings

    @property
    def distroreleaselanguages(self):
        result = DistroReleaseLanguage.selectBy(distroreleaseID=self.id)
        return sorted(result, key=lambda a: a.language.englishname)

    @property
    def translatable_sourcepackages(self):
        """See IDistroRelease."""
        result = SourcePackageName.select("""
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distrorelease = %s
            """ % sqlvalues(self.id),
            clauseTables=['POTemplate'],
            orderBy=['name'])
        return [SourcePackage(sourcepackagename=spn, distrorelease=self) for
            spn in result]

    @property
    def previous_releases(self):
        """See IDistroRelease."""
        datereleased = self.datereleased
        # if this one is unreleased, use the last released one
        if not datereleased:
            datereleased = 'NOW'
        return DistroRelease.select('''
                distribution = %s AND
                datereleased < %s
                ''' % sqlvalues(self.distribution.id, datereleased),
                orderBy=['-datereleased'])

    @property
    def parent(self):
        """See IDistroRelease."""
        if self.parentrelease:
            return self.parentrelease.title
        return ''

    @property
    def status(self):
        return self.releasestatus.title

    def updatePackageCount(self):
        """See IDistroRelease."""

        # first update the source package count
        query = """
            SourcePackagePublishing.distrorelease = %s AND
            SourcePackagePublishing.status = %s AND
            SourcePackagePublishing.pocket = %s AND
            SourcePackagePublishing.sourcepackagerelease = 
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(
                self.id,
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingPocket.RELEASE)
        self.sourcecount = SourcePackageName.select(query,
            distinct=True,
            clauseTables=['SourcePackageRelease',
                'SourcePackagePublishing']).count()

        # next update the binary count
        clauseTables = ['DistroArchRelease', 'BinaryPackagePublishing',
                        'BinaryPackageRelease']
        query = """
            BinaryPackagePublishing.binarypackagerelease = 
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishing.status = %s AND
            BinaryPackagePublishing.pocket = %s AND
            BinaryPackagePublishing.distroarchrelease = 
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s
            """ % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingPocket.RELEASE,
                self.id)
        ret = BinaryPackageName.select(
            query, distinct=True, clauseTables=clauseTables).count()
        self.binarycount = ret

    @property
    def architecturecount(self):
        """See IDistroRelease."""
        return len(list(self.architectures))

    @property
    def potemplates(self):
        result = POTemplate.selectBy(distroreleaseID=self.id)
        result = list(result)
        return sorted(result, key=lambda x: x.potemplatename.name)

    @property
    def currentpotemplates(self):
        result = POTemplate.selectBy(distroreleaseID=self.id, iscurrent=True)
        result = list(result)
        return sorted(result, key=lambda x: x.potemplatename.name)

    @property
    def fullreleasename(self):
        return "%s %s" % (
            self.distribution.name.capitalize(), self.name.capitalize())

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistributionRelease(self)
        return BugTaskSet().search(search_params)

    def specifications(self, sort=None, quantity=None):
        """See IHasSpecifications."""
        if sort is None or sort == SpecificationSort.DATE:
            order = ['-datecreated', 'id']
        elif sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'status', 'name']
        return Specification.selectBy(distroreleaseID=self.id,
            orderBy=order)[:quantity]

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return self.distribution.getSpecification(name)

    @property
    def open_cve_bugtasks(self):
        """See IDistroRelease."""
        result = BugTask.select("""
            CVE.id = BugCve.cve AND
            BugCve.bug = Bug.id AND
            BugTask.bug = Bug.id AND
            BugTask.distrorelease=%s AND
            BugTask.status IN (%s, %s)
            """ % sqlvalues(
                self.id,
                BugTaskStatus.NEW,
                BugTaskStatus.ACCEPTED),
            clauseTables=['Bug', 'Cve', 'BugCve'],
            orderBy=['-severity', 'datecreated'])
        return result

    @property
    def resolved_cve_bugtasks(self):
        """See IDistroRelease."""
        result = BugTask.select("""
            CVE.id = BugCve.cve AND
            BugCve.bug = Bug.id AND
            BugTask.bug = Bug.id AND
            BugTask.distrorelease=%s AND
            BugTask.status IN (%s, %s, %s)
            """ % sqlvalues(
                self.id,
                BugTaskStatus.REJECTED,
                BugTaskStatus.FIXED,
                BugTaskStatus.PENDINGUPLOAD),
            clauseTables=['Bug', 'Cve', 'BugCve'],
            orderBy=['-severity', 'datecreated'])
        return result

    def getDistroReleaseLanguage(self, language):
        """See IDistroRelease."""
        return DistroReleaseLanguage.selectOneBy(
            distroreleaseID=self.id,
            languageID=language.id)

    def getDistroReleaseLanguageOrDummy(self, language):
        """See IDistroRelease."""
        drl = self.getDistroReleaseLanguage(language)
        if drl is not None:
            return drl
        return DummyDistroReleaseLanguage(self, language)

    def updateStatistics(self, ztm):
        """See IDistroRelease."""
        # first find the set of all languages for which we have pofiles in
        # the distribution
        langidset = set([
            language.id for language in Language.select('''
                Language.id = POFile.language AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distrorelease = %s
                ''' % sqlvalues(self.id),
                orderBy=['code'],
                distinct=True,
                clauseTables=['POFile', 'POTemplate'])
            ])
        # now run through the existing DistroReleaseLanguages for the
        # distrorelease, and update their stats, and remove them from the
        # list of languages we need to have stats for
        for distroreleaselanguage in self.distroreleaselanguages:
            distroreleaselanguage.updateStatistics(ztm)
            langidset.discard(distroreleaselanguage.language.id)
        # now we should have a set of languages for which we NEED
        # to have a DistroReleaseLanguage
        for langid in langidset:
            drl = DistroReleaseLanguage(distrorelease=self, languageID=langid)
            drl.updateStatistics(ztm)
        # lastly, we need to update the message count for this distro
        # release itself
        messagecount = 0
        for potemplate in self.potemplates:
            messagecount += potemplate.messageCount()
        self.messagecount = messagecount
        ztm.commit()

    def getSourcePackage(self, name):
        """See IDistroRelease."""
        if not ISourcePackageName.providedBy(name):
            try:
                name = SourcePackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return SourcePackage(sourcepackagename=name, distrorelease=self)

    def getBinaryPackage(self, name):
        """See IDistroRelease."""
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroReleaseBinaryPackage(self, name)

    def getSourcePackageRelease(self, sourcepackagerelease):
        """See IDistroRelease."""
        return DistroReleaseSourcePackageRelease(self, sourcepackagerelease)

    def __getitem__(self, archtag):
        """See IDistroRelease."""
        item = DistroArchRelease.selectOneBy(
            distroreleaseID=self.id, architecturetag=archtag)
        if item is None:
            raise NotFoundError('Unknown architecture %s for %s %s' % (
                archtag, self.distribution.name, self.name))
        return item

    def getPublishedReleases(self, sourcepackage_or_name, pocket=None):
        """See IDistroRelease."""
        if ISourcePackageName.providedBy(sourcepackage_or_name):
            sourcepackage = sourcepackage_or_name
        else:
            sourcepackage = sourcepackage_or_name.name
        pocketclause = ""
        if pocket is not None:
            pocketclause = "AND pocket=%s" % sqlvalues(pocket.value)
        published = SourcePackagePublishing.select((
            """
            distrorelease = %s AND
            status = %s AND
            sourcepackagerelease = sourcepackagerelease.id AND
            sourcepackagerelease.sourcepackagename = %s
            """ % sqlvalues(self.id,
                            PackagePublishingStatus.PUBLISHED,
                            sourcepackage.id))+pocketclause,
            clauseTables = ['SourcePackageRelease'])
        return shortlist(published)

    def getAllReleasesByStatus(self, status):
        """See IDistroRelease."""
        return SourcePackagePublishing.selectBy(distroreleaseID=self.id,
                                                status=status)

    def publishedBinaryPackages(self, component=None):
        """See IDistroRelease."""
        # XXX sabdfl 04/07/05 this can become a utility when that works
        # this is used by the debbugs import process, mkdebwatches
        pubpkgset = getUtility(IPublishedPackageSet)
        result = pubpkgset.query(distrorelease=self, component=component)
        return [BinaryPackageRelease.get(pubrecord.binarypackagerelease)
                for pubrecord in result]

    def getBuildRecords(self, status=None, limit=10):
        """See IHasBuildRecords"""
        # find out the distroarchrelease in question
        arch_ids = ','.join(
            '%d' % arch.id for arch in self.architectures)

        # if no distroarchrelease was found return None
        if not arch_ids:
            return None

        # specific status or simply worked
        if status:
            status_clause = "buildstate=%s" % sqlvalues(status)
        else:
            status_clause = "builder is not NULL"

        return Build.select(
            "distroarchrelease IN (%s) AND %s" % (arch_ids, status_clause),
            limit=limit, orderBy="-datebuilt")

    def createUploadedSourcePackageRelease(self, sourcepackagename,
            version, maintainer, dateuploaded, builddepends,
            builddependsindep, architecturehintlist, component,
            creator, urgency, changelog, dsc, dscsigningkey, section,
            manifest):
        """See IDistroRelease."""
        return SourcePackageRelease(uploaddistrorelease=self.id,
                                    sourcepackagename=sourcepackagename,
                                    version=version,
                                    maintainer=maintainer,
                                    dateuploaded=dateuploaded,
                                    builddepends=builddepends,
                                    builddependsindep=builddependsindep,
                                    architecturehintlist=architecturehintlist,
                                    component=component,
                                    creator=creator,
                                    urgency=urgency,
                                    changelog=changelog,
                                    dsc=dsc,
                                    dscsigningkey=dscsigningkey,
                                    section=section,
                                    manifest=manifest)

    def getComponentByName(self, name):
        """See IDistroRelease."""
        comp = Component.byName(name)
        if comp is None:
            raise NotFoundError(name)
        permitted = set(self.components)
        if comp in permitted:
            return comp
        raise NotFoundError(name)

    def getSectionByName(self, name):
        """See IDistroRelease."""
        section = Section.byName(name)
        if section is None:
            raise NotFoundError(name)
        permitted = set(self.sections)
        if section in permitted:
            return section
        raise NotFoundError(name)

    def removeOldCacheItems(self):
        """See IDistroRelease."""

        # get the set of package names that should be there
        bpns = set(BinaryPackageName.select("""
            BinaryPackagePublishing.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id
            """ % sqlvalues(self.id),
            distinct=True,
            clauseTables=['BinaryPackagePublishing', 'DistroArchRelease',
                'BinaryPackageRelease']))

        # remove the cache entries for binary packages we no longer want
        for cache in self.binary_package_caches:
            if cache.binarypackagename not in bpns:
                cache.destroySelf()

    def updateCompletePackageCache(self, ztm=None):
        """See IDistroRelease."""

        # get the set of package names to deal with
        bpns = list(BinaryPackageName.select("""
            BinaryPackagePublishing.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id
            """ % sqlvalues(self.id),
            distinct=True,
            clauseTables=['BinaryPackagePublishing', 'DistroArchRelease',
                'BinaryPackageRelease']))

        # now ask each of them to update themselves. commit every 100
        # packages
        counter = 0
        for bpn in bpns:
            self.updatePackageCache(bpn)
            counter += 1
            if counter > 99:
                counter = 0
                if ztm is not None:
                    ztm.commit()


    def updatePackageCache(self, binarypackagename):
        """See IDistroRelease."""

        # get the set of published binarypackagereleases
        bprs = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishing.binarypackagerelease AND
            BinaryPackagePublishing.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s
            """ % sqlvalues(binarypackagename.id, self.id),
            orderBy='-datecreated',
            clauseTables=['BinaryPackagePublishing', 'DistroArchRelease'],
            distinct=True)
        if len(bprs) == 0:
            return

        # find or create the cache entry
        cache = DistroReleasePackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.id, binarypackagename.id))
        if cache is None:
            cache = DistroReleasePackageCache(
                distrorelease=self,
                binarypackagename=binarypackagename)

        # make sure the cached name, summary and description are correct
        cache.name = binarypackagename.name
        cache.summary = bprs[0].summary
        cache.description = bprs[0].description

        # get the sets of binary package summaries, descriptions. there is
        # likely only one, but just in case...

        summaries = set()
        descriptions = set()
        for bpr in bprs:
            summaries.add(bpr.summary)
            descriptions.add(bpr.description)

        # and update the caches
        cache.summaries = ' '.join(sorted(summaries))
        cache.descriptions = ' '.join(sorted(descriptions))

    def searchPackages(self, text):
        """See IDistroRelease."""
        drpcaches = DistroReleasePackageCache.select("""
            distrorelease = %s AND
            fti @@ ftq(%s)
            """ % sqlvalues(self.id, text),
            selectAlso='rank(fti, ftq(%s)) AS rank' % sqlvalues(text),
            orderBy=['-rank'],
            distinct=True)
        return [DistroReleaseBinaryPackage(
            distrorelease=self,
            binarypackagename=drpc.binarypackagename) for drpc in drpcaches]

    def newArch(self, architecturetag, processorfamily, official, owner):
        """See IDistroRelease."""
        dar = DistroArchRelease(architecturetag=architecturetag,
            processorfamily=processorfamily, official=official,
            distrorelease=self, owner=owner)
        return dar

    def createQueueEntry(self, pocket, changesfilename, changesfilecontent):
        """See IDistroRelease."""
        file_alias_set = getUtility(ILibraryFileAliasSet)
        changes_file = file_alias_set.create(changesfilename,
            len(changesfilecontent), StringIO(changesfilecontent),
            'text/plain')
        return DistroReleaseQueue(distrorelease=self.id,
                                  pocket=pocket,
                                  changesfilealias=changes_file.id)

    def getQueueItems(self, status=DistroReleaseQueueStatus.ACCEPTED):
        """See IDistroRelease."""

        return DistroReleaseQueue.selectBy(distroreleaseID=self.id,
                                           status=status)

    def createBug(self, owner, title, comment, private=False):
        """See canonical.launchpad.interfaces.IBugTarget."""
        # We don't currently support opening a new bug on an IDistroRelease,
        # because internally bugs are reported against IDistroRelease only when
        # targetted to be fixed in that release, which is rarely the case for a
        # brand new bug report.
        raise NotImplementedError(
            "A new bug cannot be filed directly on a distribution release, "
            "because releases are meant for \"targeting\" a fix to a specific "
            "release. It's possible that we may change this behaviour to "
            "allow filing a bug on a distribution release in the "
            "not-too-distant future. For now, you probably meant to file "
            "the bug on the distribution instead.")

    def initialiseFromParent(self):
        """See IDistroRelease."""
        assert self.parentrelease is not None, "Parent release must be present"
        assert SourcePackagePublishingHistory.selectBy(
            distroreleaseID=self.id).count() == 0, \
            "Source Publishing must be empty"
        for arch in self.architectures:
            assert BinaryPackagePublishingHistory.selectBy(
                distroarchreleaseID=arch.id).count() == 0, \
                "Binary Publishing must be empty"
            try:
                parent_arch = self.parentrelease[arch.architecturetag]
                assert parent_arch.processorfamily == arch.processorfamily, \
                       "The arch tags must match the processor families."
            except KeyError:
                raise AssertionError("Parent release lacks %s" % (
                    arch.architecturetag))
        assert self.nominatedarchindep is not None, \
               "Must have a nominated archindep architecture."
        assert len(self.components) == 0, \
               "Component selections must be empty."
        assert len(self.sections) == 0, \
               "Section selections must be empty."

        # MAINTAINER: dsilvers: 20051031
        # Here we go underneath the SQLObject caching layers in order to
        # generate what will potentially be tens of thousands of rows
        # in various tables. Thus we flush pending updates from the SQLObject
        # layer, perform our work directly in the transaction and then throw
        # the rest of the SQLObject cache away to make sure it hasn't cached
        # anything that is no longer true.
        
        # Prepare for everything by flushing updates to the database.
        flush_database_updates()
        cur = cursor()

        # Perform the copies
        self._copy_component_and_section_selections(cur)
        self._copy_source_publishing_records(cur)
        for arch in self.architectures:
            parent_arch = self.parentrelease[arch.architecturetag]
            self._copy_binary_publishing_records(cur, arch, parent_arch)
        self._copy_lucille_config(cur)
        
        # Finally, flush the caches because we've altered stuff behind the
        # back of sqlobject.
        flush_database_caches()

    def _copy_lucille_config(self, cur):
        """Copy all lucille related configuration from our parent release."""
        cur.execute('''
            UPDATE DistroRelease SET lucilleconfig=(
                SELECT pdr.lucilleconfig FROM DistroRelease AS pdr
                WHERE pdr.id = %s)
            WHERE id = %s
            ''' % sqlvalues(self.parentrelease.id, self.id))

    def _copy_binary_publishing_records(self, cur, arch, parent_arch):
        """Copy the binary publishing records from the parent arch release
        to the given arch release in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket.
        """
        cur.execute('''
            INSERT INTO SecureBinaryPackagePublishingHistory (
                binarypackagerelease, distroarchrelease, status,
                component, section, priority, datecreated, pocket, embargo)
            SELECT bpp.binarypackagerelease, %s as distroarchrelease,
                   bpp.status, bpp.component, bpp.section, bpp.priority,
                   %s as datecreated, %s as pocket, false as embargo
            FROM BinaryPackagePublishing AS bpp
            WHERE bpp.distroarchrelease = %s AND bpp.status in (%s, %s) AND
                  bpp.pocket = %s
            ''' % sqlvalues(arch.id, UTC_NOW,
                            PackagePublishingPocket.RELEASE.value,
                            parent_arch.id,
                            PackagePublishingStatus.PENDING.value,
                            PackagePublishingStatus.PUBLISHED.value,
                            PackagePublishingPocket.RELEASE.value))

    def _copy_source_publishing_records(self, cur):
        """Copy the source publishing records from our parent distro release.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket.
        """
        cur.execute('''
            INSERT INTO SecureSourcePackagePublishingHistory (
                sourcepackagerelease, distrorelease, status, component,
                section, datecreated, pocket, embargo)
            SELECT spp.sourcepackagerelease, %s as distrorelease,
                   spp.status, spp.component, spp.section, %s as datecreated,
                   %s as pocket, false as embargo
            FROM SourcePackagePublishing AS spp
            WHERE spp.distrorelease = %s AND spp.status in (%s, %s) AND
                  spp.pocket = %s
            ''' % sqlvalues(self.id, UTC_NOW,
                            PackagePublishingPocket.RELEASE.value,
                            self.parentrelease.id,
                            PackagePublishingStatus.PENDING.value,
                            PackagePublishingStatus.PUBLISHED.value,
                            PackagePublishingPocket.RELEASE.value))

    def _copy_component_and_section_selections(self, cur):
        """Copy the section and component selections from the parent distro
        release into this one.
        """
        # Copy the component selections
        cur.execute('''
            INSERT INTO ComponentSelection (distrorelease, component)
            SELECT %s AS distrorelease, cs.component AS component
            FROM ComponentSelection AS cs WHERE cs.distrorelease = %s
            ''' % sqlvalues(self.id, self.parentrelease.id))
        # Copy the section selections
        cur.execute('''
            INSERT INTO SectionSelection (distrorelease, section)
            SELECT %s as distrorelease, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distrorelease = %s
            ''' % sqlvalues(self.id, self.parentrelease.id))


class DistroReleaseSet:
    implements(IDistroReleaseSet)

    def get(self, distroreleaseid):
        """See IDistroReleaseSet."""
        return DistroRelease.get(distroreleaseid)

    def translatables(self):
        """See IDistroReleaseSet."""
        return DistroRelease.select(
            "POTemplate.distrorelease=DistroRelease.id",
            clauseTables=['POTemplate'], distinct=True)

    def findByName(self, name):
        """See IDistroReleaseSet."""
        return DistroRelease.selectBy(name=name)

    def queryByName(self, distribution, name):
        """See IDistroReleaseSet."""
        return DistroRelease.selectOneBy(
            distributionID=distribution.id, name=name)

    def findByVersion(self, version):
        """See IDistroReleaseSet."""
        return DistroRelease.selectBy(version=version)

    def search(self, distribution=None, isreleased=None, orderBy=None):
        """See IDistroReleaseSet."""
        where_clause = ""
        if distribution is not None:
            where_clause += "distribution = %s" % sqlvalues(distribution.id)
        if isreleased is not None:
            if where_clause:
                where_clause += " AND "
            if isreleased:
                # The query is filtered on released releases.
                where_clause += "releasestatus in (%s, %s)" % sqlvalues(
                    DistributionReleaseStatus.CURRENT,
                    DistributionReleaseStatus.SUPPORTED)
            else:
                # The query is filtered on unreleased releases.
                where_clause += "releasestatus in (%s, %s, %s)" % sqlvalues(
                    DistributionReleaseStatus.EXPERIMENTAL,
                    DistributionReleaseStatus.DEVELOPMENT,
                    DistributionReleaseStatus.FROZEN)
        if orderBy is not None:
            return DistroRelease.select(where_clause, orderBy=orderBy)
        else:
            return DistroRelease.select(where_clause)

    def new(self, distribution, name, displayname, title, summary, description,
            version, parentrelease, owner):
        """See IDistroReleaseSet."""
        return DistroRelease(
            distribution=distribution,
            name=name,
            displayname=displayname,
            title=title,
            summary=summary,
            description=description,
            version=version,
            releasestatus=DistributionReleaseStatus.EXPERIMENTAL,
            parentrelease=parentrelease,
            owner=owner)

