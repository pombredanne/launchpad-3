# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Classes to represent source packages in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackage',
    'DistributionSourcePackageInDatabase',
    ]

import itertools
import operator

from lazr.restful.utils import smartquote
from sqlobject.sqlbuilder import SQLConstant
from storm.expr import (
    And,
    Count,
    Desc,
    Max,
    Sum,
    )
from storm.locals import (
    Bool,
    Int,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.interfaces.bugsummary import IBugSummaryDimension
from lp.bugs.interfaces.bugtarget import IHasBugHeat
from lp.bugs.interfaces.bugtask import DB_UNRESOLVED_BUGTASK_STATUSES
from lp.bugs.model.bug import (
    Bug,
    BugSet,
    )
from lp.bugs.model.bugtarget import (
    BugTargetBase,
    HasBugHeatMixin,
    )
from lp.bugs.model.bugtask import BugTask
from lp.bugs.model.structuralsubscription import (
    StructuralSubscriptionTargetMixin,
    )
from lp.code.model.hasbranches import (
    HasBranchesMixin,
    HasMergeProposalsMixin,
    )
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.karma import KarmaTotalCache
from lp.registry.model.packaging import Packaging
from lp.registry.model.sourcepackage import (
    SourcePackage,
    SourcePackageQuestionTargetMixin,
    )
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease,
    )
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.translations.interfaces.customlanguagecode import (
    IHasCustomLanguageCodes,
    )
from lp.translations.model.customlanguagecode import (
    CustomLanguageCode,
    HasCustomLanguageCodesMixin,
    )


def is_upstream_link_allowed(spph):
    """Metapackages shouldn't have upstream links.

    Metapackages normally are in the 'misc' section.
    """
    if spph is None:
        return True
    return spph.section.name == 'misc'


class DistributionSourcePackageProperty:

    def __init__(self, attrname, default=None):
        self.attrname = attrname
        self.default = default

    def __get__(self, obj, class_):
        return getattr(obj._self_in_database, self.attrname, self.default)

    def __set__(self, obj, value):
        if obj._self_in_database is None:
            spph = Store.of(obj.distribution).find(
                SourcePackagePublishingHistory,
                SourcePackagePublishingHistory.distroseriesID ==
                    DistroSeries.id,
                DistroSeries.distributionID == obj.distribution.id,
                SourcePackagePublishingHistory.sourcepackagereleaseID ==
                    SourcePackageRelease.id,
                SourcePackageRelease.sourcepackagenameID ==
                    obj.sourcepackagename.id).order_by(
                        Desc(SourcePackagePublishingHistory.id)).first()
            obj._new(obj.distribution, obj.sourcepackagename,
                     is_upstream_link_allowed(spph))
        setattr(obj._self_in_database, self.attrname, value)


class DistributionSourcePackage(BugTargetBase,
                                SourcePackageQuestionTargetMixin,
                                StructuralSubscriptionTargetMixin,
                                HasBranchesMixin,
                                HasCustomLanguageCodesMixin,
                                HasMergeProposalsMixin,
                                HasBugHeatMixin):
    """This is a "Magic Distribution Source Package". It is not an
    SQLObject, but instead it represents a source package with a particular
    name in a particular distribution. You can then ask it all sorts of
    things about the releases that are published under its name, the latest
    or current release, etc.
    """

    implements(
        IBugSummaryDimension, IDistributionSourcePackage, IHasBugHeat,
        IHasCustomLanguageCodes)

    bug_reporting_guidelines = DistributionSourcePackageProperty(
        'bug_reporting_guidelines')
    bug_reported_acknowledgement = DistributionSourcePackageProperty(
        'bug_reported_acknowledgement')
    max_bug_heat = DistributionSourcePackageProperty('max_bug_heat')
    total_bug_heat = DistributionSourcePackageProperty('total_bug_heat')
    bug_count = DistributionSourcePackageProperty('bug_count')
    po_message_count = DistributionSourcePackageProperty('po_message_count')
    is_upstream_link_allowed = DistributionSourcePackageProperty(
        'is_upstream_link_allowed')
    enable_bugfiling_duplicate_search = DistributionSourcePackageProperty(
        'enable_bugfiling_duplicate_search', default=True)

    def __init__(self, distribution, sourcepackagename):
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename

    @property
    def name(self):
        """See `IDistributionSourcePackage`."""
        return self.sourcepackagename.name

    @property
    def displayname(self):
        """See `IDistributionSourcePackage`."""
        return '%s in %s' % (
            self.sourcepackagename.name, self.distribution.displayname)

    @property
    def bugtargetdisplayname(self):
        """See `IBugTarget`."""
        return "%s (%s)" % (self.name, self.distribution.displayname)

    @property
    def bugtargetname(self):
        """See `IBugTarget`."""
        return "%s (%s)" % (self.name, self.distribution.displayname)

    @property
    def title(self):
        """See `IDistributionSourcePackage`."""
        return smartquote('"%s" package in %s') % (
            self.sourcepackagename.name, self.distribution.displayname)

    @property
    def summary(self):
        """See `IDistributionSourcePackage`."""
        if self.development_version is None:
            return None
        return self.development_version.summary

    @property
    def development_version(self):
        """See `IDistributionSourcePackage`."""
        series = self.distribution.currentseries
        if series is None:
            return None
        return series.getSourcePackage(self.sourcepackagename)

    @property
    def _self_in_database(self):
        """Return the equivalent database-backed record of self."""
        # XXX: allenap 2008-11-13 bug=297736: This is a temporary
        # measure while DistributionSourcePackage is not yet hooked
        # into the database but we need access to some of the fields
        # in the database.
        return self._get(self.distribution, self.sourcepackagename)

    def delete(self):
        """See `DistributionSourcePackage`."""
        dsp_in_db = self._self_in_database
        no_spph = self.publishing_history.count() == 0
        if dsp_in_db is not None and no_spph:
            store = IStore(dsp_in_db)
            store.remove(dsp_in_db)
            return True
        return False

    def recalculateBugHeatCache(self):
        """See `IHasBugHeat`."""
        row = IStore(Bug).find(
            (Max(Bug.heat), Sum(Bug.heat), Count(Bug.id)),
            BugTask.bug == Bug.id,
            BugTask.distributionID == self.distribution.id,
            BugTask.sourcepackagenameID == self.sourcepackagename.id,
            Bug.duplicateof == None,
            # Change back to _status # DO NOT COMMIT
            BugTask._xstatus.is_in(DB_UNRESOLVED_BUGTASK_STATUSES)).one()

        # Aggregate functions return NULL if zero rows match.
        row = list(row)
        for i in range(len(row)):
            if row[i] is None:
                row[i] = 0

        self.max_bug_heat, self.total_bug_heat, self.bug_count = row

    @property
    def latest_overall_publication(self):
        """See `IDistributionSourcePackage`."""
        # XXX kiko 2008-06-03: This is magical code that finds the
        # latest relevant publication. It relies on ordering of status
        # and pocket enum values, which is arguably evil but much faster
        # than CASE sorting; at any rate this can be fixed when
        # https://bugs.launchpad.net/soyuz/+bug/236922 is.
        spph = SourcePackagePublishingHistory.selectFirst("""
            SourcePackagePublishingHistory.distroseries = DistroSeries.id AND
            DistroSeries.distribution = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            pocket NOT IN (%s, %s) AND
            status in (%s, %s)""" %
                sqlvalues(self.distribution,
                          self.sourcepackagename,
                          self.distribution.all_distro_archive_ids,
                          PackagePublishingPocket.PROPOSED,
                          PackagePublishingPocket.BACKPORTS,
                          PackagePublishingStatus.PUBLISHED,
                          PackagePublishingStatus.OBSOLETE),
            clauseTables=["SourcePackagePublishingHistory",
                          "SourcePackageRelease",
                          "DistroSeries"],
            orderBy=["status",
                     SQLConstant(
                        "to_number(DistroSeries.version, '99.99') DESC"),
                     "-pocket"])
        return spph

    def getVersion(self, version):
        """See `IDistributionSourcePackage`."""
        spph = SourcePackagePublishingHistory.select("""
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            DistroSeries.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.version = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagename,
                            version),
            orderBy='-datecreated',
            prejoinClauseTables=['SourcePackageRelease'],
            clauseTables=['DistroSeries', 'SourcePackageRelease'])
        if spph.count() == 0:
            return None
        return DistributionSourcePackageRelease(
            distribution=self.distribution,
            sourcepackagerelease=spph[0].sourcepackagerelease)

    # XXX kiko 2006-08-16: Bad method name, no need to be a property.
    @property
    def currentrelease(self):
        """See `IDistributionSourcePackage`."""
        releases = self.distribution.getCurrentSourceReleases(
            [self.sourcepackagename])
        return releases.get(self)

    def bugtasks(self, quantity=None):
        """See `IDistributionSourcePackage`."""
        return BugTask.select("""
            distribution=%s AND
            sourcepackagename=%s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagename.id),
            orderBy='-datecreated',
            limit=quantity)

    def get_distroseries_packages(self, active_only=True):
        """See `IDistributionSourcePackage`."""
        result = []
        for series in self.distribution.series:
            if active_only:
                if not series.active:
                    continue
            candidate = SourcePackage(self.sourcepackagename, series)
            if candidate.currentrelease is not None:
                result.append(candidate)
        return result

    def findRelatedArchives(self,
                            exclude_archive=None,
                            archive_purpose=ArchivePurpose.PPA,
                            required_karma=0):
        """See `IDistributionSourcePackage`."""

        extra_args = []

        # Exclude the specified archive where appropriate
        if exclude_archive is not None:
            extra_args.append(Archive.id != exclude_archive.id)

        # Filter by archive purpose where appropriate
        if archive_purpose is not None:
            extra_args.append(Archive.purpose == archive_purpose)

        # Include only those archives containing the source package released
        # by a person with karma for this source package greater than that
        # specified.
        if required_karma > 0:
            extra_args.append(KarmaTotalCache.karma_total >= required_karma)

        store = Store.of(self.distribution)
        results = store.find(
            Archive,
            Archive.distribution == self.distribution,
            Archive._enabled == True,
            Archive._private == False,
            SourcePackagePublishingHistory.archive == Archive.id,
            (SourcePackagePublishingHistory.status ==
                PackagePublishingStatus.PUBLISHED),
            (SourcePackagePublishingHistory.sourcepackagerelease ==
                SourcePackageRelease.id),
            SourcePackageRelease.sourcepackagename == self.sourcepackagename,
            # Ensure that the package was not copied.
            SourcePackageRelease.upload_archive == Archive.id,
            # Next, the joins for the ordering by soyuz karma of the
            # SPR creator.
            KarmaTotalCache.person == SourcePackageRelease.creatorID,
            *extra_args)

        # Note: If and when we later have a field on IArchive to order by,
        # such as IArchive.rank, we will then be able to return distinct
        # results. As it is, we cannot return distinct results while ordering
        # by a non-selected column.
        results.order_by(
            Desc(KarmaTotalCache.karma_total), Archive.id)

        return results

    @property
    def publishing_history(self):
        """See `IDistributionSourcePackage`."""
        return self._getPublishingHistoryQuery()

    @property
    def upstream_product(self):
        store = Store.of(self.sourcepackagename)
        condition = And(
            Packaging.sourcepackagename == self.sourcepackagename,
            Packaging.distroseriesID == DistroSeries.id,
            DistroSeries.distribution == self.distribution)
        result = store.find(Packaging, condition)
        result.order_by("debversion_sort_key(version) DESC")
        if result.count() == 0:
            return None
        else:
            return result[0].productseries.product

    # XXX kiko 2006-08-16: Bad method name, no need to be a property.
    @property
    def current_publishing_records(self):
        """See `IDistributionSourcePackage`."""
        status = PackagePublishingStatus.PUBLISHED
        return self._getPublishingHistoryQuery(status)

    def _getPublishingHistoryQuery(self, status=None):
        query = """
            DistroSeries.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagename)

        if status is not None:
            query += ("AND SourcePackagePublishingHistory.status = %s"
                      % sqlvalues(status))

        return SourcePackagePublishingHistory.select(query,
            clauseTables=['DistroSeries', 'SourcePackageRelease'],
            prejoinClauseTables=['SourcePackageRelease'],
            orderBy='-datecreated')

    def getReleasesAndPublishingHistory(self):
        """See `IDistributionSourcePackage`."""
        store = Store.of(self.distribution)
        result = store.find(
            (SourcePackageRelease, SourcePackagePublishingHistory),
            SourcePackagePublishingHistory.distroseries == DistroSeries.id,
            DistroSeries.distribution == self.distribution,
            SourcePackagePublishingHistory.archiveID.is_in(
               self.distribution.all_distro_archive_ids),
            SourcePackagePublishingHistory.sourcepackagerelease ==
                SourcePackageRelease.id,
            SourcePackageRelease.sourcepackagename == self.sourcepackagename)
        result.order_by(
            Desc(SourcePackageRelease.id),
            Desc(SourcePackagePublishingHistory.datecreated),
            Desc(SourcePackagePublishingHistory.id))

        # Collate the publishing history by SourcePackageRelease.
        dspr_pubs = []
        for spr, pubs in itertools.groupby(result, operator.itemgetter(0)):
            dspr_pubs.append(
                (DistributionSourcePackageRelease(
                        distribution=self.distribution,
                        sourcepackagerelease=spr),
                 [spph for (spr, spph) in pubs]))
        return dspr_pubs

    # XXX kiko 2006-08-16: Bad method name, no need to be a property.
    @property
    def releases(self):
        """See `IDistributionSourcePackage`."""
        return [dspr for (dspr, pubs) in
                self.getReleasesAndPublishingHistory()]

    def __eq__(self, other):
        """See `IDistributionSourcePackage`."""
        return (
            (IDistributionSourcePackage.providedBy(other)) and
            (self.distribution.id == other.distribution.id) and
            (self.sourcepackagename.id == other.sourcepackagename.id))

    def __hash__(self):
        """Return the combined hash of distribution and package name."""
        # Combine two hashes, in order to try to get the hash somewhat
        # unique (it doesn't have to be unique). Use ^ instead of +, to
        # avoid the hash from being larger than sys.maxint.
        return hash(self.distribution) ^ hash(self.sourcepackagename)

    def __ne__(self, other):
        """See `IDistributionSourcePackage`."""
        return not self.__eq__(other)

    def getBugSummaryContextWhereClause(self):
        """See `BugTargetBase`."""
        # Circular fail.
        from lp.bugs.model.bugsummary import BugSummary
        return And(
            BugSummary.distribution == self.distribution,
            BugSummary.sourcepackagename == self.sourcepackagename),

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this distribution source package."""
        search_params.setSourcePackage(self)

    def getUsedBugTags(self):
        """See `IBugTarget`."""
        return self.distribution.getUsedBugTags()

    def _getOfficialTagClause(self):
        return self.distribution._getOfficialTagClause()

    @property
    def official_bug_tags(self):
        """See `IHasBugs`."""
        return self.distribution.official_bug_tags

    def createBug(self, bug_params):
        """See `IBugTarget`."""
        bug_params.setBugTarget(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename)
        return BugSet().createBug(bug_params)

    def composeCustomLanguageCodeMatch(self):
        """See `HasCustomLanguageCodesMixin`."""
        return And(
            CustomLanguageCode.distribution == self.distribution,
            CustomLanguageCode.sourcepackagename == self.sourcepackagename)

    def createCustomLanguageCode(self, language_code, language):
        """See `IHasCustomLanguageCodes`."""
        return CustomLanguageCode(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            language_code=language_code, language=language)

    @classmethod
    def _get(cls, distribution, sourcepackagename):
        return Store.of(distribution).find(
            DistributionSourcePackageInDatabase,
            DistributionSourcePackageInDatabase.sourcepackagename ==
                sourcepackagename,
            DistributionSourcePackageInDatabase.distribution ==
                distribution).one()

    @classmethod
    def _new(cls, distribution, sourcepackagename,
             is_upstream_link_allowed=False):
        dsp = DistributionSourcePackageInDatabase()
        dsp.distribution = distribution
        dsp.sourcepackagename = sourcepackagename
        dsp.is_upstream_link_allowed = is_upstream_link_allowed
        Store.of(distribution).add(dsp)
        Store.of(distribution).flush()
        return dsp

    @classmethod
    def ensure(cls, spph=None, sourcepackage=None):
        """Create DistributionSourcePackage record, if necessary.

        Only create a record for primary archives (i.e. not for PPAs) or
        for official package branches. Requires either a SourcePackage
        or a SourcePackagePublishingHistory.

        :param spph: A SourcePackagePublishingHistory to create a DSP
            to represent an official uploaded/published package.
        :param sourcepackage: A SourcePackage to create a DSP to represent an
            official package branch.
        """
        if spph is None and sourcepackage is None:
            raise ValueError(
                'ensure() must be called with either a SPPH '
                'or a SourcePackage.')
        if spph is not None:
            if spph.archive.purpose != ArchivePurpose.PRIMARY:
                return
            distribution = spph.distroseries.distribution
            sourcepackagename = spph.sourcepackagerelease.sourcepackagename
        else:
            distribution = sourcepackage.distribution
            sourcepackagename = sourcepackage.sourcepackagename
        dsp = cls._get(distribution, sourcepackagename)
        if dsp is None:
            upstream_link_allowed = is_upstream_link_allowed(spph)
            cls._new(distribution, sourcepackagename, upstream_link_allowed)


class DistributionSourcePackageInDatabase(Storm):
    """Temporary class to allow access to the database."""

    # XXX: allenap 2008-11-13 bug=297736: This is a temporary measure
    # while DistributionSourcePackage is not yet hooked into the
    # database but we need access to some of the fields in the
    # database.

    __storm_table__ = 'DistributionSourcePackage'

    id = Int(primary=True)

    distribution_id = Int(name='distribution')
    distribution = Reference(
        distribution_id, 'Distribution.id')

    sourcepackagename_id = Int(name='sourcepackagename')
    sourcepackagename = Reference(
        sourcepackagename_id, 'SourcePackageName.id')

    bug_reporting_guidelines = Unicode()
    bug_reported_acknowledgement = Unicode()

    max_bug_heat = Int()
    total_bug_heat = Int()
    bug_count = Int()
    po_message_count = Int()
    is_upstream_link_allowed = Bool()
    enable_bugfiling_duplicate_search = Bool()

    @property
    def currentrelease(self):
        """See `IDistributionSourcePackage`."""
        releases = self.distribution.getCurrentSourceReleases(
            [self.sourcepackagename])
        return releases.get(self)
