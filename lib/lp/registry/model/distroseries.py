# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Database classes for a distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeries',
    'DistroSeriesSet',
    ]

import collections
from cStringIO import StringIO
import logging
from operator import attrgetter

import apt_pkg
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLMultipleJoin,
    SQLObjectNotFound,
    SQLRelatedJoin,
    StringCol,
    )
from storm.locals import (
    And,
    Desc,
    Join,
    SQL,
    )
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    flush_database_caches,
    flush_database_updates,
    quote,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    SLAVE_FLAVOR,
    )
from lp.app.enums import service_uses_launchpad
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import IServiceUsage
from lp.blueprints.enums import (
    SpecificationFilter,
    SpecificationGoalStatus,
    SpecificationImplementationStatus,
    SpecificationSort,
    )
from lp.blueprints.model.specification import (
    HasSpecificationsMixin,
    Specification,
    )
from lp.bugs.interfaces.bugsummary import IBugSummaryDimension
from lp.bugs.interfaces.bugtarget import (
    IHasBugHeat,
    ISeriesBugTarget,
    )
from lp.bugs.interfaces.bugtaskfilter import OrderedBugTask
from lp.bugs.model.bug import get_bug_tags
from lp.bugs.model.bugtarget import (
    BugTargetBase,
    HasBugHeatMixin,
    )
from lp.bugs.model.structuralsubscription import (
    StructuralSubscriptionTargetMixin,
    )
from lp.registry.interfaces.distroseries import (
    DerivationError,
    IDistroSeries,
    IDistroSeriesSet,
    )
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceCommentSource,
    )
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import (
    ISourcePackage,
    ISourcePackageFactory,
    )
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageName,
    ISourcePackageNameSet,
    )
from lp.registry.model.milestone import (
    HasMilestonesMixin,
    Milestone,
    )
from lp.registry.model.packaging import Packaging
from lp.registry.model.person import Person
from lp.registry.model.series import SeriesMixin
from lp.registry.model.sourcepackage import SourcePackage
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.mail.signedmessage import signed_message_from_string
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.worlddata.model.language import Language
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import ALLOW_RELEASE_BUILDS
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageName
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.distributionjob import (
    IInitializeDistroSeriesJobSource,
    )
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    ICanPublishPackages,
    )
from lp.soyuz.interfaces.queue import (
    IHasQueueItems,
    IPackageUploadSet,
    )
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.component import Component
from lp.soyuz.model.distroarchseries import (
    DistroArchSeries,
    DistroArchSeriesSet,
    PocketChroot,
    )
from lp.soyuz.model.distroseriesbinarypackage import DistroSeriesBinaryPackage
from lp.soyuz.model.distroseriespackagecache import DistroSeriesPackageCache
from lp.soyuz.model.distroseriessourcepackagerelease import (
    DistroSeriesSourcePackageRelease,
    )
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.soyuz.model.queue import (
    PackageUpload,
    PackageUploadQueue,
    )
from lp.soyuz.model.section import Section
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.soyuz.scripts.initialize_distroseries import (
    InitializationError,
    InitializeDistroSeries,
    )
from lp.translations.enums import LanguagePackType
from lp.translations.model.distroseries_translations_copy import (
    copy_active_translations,
    )
from lp.translations.model.distroserieslanguage import (
    DistroSeriesLanguage,
    DummyDistroSeriesLanguage,
    )
from lp.translations.model.hastranslationimports import (
    HasTranslationImportsMixin,
    )
from lp.translations.model.hastranslationtemplates import (
    HasTranslationTemplatesMixin,
    )
from lp.translations.model.languagepack import LanguagePack
from lp.translations.model.pofile import POFile
from lp.translations.model.pofiletranslator import POFileTranslator
from lp.translations.model.potemplate import (
    POTemplate,
    TranslationTemplatesCollection,
    )


class DistroSeries(SQLBase, BugTargetBase, HasSpecificationsMixin,
                   HasTranslationImportsMixin, HasTranslationTemplatesMixin,
                   HasMilestonesMixin, SeriesMixin,
                   StructuralSubscriptionTargetMixin, HasBugHeatMixin):
    """A particular series of a distribution."""
    implements(
        ICanPublishPackages, IBugSummaryDimension, IDistroSeries, IHasBugHeat,
        IHasBuildRecords, IHasQueueItems, IServiceUsage, ISeriesBugTarget)

    _table = 'DistroSeries'
    _defaultOrder = ['distribution', 'version']

    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=True)
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    status = EnumCol(
        dbName='releasestatus', notNull=True, schema=SeriesStatus)
    date_created = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    datereleased = UtcDateTimeCol(notNull=False, default=None)
    previous_series = ForeignKey(
        dbName='parent_series', foreignKey='DistroSeries', notNull=False)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    driver = ForeignKey(
        dbName="driver", foreignKey="Person",
        storm_validator=validate_public_person, notNull=False, default=None)
    changeslist = StringCol(notNull=False, default=None)
    nominatedarchindep = ForeignKey(
        dbName='nominatedarchindep', foreignKey='DistroArchSeries',
        notNull=False, default=None)
    messagecount = IntCol(notNull=True, default=0)
    binarycount = IntCol(notNull=True, default=DEFAULT)
    sourcecount = IntCol(notNull=True, default=DEFAULT)
    defer_translation_imports = BoolCol(notNull=True, default=True)
    hide_all_translations = BoolCol(notNull=True, default=True)
    language_pack_base = ForeignKey(
        foreignKey="LanguagePack", dbName="language_pack_base", notNull=False,
        default=None)
    language_pack_delta = ForeignKey(
        foreignKey="LanguagePack", dbName="language_pack_delta",
        notNull=False, default=None)
    language_pack_proposed = ForeignKey(
        foreignKey="LanguagePack", dbName="language_pack_proposed",
        notNull=False, default=None)
    language_pack_full_export_requested = BoolCol(notNull=True, default=False)
    backports_not_automatic = BoolCol(notNull=True, default=False)
    include_long_descriptions = BoolCol(notNull=True, default=True)

    language_packs = SQLMultipleJoin(
        'LanguagePack', joinColumn='distroseries', orderBy='-date_exported')
    sections = SQLRelatedJoin(
        'Section', joinColumn='distroseries', otherColumn='section',
        intermediateTable='SectionSelection')

    @property
    def pillar(self):
        """See `IBugTarget`."""
        return self.distribution

    @property
    def named_version(self):
        return '%s (%s)' % (self.displayname, self.version)

    @property
    def upload_components(self):
        """See `IDistroSeries`."""
        return Component.select("""
            ComponentSelection.distroseries = %s AND
            Component.id = ComponentSelection.component
            """ % self.id,
            clauseTables=["ComponentSelection"])

    @cachedproperty
    def components(self):
        """See `IDistroSeries`."""
        # XXX julian 2007-06-25
        # This is filtering out the partner component for now, until
        # the second stage of the partner repo arrives in 1.1.8.
        return list(Component.select("""
            ComponentSelection.distroseries = %s AND
            Component.id = ComponentSelection.component AND
            Component.name != 'partner'
            """ % self.id,
            clauseTables=["ComponentSelection"]))

    @cachedproperty
    def component_names(self):
        """See `IDistroSeries`."""
        return [component.name for component in self.components]

    @cachedproperty
    def suite_names(self):
        """See `IDistroSeries`."""
        return [unicode(pocket) for pocket in PackagePublishingPocket.items]

    @property
    def answers_usage(self):
        """See `IServiceUsage.`"""
        return self.distribution.answers_usage

    @property
    def blueprints_usage(self):
        """See `IServiceUsage.`"""
        return self.distribution.blueprints_usage

    @property
    def translations_usage(self):
        """See `IServiceUsage.`"""
        return self.distribution.translations_usage

    @property
    def codehosting_usage(self):
        """See `IServiceUsage.`"""
        return self.distribution.codehosting_usage

    @property
    def bug_tracking_usage(self):
        """See `IServiceUsage.`"""
        return self.distribution.bug_tracking_usage

    @property
    def uses_launchpad(self):
        """ See `IServiceUsage.`"""
        return (
            service_uses_launchpad(self.blueprints_usage) or
            service_uses_launchpad(self.translations_usage) or
            service_uses_launchpad(self.answers_usage) or
            service_uses_launchpad(self.codehosting_usage) or
            service_uses_launchpad(self.bug_tracking_usage))

    # DistroArchSeries lookup properties/methods.
    architectures = SQLMultipleJoin(
        'DistroArchSeries', joinColumn='distroseries',
        orderBy='architecturetag')

    def __getitem__(self, archtag):
        """See `IDistroSeries`."""
        return self.getDistroArchSeries(archtag)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)

    def __str__(self):
        return '%s %s' % (self.distribution.name, self.name)

    def getDistroArchSeries(self, archtag):
        """See `IDistroSeries`."""
        item = DistroArchSeries.selectOneBy(
            distroseries=self, architecturetag=archtag)
        if item is None:
            raise NotFoundError('Unknown architecture %s for %s %s' % (
                archtag, self.distribution.name, self.name))
        return item

    def getDistroArchSeriesByProcessor(self, processor):
        """See `IDistroSeries`."""
        # XXX: JRV 2010-01-14: This should ideally use storm to find the
        # distroarchseries rather than iterating over all of them, but
        # I couldn't figure out how to do that - and a trivial for loop
        # isn't expensive given there's generally less than a dozen
        # architectures.
        for architecture in self.architectures:
            if architecture.processorfamily == processor.family:
                return architecture
        return None

    @property
    def enabled_architectures(self):
        store = Store.of(self)
        results = store.find(
            DistroArchSeries,
            DistroArchSeries.distroseries == self,
            DistroArchSeries.enabled == True)
        return results.order_by(DistroArchSeries.architecturetag)

    @property
    def buildable_architectures(self):
        store = Store.of(self)
        origin = [
            DistroArchSeries,
            Join(PocketChroot,
                 PocketChroot.distroarchseries == DistroArchSeries.id),
            Join(LibraryFileAlias,
                 PocketChroot.chroot == LibraryFileAlias.id),
            ]
        results = store.using(*origin).find(
            DistroArchSeries,
            DistroArchSeries.distroseries == self)
        return results.order_by(DistroArchSeries.architecturetag)

    @property
    def virtualized_architectures(self):
        store = Store.of(self)
        results = store.find(
            DistroArchSeries,
            DistroArchSeries.distroseries == self,
            DistroArchSeries.supports_virtualized == True)
        return results.order_by(DistroArchSeries.architecturetag)
    # End of DistroArchSeries lookup methods

    @property
    def parent(self):
        """See `IDistroSeries`."""
        return self.distribution

    @property
    def owner(self):
        """See `IDistroSeries`."""
        return self.distribution.owner

    @property
    def sortkey(self):
        """A string to be used for sorting distro seriess.

        This is designed to sort alphabetically by distro and series name,
        except that Ubuntu will be at the top of the listing.
        """
        result = ''
        if self.distribution.name == 'ubuntu':
            result += '-'
        result += self.distribution.name + self.name
        return result

    @cachedproperty
    def _all_packagings(self):
        """Get an unordered list of all packagings.

        :return: A ResultSet which can be decorated or tuned further. Use
            DistroSeries._packaging_row_to_packaging to extract the
            packaging objects out.
        """
        # We join to SourcePackageName, ProductSeries, and Product to cache
        # the objects that are implicitly needed to work with a
        # Packaging object.
        # NB: precaching objects like this method tries to do has a very poor
        # hit rate with storm - many queries will still be executed; consider
        # ripping this out and instead allowing explicit inclusion of things
        # like Person._members does - returning a cached object graph.
        # -- RBC 20100810
        # Avoid circular import failures.
        from lp.registry.model.product import Product
        from lp.registry.model.productseries import ProductSeries
        find_spec = (Packaging, SourcePackageName, ProductSeries, Product)
        origin = [
            Packaging,
            Join(
                SourcePackageName,
                Packaging.sourcepackagename == SourcePackageName.id),
            Join(
                ProductSeries,
                Packaging.productseries == ProductSeries.id),
            Join(
                Product,
                ProductSeries.product == Product.id)]
        condition = Packaging.distroseries == self.id
        results = IStore(self).using(*origin).find(find_spec, condition)
        return results

    @staticmethod
    def _packaging_row_to_packaging(row):
        # each row has:
        #  (packaging, spn, product_series, product)
        return row[0]

    @property
    def packagings(self):
        """See `IDistroSeries`."""
        results = self._all_packagings
        results = results.order_by(SourcePackageName.name)
        return DecoratedResultSet(results,
            DistroSeries._packaging_row_to_packaging)

    def getPrioritizedUnlinkedSourcePackages(self):
        """See `IDistroSeries`.

        The prioritization is a heuristic rule using bug heat,
        translatable messages, and the source package release's component.
        """
        find_spec = (
            SourcePackageName,
            SQL("""
                coalesce(total_bug_heat, 0) + coalesce(po_messages, 0) +
                CASE WHEN component = 1 THEN 1000 ELSE 0 END AS score"""),
            SQL("coalesce(bug_count, 0) AS bug_count"),
            SQL("coalesce(total_messages, 0) AS total_messages"))
        # This does not use _current_sourcepackage_joins_and_conditions
        # because the two queries are working on different data sets -
        # +needs-packaging was timing out and +packaging wasn't, and
        # destabilising things unnecessarily is not good.
        origin = SQL("""
            SourcePackageName, (SELECT
        spr.sourcepackagename,
        spr.component,
        bug_count,
        total_bug_heat,
        SUM(POTemplate.messagecount) * %(po_message_weight)s AS po_messages,
        SUM(POTemplate.messagecount) AS total_messages
    FROM
        SourcePackageRelease AS spr
        JOIN SourcePackagePublishingHistory AS spph
            ON spr.id = spph.sourcepackagerelease
        JOIN Archive
            ON spph.archive = Archive.id
        JOIN Section
            ON spph.section = Section.id
        JOIN DistroSeries
            ON spph.distroseries = DistroSeries.id
        LEFT OUTER JOIN DistributionSourcePackage AS dsp
            ON dsp.sourcepackagename = spr.sourcepackagename
                AND dsp.distribution = DistroSeries.distribution
        LEFT OUTER JOIN POTemplate
            ON POTemplate.sourcepackagename = spr.sourcepackagename
                AND POTemplate.distroseries = DistroSeries.id
    WHERE
        DistroSeries.id = %(distroseries)s
        AND spph.status IN %(active_status)s
        AND Archive.purpose = %(primary)s
        AND Section.name <> 'translations'
        AND NOT EXISTS (
            SELECT TRUE FROM Packaging
            WHERE
                Packaging.sourcepackagename = spr.sourcepackagename
                AND Packaging.distroseries = spph.distroseries)
    GROUP BY
        spr.sourcepackagename, spr.component, bug_count, total_bug_heat
    ) AS spn_info""" % sqlvalues(
            po_message_weight=self._current_sourcepackage_po_weight,
            distroseries=self,
            active_status=active_publishing_status,
            primary=ArchivePurpose.PRIMARY))
        condition = SQL("sourcepackagename.id = spn_info.sourcepackagename")
        results = IStore(self).using(origin).find(find_spec, condition)
        results = results.order_by('score DESC', SourcePackageName.name)
        results = results.config(distinct=('score', SourcePackageName.name))

        def decorator(row):
            spn, score, bug_count, total_messages = row
            return {
                'package': SourcePackage(
                    sourcepackagename=spn, distroseries=self),
                'bug_count': bug_count,
                'total_messages': total_messages,
                }
        return DecoratedResultSet(results, decorator)

    def getPrioritizedPackagings(self):
        """See `IDistroSeries`.

        The prioritization is a heuristic rule using the branch, bug heat,
        translatable messages, and the source package release's component.
        """
        # We join to SourcePackageName, ProductSeries, and Product to cache
        # the objects that are implcitly needed to work with a
        # Packaging object.
        joins, conditions = self._current_sourcepackage_joins_and_conditions
        # XXX: EdwinGrubbs 2010-07-29 bug=374777
        # Storm doesn't support DISTINCT ON.
        origin = SQL('''
            (
            SELECT DISTINCT ON (Packaging.id)
                Packaging.*,
                spr.component AS spr_component,
                SourcePackageName.name AS spn_name,
                total_bug_heat,
                po_messages
            FROM %(joins)s
            WHERE %(conditions)s
                AND packaging.id IS NOT NULL
            ) AS Packaging
            JOIN ProductSeries
                ON Packaging.productseries = ProductSeries.id
            JOIN Product
                ON ProductSeries.product = Product.id
            ''' % dict(joins=joins, conditions=conditions))
        return IStore(self).using(origin).find(Packaging).order_by('''
                (CASE WHEN spr_component = 1 THEN 1000 ELSE 0 END
                + CASE WHEN Product.bugtracker IS NULL
                    THEN coalesce(total_bug_heat, 10) ELSE 0 END
                + CASE WHEN ProductSeries.translations_autoimport_mode = 1
                    THEN coalesce(po_messages, 10) ELSE 0 END
                + CASE WHEN ProductSeries.branch IS NULL THEN 500 ELSE 0 END
                ) DESC,
                spn_name ASC
                ''')

    @property
    def _current_sourcepackage_po_weight(self):
        """See getPrioritized*."""
        # Bugs and PO messages are heuristically scored. These queries
        # can easily timeout so filters and weights are used to create
        # an acceptable prioritization of packages that is fast to excecute.
        return .5

    @property
    def _current_sourcepackage_joins_and_conditions(self):
        """The SQL joins and conditions to prioritize source packages.

        Used for getPrioritizedPackagings only.
        """
        # Bugs and PO messages are heuristically scored. These queries
        # can easily timeout so filters and weights are used to create
        # an acceptable prioritization of packages that is fast to excecute.
        po_message_weight = self._current_sourcepackage_po_weight
        message_score = ("""
            LEFT JOIN (
                SELECT
                    POTemplate.sourcepackagename,
                    POTemplate.distroseries,
                    SUM(POTemplate.messagecount) * %(po_message_weight)s
                        AS po_messages,
                    SUM(POTemplate.messagecount) AS total_messages
                FROM POTemplate
                WHERE
                    POTemplate.sourcepackagename is not NULL
                    AND POTemplate.distroseries = %(distroseries)s
                GROUP BY
                    POTemplate.sourcepackagename,
                    POTemplate.distroseries
                ) messages
                ON SourcePackageName.id = messages.sourcepackagename
                AND DistroSeries.id = messages.distroseries
            """ % sqlvalues(
                distroseries=self,
                po_message_weight=po_message_weight))
        joins = ("""
            SourcePackageName
            JOIN SourcePackageRelease spr
                ON SourcePackageName.id = spr.sourcepackagename
            JOIN SourcePackagePublishingHistory spph
                ON spr.id = spph.sourcepackagerelease
            JOIN archive
                ON spph.archive = Archive.id
            JOIN section
                ON spph.section = section.id
            JOIN DistroSeries
                ON spph.distroseries = DistroSeries.id
            LEFT JOIN Packaging
                ON SourcePackageName.id = Packaging.sourcepackagename
                AND Packaging.distroseries = DistroSeries.id
            LEFT JOIN DistributionSourcePackage dsp
                ON dsp.sourcepackagename = spr.sourcepackagename
                    AND dsp.distribution = DistroSeries.distribution
            """ + message_score)
        conditions = ("""
            DistroSeries.id = %(distroseries)s
            AND spph.status IN %(active_status)s
            AND archive.purpose = %(primary)s
            AND section.name != 'translations'
            """ % sqlvalues(
                distroseries=self,
                active_status=active_publishing_status,
                primary=ArchivePurpose.PRIMARY))
        return (joins, conditions)

    def getMostRecentlyLinkedPackagings(self):
        """See `IDistroSeries`."""
        results = self._all_packagings
        # Order by creation date with a secondary ordering by sourcepackage
        # name to ensure the ordering for test data where many packagings have
        # identical creation dates.
        results = results.order_by(Desc(Packaging.datecreated),
                                   SourcePackageName.name)[:5]
        return DecoratedResultSet(results,
            DistroSeries._packaging_row_to_packaging)

    @property
    def supported(self):
        return self.status in [
            SeriesStatus.CURRENT,
            SeriesStatus.SUPPORTED,
            ]

    @property
    def distroserieslanguages(self):
        result = DistroSeriesLanguage.select(
            "DistroSeriesLanguage.language = Language.id AND "
            "DistroSeriesLanguage.distroseries = %d AND "
            "Language.visible = TRUE" % self.id,
            prejoinClauseTables=["Language"],
            clauseTables=["Language"],
            prejoins=["distroseries"],
            orderBy=["Language.englishname"])
        return result

    def priorReleasedSeries(self):
        """See `IDistroSeries`."""
        datereleased = self.datereleased
        # if this one is unreleased, use the last released one
        if not datereleased:
            datereleased = UTC_NOW
        return getUtility(IDistroSeriesSet).priorReleasedSeries(
            self.distribution, datereleased)

    @property
    def bug_reporting_guidelines(self):
        """See `IBugTarget`."""
        return self.distribution.bug_reporting_guidelines

    @property
    def bug_reported_acknowledgement(self):
        """See `IBugTarget`."""
        return self.distribution.bug_reported_acknowledgement

    def _getMilestoneCondition(self):
        """See `HasMilestonesMixin`."""
        return (Milestone.distroseries == self)

    def canUploadToPocket(self, pocket):
        """See `IDistroSeries`."""
        # Allow everything for distroseries in FROZEN state.
        if self.status == SeriesStatus.FROZEN:
            return True

        # Define stable/released states.
        stable_states = (SeriesStatus.SUPPORTED,
                         SeriesStatus.CURRENT)

        # Deny uploads for RELEASE pocket in stable states.
        if (pocket == PackagePublishingPocket.RELEASE and
            self.status in stable_states):
            return False

        # Deny uploads for post-release pockets in unstable states.
        if (pocket != PackagePublishingPocket.RELEASE and
            self.status not in stable_states):
            return False

        # Allow anything else.
        return True

    def updatePackageCount(self):
        """See `IDistroSeries`."""

        # first update the source package count
        query = """
            SourcePackagePublishingHistory.distroseries = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.status IN %s AND
            SourcePackagePublishingHistory.pocket = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(
                    self,
                    self.distribution.all_distro_archive_ids,
                    active_publishing_status,
                    PackagePublishingPocket.RELEASE)
        self.sourcecount = SourcePackageName.select(
            query, distinct=True,
            clauseTables=['SourcePackageRelease',
                          'SourcePackagePublishingHistory']).count()

        # next update the binary count
        clauseTables = ['DistroArchSeries', 'BinaryPackagePublishingHistory',
                        'BinaryPackageRelease']
        query = """
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status IN %s AND
            BinaryPackagePublishingHistory.pocket = %s AND
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = %s AND
            BinaryPackagePublishingHistory.archive IN %s
            """ % sqlvalues(
                    active_publishing_status,
                    PackagePublishingPocket.RELEASE,
                    self,
                    self.distribution.all_distro_archive_ids)
        ret = BinaryPackageName.select(
            query, distinct=True, clauseTables=clauseTables).count()
        self.binarycount = ret

    @property
    def architecturecount(self):
        """See `IDistroSeries`."""
        return self.architectures.count()

    @property
    def fullseriesname(self):
        return "%s %s" % (
            self.distribution.name.capitalize(), self.name.capitalize())

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        # XXX mpt 2007-07-10 bugs 113258, 113262:
        # The distribution's and series' names should be used instead
        # of fullseriesname.
        return self.fullseriesname

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.fullseriesname

    @property
    def bugtarget_parent(self):
        """See `ISeriesBugTarget`."""
        return self.parent

    @property
    def max_bug_heat(self):
        """See `IHasBugs`."""
        return self.distribution.max_bug_heat

    @property
    def last_full_language_pack_exported(self):
        return LanguagePack.selectFirstBy(
            distroseries=self, type=LanguagePackType.FULL,
            orderBy='-date_exported')

    @property
    def last_delta_language_pack_exported(self):
        return LanguagePack.selectFirstBy(
            distroseries=self, type=LanguagePackType.DELTA,
            updates=self.language_pack_base, orderBy='-date_exported')

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this distribution series."""
        search_params.setDistroSeries(self)

    def _getOfficialTagClause(self):
        return self.distribution._getOfficialTagClause()

    @property
    def official_bug_tags(self):
        """See `IHasBugs`."""
        return self.distribution.official_bug_tags

    def getUsedBugTags(self):
        """See `IHasBugs`."""
        return get_bug_tags("BugTask.distroseries = %s" % sqlvalues(self))

    @property
    def has_any_specifications(self):
        """See IHasSpecifications."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See IHasSpecifications.

        In this case the rules for the default behaviour cover three things:

          - acceptance: if nothing is said, ACCEPTED only
          - completeness: if nothing is said, ANY
          - informationalness: if nothing is said, ANY

        """

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a distroseries is to show everything approved
            filter = [SpecificationFilter.ACCEPTED]

        # defaults for completeness: in this case we don't actually need to
        # do anything, because the default is ANY

        # defaults for acceptance: in this case, if nothing is said about
        # acceptance, we want to show only accepted specs
        acceptance = False
        for option in [
            SpecificationFilter.ACCEPTED,
            SpecificationFilter.DECLINED,
            SpecificationFilter.PROPOSED]:
            if option in filter:
                acceptance = True
        if acceptance is False:
            filter.append(SpecificationFilter.ACCEPTED)

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'Specification.definition_status',
                     'Specification.name']
        elif sort == SpecificationSort.DATE:
            # we are showing specs for a GOAL, so under some circumstances
            # we care about the order in which the specs were nominated for
            # the goal, and in others we care about the order in which the
            # decision was made.

            # we need to establish if the listing will show specs that have
            # been decided only, or will include proposed specs.
            show_proposed = set([
                SpecificationFilter.ALL,
                SpecificationFilter.PROPOSED,
                ])
            if len(show_proposed.intersection(set(filter))) > 0:
                # we are showing proposed specs so use the date proposed
                # because not all specs will have a date decided.
                order = ['-Specification.datecreated', 'Specification.id']
            else:
                # this will show only decided specs so use the date the spec
                # was accepted or declined for the sprint
                order = ['-Specification.date_goal_decided',
                         '-Specification.datecreated',
                         'Specification.id']

        # figure out what set of specifications we are interested in. for
        # distroseries, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - goal status.
        #  - informational.
        #
        base = 'Specification.distroseries = %s' % self.id
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s' %
              quote(SpecificationImplementationStatus.INFORMATIONAL))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness = Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # look for specs that have a particular goalstatus (proposed,
        # accepted or declined)
        if SpecificationFilter.ACCEPTED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.ACCEPTED.value)
        elif SpecificationFilter.PROPOSED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.PROPOSED.value)
        elif SpecificationFilter.DECLINED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.DECLINED.value)

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        results = Specification.select(query, orderBy=order, limit=quantity)
        if prejoin_people:
            results = results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return self.distribution.getSpecification(name)

    def getDistroSeriesLanguage(self, language):
        """See `IDistroSeries`."""
        return DistroSeriesLanguage.selectOneBy(
            distroseries=self, language=language)

    def getDistroSeriesLanguageOrDummy(self, language):
        """See `IDistroSeries`."""
        drl = self.getDistroSeriesLanguage(language)
        if drl is not None:
            return drl
        return DummyDistroSeriesLanguage(self, language)

    def updateStatistics(self, ztm):
        """See `IDistroSeries`."""
        # first find the set of all languages for which we have pofiles in
        # the distribution that are visible and not English
        langidset = set(IStore(Language).find(
            Language.id,
            Language.visible == True,
            Language.id == POFile.languageID,
            Language.code != 'en',
            POFile.potemplateID == POTemplate.id,
            POTemplate.distroseries == self,
            POTemplate.iscurrent == True).config(distinct=True))

        # now run through the existing DistroSeriesLanguages for the
        # distroseries, and update their stats, and remove them from the
        # list of languages we need to have stats for
        for distroserieslanguage in self.distroserieslanguages:
            distroserieslanguage.updateStatistics(ztm)
            langidset.discard(distroserieslanguage.language.id)
        # now we should have a set of languages for which we NEED
        # to have a DistroSeriesLanguage
        for langid in langidset:
            drl = DistroSeriesLanguage(distroseries=self, languageID=langid)
            drl.updateStatistics(ztm)
        # lastly, we need to update the message count for this distro
        # series itself
        messagecount = 0
        for potemplate in self.getCurrentTranslationTemplates():
            messagecount += potemplate.messageCount()
        self.messagecount = messagecount
        ztm.commit()

    def getSourcePackage(self, name):
        """See `IDistroSeries`."""
        if not ISourcePackageName.providedBy(name):
            try:
                name = SourcePackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return getUtility(ISourcePackageFactory).new(
            sourcepackagename=name, distroseries=self)

    def getBinaryPackage(self, name):
        """See `IDistroSeries`."""
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroSeriesBinaryPackage(self, name)

    def getSourcePackageRelease(self, sourcepackagerelease):
        """See `IDistroSeries`."""
        return DistroSeriesSourcePackageRelease(self, sourcepackagerelease)

    def getCurrentSourceReleases(self, source_package_names):
        """See `IDistroSeries`."""
        return getUtility(IDistroSeriesSet).getCurrentSourceReleases(
            {self: source_package_names})

    def getTranslatableSourcePackages(self):
        """See `IDistroSeries`."""
        query = """
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.iscurrent = TRUE AND
            POTemplate.distroseries = %s""" % sqlvalues(self.id)
        result = SourcePackageName.select(query, clauseTables=['POTemplate'],
            orderBy=['name'], distinct=True)
        return [SourcePackage(sourcepackagename=spn, distroseries=self) for
            spn in result]

    def getUnlinkedTranslatableSourcePackages(self):
        """See `IDistroSeries`."""
        # Note that both unlinked packages and
        # linked-with-no-productseries packages are considered to be
        # "unlinked translatables".
        query = """
            SourcePackageName.id NOT IN (SELECT DISTINCT
             sourcepackagename FROM Packaging WHERE distroseries = %s) AND
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distroseries = %s""" % sqlvalues(self.id, self.id)
        unlinked = SourcePackageName.select(
            query, clauseTables=['POTemplate'], orderBy=['name'])
        query = """
            Packaging.sourcepackagename = SourcePackageName.id AND
            Packaging.productseries = NULL AND
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distroseries = %s""" % sqlvalues(self.id)
        linked_but_no_productseries = SourcePackageName.select(
            query, clauseTables=['POTemplate', 'Packaging'], orderBy=['name'])
        result = unlinked.union(linked_but_no_productseries)
        return [SourcePackage(sourcepackagename=spn, distroseries=self) for
            spn in result]

    def getPublishedSources(self, sourcepackage_or_name, version=None,
                             pocket=None, include_pending=False,
                             exclude_pocket=None, archive=None):
        """See `IDistroSeries`."""
        # Deprecated.  Use IArchive.getPublishedSources instead.

        # XXX cprov 2006-02-13 bug 31317:
        # We need a standard and easy API, no need
        # to support multiple type arguments, only string name should be
        # the best choice in here, the call site will be clearer.
        if ISourcePackage.providedBy(sourcepackage_or_name):
            spn = sourcepackage_or_name.name
        elif ISourcePackageName.providedBy(sourcepackage_or_name):
            spn = sourcepackage_or_name
        else:
            spns = getUtility(ISourcePackageNameSet)
            spn = spns.queryByName(sourcepackage_or_name)
            if spn is None:
                return EmptyResultSet()

        queries = ["""
        sourcepackagerelease=sourcepackagerelease.id AND
        sourcepackagerelease.sourcepackagename=%s AND
        distroseries=%s
        """ % sqlvalues(spn.id, self.id)]

        if pocket is not None:
            queries.append("pocket=%s" % sqlvalues(pocket.value))

        if version is not None:
            queries.append("version=%s" % sqlvalues(version))

        if exclude_pocket is not None:
            queries.append("pocket!=%s" % sqlvalues(exclude_pocket.value))

        if include_pending:
            queries.append("status in (%s, %s)" % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING))
        else:
            queries.append("status=%s" % sqlvalues(
                PackagePublishingStatus.PUBLISHED))

        archives = self.distribution.getArchiveIDList(archive)
        queries.append("archive IN %s" % sqlvalues(archives))

        published = SourcePackagePublishingHistory.select(
            " AND ".join(queries), clauseTables=['SourcePackageRelease'],
            orderBy=['-id'])

        return published

    def isUnstable(self):
        """See `IDistroSeries`."""
        return self.status in [
            SeriesStatus.FROZEN,
            SeriesStatus.DEVELOPMENT,
            SeriesStatus.EXPERIMENTAL,
        ]

    def _getAllSources(self):
        """Get all sources ever published in this series' main archives."""
        return IStore(SourcePackagePublishingHistory).find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.distroseriesID == self.id,
            SourcePackagePublishingHistory.archiveID.is_in(
                self.distribution.all_distro_archive_ids),
            ).order_by(SourcePackagePublishingHistory.id)

    def _getAllBinaries(self):
        """Get all binaries ever published in this series' main archives."""
        return IStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            DistroArchSeries.distroseriesID == self.id,
            BinaryPackagePublishingHistory.distroarchseriesID
                == DistroArchSeries.id,
            BinaryPackagePublishingHistory.archiveID.is_in(
                self.distribution.all_distro_archive_ids),
            ).order_by(BinaryPackagePublishingHistory.id)

    def getAllPublishedSources(self):
        """See `IDistroSeries`."""
        # Consider main archives only, and return all sources in
        # the PUBLISHED state.
        return self._getAllSources().find(
            status=PackagePublishingStatus.PUBLISHED)

    def getAllPublishedBinaries(self):
        """See `IDistroSeries`."""
        # Consider main archives only, and return all binaries in
        # the PUBLISHED state.
        return self._getAllBinaries().find(
            status=PackagePublishingStatus.PUBLISHED)

    def getAllUncondemnedSources(self):
        """See `IDistroSeries`."""
        return self._getAllSources().find(scheduleddeletiondate=None)

    def getAllUncondemnedBinaries(self):
        """See `IDistroSeries`."""
        return self._getAllBinaries().find(scheduleddeletiondate=None)

    def getSourcesPublishedForAllArchives(self):
        """See `IDistroSeries`."""
        query = """
            SourcePackagePublishingHistory.distroseries = %s AND
            SourcePackagePublishingHistory.archive = Archive.id AND
            SourcePackagePublishingHistory.status in %s AND
            Archive.purpose != %s
         """ % sqlvalues(self, active_publishing_status, ArchivePurpose.COPY)

        if not self.isUnstable():
            # Stable distroseries don't allow builds for the release
            # pockets for the primary archives, but they do allow them for
            # the PPA and PARTNER archives.

            # XXX: Julian 2007-09-14: this should come from a single
            # location where this is specified, not sprinkled around the code.
            query += ("""AND (Archive.purpose in %s OR
                            SourcePackagePublishingHistory.pocket != %s)""" %
                      sqlvalues(ALLOW_RELEASE_BUILDS,
                                PackagePublishingPocket.RELEASE))

        return SourcePackagePublishingHistory.select(
            query, clauseTables=['Archive'], orderBy="id")

    def getSourcePackagePublishing(self, status, pocket, component=None,
                                   archive=None):
        """See `IDistroSeries`."""
        archives = self.distribution.getArchiveIDList(archive)

        clause = """
            SourcePackagePublishingHistory.sourcepackagerelease=
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename=
                SourcePackageName.id AND
            SourcePackagePublishingHistory.distroseries=%s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.status=%s AND
            SourcePackagePublishingHistory.pocket=%s
            """ % sqlvalues(self, archives, status, pocket)

        if component:
            clause += (
                " AND SourcePackagePublishingHistory.component=%s"
                % sqlvalues(component))

        orderBy = ['SourcePackageName.name']
        clauseTables = ['SourcePackageRelease', 'SourcePackageName']

        return SourcePackagePublishingHistory.select(
            clause, orderBy=orderBy, clauseTables=clauseTables)

    def getBinaryPackagePublishing(
        self, name=None, version=None, archtag=None, sourcename=None,
        orderBy=None, pocket=None, component=None, archive=None):
        """See `IDistroSeries`."""
        archives = self.distribution.getArchiveIDList(archive)

        query = ["""
        BinaryPackagePublishingHistory.binarypackagerelease =
            BinaryPackageRelease.id AND
        BinaryPackagePublishingHistory.distroarchseries =
            DistroArchSeries.id AND
        BinaryPackageRelease.binarypackagename =
            BinaryPackageName.id AND
        BinaryPackageRelease.build =
            BinaryPackageBuild.id AND
        BinaryPackageBuild.source_package_release =
            SourcePackageRelease.id AND
        SourcePackageRelease.sourcepackagename =
            SourcePackageName.id AND
        DistroArchSeries.distroseries = %s AND
        BinaryPackagePublishingHistory.archive IN %s AND
        BinaryPackagePublishingHistory.status = %s
        """ % sqlvalues(self, archives, PackagePublishingStatus.PUBLISHED)]

        if name:
            query.append('BinaryPackageName.name = %s' % sqlvalues(name))

        if version:
            query.append('BinaryPackageRelease.version = %s'
                      % sqlvalues(version))

        if archtag:
            query.append('DistroArchSeries.architecturetag = %s'
                      % sqlvalues(archtag))

        if sourcename:
            query.append(
                'SourcePackageName.name = %s' % sqlvalues(sourcename))

        if pocket:
            query.append(
                'BinaryPackagePublishingHistory.pocket = %s'
                % sqlvalues(pocket))

        if component:
            query.append(
                'BinaryPackagePublishingHistory.component = %s'
                % sqlvalues(component))

        query = " AND ".join(query)

        clauseTables = ['BinaryPackagePublishingHistory', 'DistroArchSeries',
                        'BinaryPackageRelease', 'BinaryPackageName',
                        'BinaryPackageBuild', 'SourcePackageRelease',
                        'SourcePackageName']

        result = BinaryPackagePublishingHistory.select(
            query, distinct=False, clauseTables=clauseTables, orderBy=orderBy)

        return result

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        arch_tag=None, user=None, binary_only=True):
        """See IHasBuildRecords"""
        # Ignore "user", since it would not make any difference to the
        # records returned here (private builds are only in PPA right
        # now). We also ignore binary_only and always return binaries.

        # Find out the distroarchseries in question.
        arch_ids = DistroArchSeriesSet().getIdsForArchitectures(
            self.architectures, arch_tag)

        # Use the facility provided by IBinaryPackageBuildSet to
        # retrieve the records.
        return getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, arch_ids, build_state, name, pocket)

    def createUploadedSourcePackageRelease(
        self, sourcepackagename, version, maintainer, builddepends,
        builddependsindep, architecturehintlist, component, creator,
        urgency, changelog, changelog_entry, dsc, dscsigningkey, section,
        dsc_maintainer_rfc822, dsc_standards_version, dsc_format,
        dsc_binaries, archive, copyright, build_conflicts,
        build_conflicts_indep, dateuploaded=DEFAULT,
        source_package_recipe_build=None, user_defined_fields=None,
        homepage=None):
        """See `IDistroSeries`."""
        return SourcePackageRelease(
            upload_distroseries=self, sourcepackagename=sourcepackagename,
            version=version, maintainer=maintainer, dateuploaded=dateuploaded,
            builddepends=builddepends, builddependsindep=builddependsindep,
            architecturehintlist=architecturehintlist, component=component,
            creator=creator, urgency=urgency, changelog=changelog,
            changelog_entry=changelog_entry, dsc=dsc,
            dscsigningkey=dscsigningkey, section=section, copyright=copyright,
            upload_archive=archive,
            dsc_maintainer_rfc822=dsc_maintainer_rfc822,
            dsc_standards_version=dsc_standards_version,
            dsc_format=dsc_format, dsc_binaries=dsc_binaries,
            build_conflicts=build_conflicts,
            build_conflicts_indep=build_conflicts_indep,
            source_package_recipe_build=source_package_recipe_build,
            user_defined_fields=user_defined_fields, homepage=homepage)

    def getComponentByName(self, name):
        """See `IDistroSeries`."""
        comp = Component.byName(name)
        if comp is None:
            raise NotFoundError(name)
        permitted = set(self.components)
        if comp in permitted:
            return comp
        raise NotFoundError(name)

    def getSectionByName(self, name):
        """See `IDistroSeries`."""
        section = Section.byName(name)
        if section is None:
            raise NotFoundError(name)
        permitted = set(self.sections)
        if section in permitted:
            return section
        raise NotFoundError(name)

    def searchPackages(self, text):
        """See `IDistroSeries`."""

        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        find_spec = (
            DistroSeriesPackageCache,
            BinaryPackageName,
            SQL('rank(fti, ftq(%s)) AS rank' % sqlvalues(text)))
        origin = [
            DistroSeriesPackageCache,
            Join(
                BinaryPackageName,
                DistroSeriesPackageCache.binarypackagename ==
                    BinaryPackageName.id),
            ]

        # Note: When attempting to convert the query below into straight
        # Storm expressions, a 'tuple index out-of-range' error was always
        # raised.
        package_caches = store.using(*origin).find(
            find_spec,
            """DistroSeriesPackageCache.distroseries = %s AND
            DistroSeriesPackageCache.archive IN %s AND
            (fti @@ ftq(%s) OR
            DistroSeriesPackageCache.name ILIKE '%%' || %s || '%%')
            """ % (quote(self),
                   quote(self.distribution.all_distro_archive_ids),
                   quote(text), quote_like(text)),
            ).config(distinct=True)

        # Create a function that will decorate the results, converting
        # them from the find_spec above into a DSBP:
        def result_to_dsbp((cache, binary_package_name, rank)):
            return DistroSeriesBinaryPackage(
                distroseries=cache.distroseries,
                binarypackagename=binary_package_name,
                cache=cache)

        # Return the decorated result set so the consumer of these
        # results will only see DSBPs
        return DecoratedResultSet(package_caches, result_to_dsbp)

    def newArch(self, architecturetag, processorfamily, official, owner,
                supports_virtualized=False, enabled=True):
        """See `IDistroSeries`."""
        distroarchseries = DistroArchSeries(
            architecturetag=architecturetag, processorfamily=processorfamily,
            official=official, distroseries=self, owner=owner,
            supports_virtualized=supports_virtualized, enabled=enabled)
        return distroarchseries

    def newMilestone(self, name, dateexpected=None, summary=None,
                     code_name=None):
        """See `IDistroSeries`."""
        return Milestone(
            name=name, code_name=code_name,
            dateexpected=dateexpected, summary=summary,
            distribution=self.distribution, distroseries=self)

    def getLatestUploads(self):
        """See `IDistroSeries`."""
        query = """
        sourcepackagerelease.id=packageuploadsource.sourcepackagerelease
        AND sourcepackagerelease.sourcepackagename=sourcepackagename.id
        AND packageuploadsource.packageupload=packageupload.id
        AND packageupload.status=%s
        AND packageupload.distroseries=%s
        AND packageupload.archive IN %s
        """ % sqlvalues(
                PackageUploadStatus.DONE,
                self,
                self.distribution.all_distro_archive_ids)

        last_uploads = SourcePackageRelease.select(
            query, limit=5, prejoins=['sourcepackagename'],
            clauseTables=['SourcePackageName', 'PackageUpload',
                          'PackageUploadSource'],
            orderBy=['-packageupload.id'])

        distro_sprs = [
            self.getSourcePackageRelease(spr) for spr in last_uploads]

        return distro_sprs

    @staticmethod
    def setNewerDistroSeriesVersions(spphs):
        """Set the newer_distroseries_version attribute on the spph entries.

        :param spphs: The SourcePackagePublishingHistory objects to set the
            newer_distroseries_version attribute on.
        """
        # Partition by distro series to use getCurrentSourceReleases
        distro_series = collections.defaultdict(list)
        for spph in spphs:
            distro_series[spph.distroseries].append(spph)
        for series, spphs in distro_series.items():
            packagenames = set()
            for spph in spphs:
                packagenames.add(spph.sourcepackagerelease.sourcepackagename)
            latest_releases = series.getCurrentSourceReleases(
                packagenames)
            for spph in spphs:
                latest_release = latest_releases.get(spph.meta_sourcepackage)
                if latest_release is not None and apt_pkg.VersionCompare(
                    latest_release.version, spph.source_package_version) > 0:
                    version = latest_release
                else:
                    version = None
                get_property_cache(spph).newer_distroseries_version = version

    def createQueueEntry(self, pocket, archive, changesfilename=None,
                         changesfilecontent=None, changes_file_alias=None,
                         signing_key=None, package_copy_job=None):
        """See `IDistroSeries`."""
        if (changesfilename is None) != (changesfilecontent is None):
            raise AssertionError(
                "Inconsistent changesfilename and changesfilecontent. "
                "Pass either both, or neither.")
        if changes_file_alias is not None and changesfilename is not None:
            raise AssertionError(
                "Conflicting options: "
                "Both changesfilename and changes_file_alias were given.")
        have_changes_file = not (
            changesfilename is None and changes_file_alias is None)
        if package_copy_job is None and not have_changes_file:
            raise AssertionError(
                "changesfilename and changesfilecontent must be supplied "
                "if there is no package_copy_job")

        if changesfilename is not None:
            # We store the changes file in the librarian to avoid having to
            # deal with broken encodings in these files; this will allow us
            # to regenerate these files as necessary.
            #
            # The use of StringIO here should be safe: we do not encoding of
            # the content in the changes file (as doing so would be guessing
            # at best, causing unpredictable corruption), and simply pass it
            # off to the librarian.

            # The PGP signature is stripped from all changesfiles
            # to avoid replay attacks (see bugs 159304 and 451396).
            signed_message = signed_message_from_string(changesfilecontent)
            if signed_message is not None:
                # Overwrite `changesfilecontent` with the text stripped
                # of the PGP signature.
                new_content = signed_message.signedContent
                if new_content is not None:
                    changesfilecontent = signed_message.signedContent

            changes_file_alias = getUtility(ILibraryFileAliasSet).create(
                changesfilename, len(changesfilecontent),
                StringIO(changesfilecontent), 'text/plain',
                restricted=archive.private)

        return PackageUpload(
            distroseries=self, status=PackageUploadStatus.NEW,
            pocket=pocket, archive=archive,
            changesfile=changes_file_alias, signing_key=signing_key,
            package_copy_job=package_copy_job)

    def getPackageUploadQueue(self, state):
        """See `IDistroSeries`."""
        return PackageUploadQueue(self, state)

    def getPackageUploads(self, status=None, created_since_date=None,
                          archive=None, pocket=None, custom_type=None,
                          name=None, version=None, exact_match=False):
        """See `IDistroSeries`."""
        return getUtility(IPackageUploadSet).getAll(
            self, created_since_date, status, archive, pocket, custom_type,
            name=name, version=version, exact_match=exact_match)

    def createBug(self, bug_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        # We don't currently support opening a new bug on an IDistroSeries,
        # because internally bugs are reported against IDistroSeries only when
        # targeted to be fixed in that series, which is rarely the case for a
        # brand new bug report.
        raise NotImplementedError(
            "A new bug cannot be filed directly on a distribution series, "
            "because series are meant for \"targeting\" a fix to a specific "
            "version. It's possible that we may change this behaviour to "
            "allow filing a bug on a distribution series in the "
            "not-too-distant future. For now, you probably meant to file "
            "the bug on the distribution instead.")

    def getBugSummaryContextWhereClause(self):
        """See BugTargetBase."""
        # Circular fail.
        from lp.bugs.model.bugsummary import BugSummary
        return And(
                BugSummary.distroseries_id == self.id,
                BugSummary.sourcepackagename_id == None
                )

    def copyTranslationsFromParent(self, transaction, logger=None):
        """See `IDistroSeries`."""
        if logger is None:
            logger = logging

        assert self.defer_translation_imports, (
            "defer_translation_imports not set!"
            " That would corrupt translation data mixing new imports"
            " with the information being copied.")

        assert self.hide_all_translations, (
            "hide_all_translations not set!"
            " That would allow users to see and modify incomplete"
            " translation state.")

        flush_database_updates()
        flush_database_caches()
        copy_active_translations(self, transaction, logger)

    def getPOFileContributorsByLanguage(self, language):
        """See `IDistroSeries`."""
        contributors = IStore(Person).find(
            Person,
            POFileTranslator.personID == Person.id,
            POFile.id == POFileTranslator.pofileID,
            POFile.language == language,
            POTemplate.id == POFile.potemplateID,
            POTemplate.distroseries == self,
            POTemplate.iscurrent == True)
        contributors = contributors.order_by(*Person._storm_sortingColumns)
        contributors = contributors.config(distinct=True)
        return contributors

    def getPendingPublications(self, archive, pocket, is_careful):
        """See ICanPublishPackages."""
        queries = ['distroseries = %s' % sqlvalues(self)]

        # Query main archive for this distroseries
        queries.append('archive=%s' % sqlvalues(archive))

        # Careful publishing should include all PUBLISHED rows, normal run
        # only includes PENDING ones.
        statuses = [PackagePublishingStatus.PENDING]
        if is_careful:
            statuses.append(PackagePublishingStatus.PUBLISHED)
        queries.append('status IN %s' % sqlvalues(statuses))

        # Restrict to a specific pocket.
        queries.append('pocket = %s' % sqlvalues(pocket))

        # Exclude RELEASE pocket if the distroseries was already released,
        # since it should not change for main archive.
        # We allow RELEASE publishing for PPAs.
        # We also allow RELEASE publishing for partner.
        if (not self.isUnstable() and
            not archive.allowUpdatesToReleasePocket()):
            queries.append(
            'pocket != %s' % sqlvalues(PackagePublishingPocket.RELEASE))

        publications = SourcePackagePublishingHistory.select(
            " AND ".join(queries), orderBy="-id")

        return publications

    def publish(self, diskpool, log, archive, pocket, is_careful=False):
        """See ICanPublishPackages."""
        log.debug("Publishing %s-%s" % (self.title, pocket.name))
        log.debug("Attempting to publish pending sources.")

        dirty_pockets = set()
        for spph in self.getPendingPublications(archive, pocket, is_careful):
            if not self.checkLegalPocket(spph, is_careful, log):
                continue
            spph.publish(diskpool, log)
            dirty_pockets.add((self.name, spph.pocket))

        # propagate publication request to each distroarchseries.
        for dar in self.architectures:
            more_dirt = dar.publish(
                diskpool, log, archive, pocket, is_careful)
            dirty_pockets.update(more_dirt)

        return dirty_pockets

    def checkLegalPocket(self, publication, is_careful, log):
        """Check if the publication can happen in the archive."""
        # 'careful' mode re-publishes everything:
        if is_careful:
            return True

        # PPA and PARTNER allow everything.
        if publication.archive.allowUpdatesToReleasePocket():
            return True

        # FROZEN state also allow all pockets to be published.
        if self.status == SeriesStatus.FROZEN:
            return True

        # If we're not republishing, we want to make sure that
        # we're not publishing packages into the wrong pocket.
        # Unfortunately for careful mode that can't hold true
        # because we indeed need to republish everything.
        if (self.isUnstable() and
            publication.pocket != PackagePublishingPocket.RELEASE):
            log.error("Tried to publish %s (%s) into a non-release "
                      "pocket on unstable series %s, skipping"
                      % (publication.displayname, publication.id,
                         self.displayname))
            return False
        if (not self.isUnstable() and
            publication.pocket == PackagePublishingPocket.RELEASE):
            log.error("Tried to publish %s (%s) into release pocket "
                      "on stable series %s, skipping"
                      % (publication.displayname, publication.id,
                         self.displayname))
            return False

        return True

    @property
    def main_archive(self):
        return self.distribution.main_archive

    def getTemplatesCollection(self):
        """See `IHasTranslationTemplates`."""
        return TranslationTemplatesCollection().restrictDistroSeries(self)

    def getSharingPartner(self):
        """See `IHasTranslationTemplates`."""
        # No sharing partner is defined for DistroSeries.
        return None

    def getSuite(self, pocket):
        """See `IDistroSeries`."""
        if pocket == PackagePublishingPocket.RELEASE:
            return self.name
        else:
            return '%s%s' % (self.name, pocketsuffix[pocket])

    def isSourcePackageFormatPermitted(self, format):
        return getUtility(
            ISourcePackageFormatSelectionSet).getBySeriesAndFormat(
                self, format) is not None

    def initDerivedDistroSeries(self, user, parents, architectures=(),
                                packagesets=(), rebuild=False, overlays=(),
                                overlay_pockets=(),
                                overlay_components=()):
        """See `IDistroSeries`."""
        if self.isDerivedSeries():
            raise DerivationError(
                "DistroSeries %s already has parent series." % self.name)
        initialize_series = InitializeDistroSeries(
            self, parents, architectures, packagesets, rebuild, overlays,
            overlay_pockets, overlay_components)
        try:
            initialize_series.check()
        except InitializationError, e:
            raise DerivationError(e)
        getUtility(IInitializeDistroSeriesJobSource).create(
            self, parents, architectures, packagesets, rebuild, overlays,
            overlay_pockets, overlay_components)

    def getParentSeries(self):
        """See `IDistroSeriesPublic`."""
        # Circular imports.
        from lp.registry.interfaces.distroseriesparent import (
            IDistroSeriesParentSet,
            )
        dsp_set = getUtility(IDistroSeriesParentSet)
        dsps = dsp_set.getByDerivedSeries(self).order_by('ordering')
        return [dsp.parent_series for dsp in dsps]

    def getDerivedSeries(self):
        """See `IDistroSeriesPublic`."""
        # Circular imports.
        from lp.registry.interfaces.distroseriesparent import (
            IDistroSeriesParentSet,
            )
        dsps = getUtility(IDistroSeriesParentSet).getByParentSeries(self)
        return [dsp.derived_series for dsp in dsps]

    def getBugTaskWeightFunction(self):
        """Provide a weight function to determine optimal bug task.

        Full weight is given to tasks for this distro series.

        If the series isn't found, the distribution task is better than
        others.
        """
        seriesID = self.id
        distributionID = self.distributionID

        def weight_function(bugtask):
            if bugtask.distroseriesID == seriesID:
                return OrderedBugTask(1, bugtask.id, bugtask)
            elif bugtask.distributionID == distributionID:
                return OrderedBugTask(2, bugtask.id, bugtask)
            else:
                return OrderedBugTask(3, bugtask.id, bugtask)
        return weight_function

    def getDifferencesTo(self, parent_series=None, difference_type=None,
                         source_package_name_filter=None, status=None,
                         child_version_higher=False):
        """See `IDistroSeries`."""
        return getUtility(
            IDistroSeriesDifferenceSource).getForDistroSeries(
                self,
                difference_type=difference_type,
                name_filter=source_package_name_filter,
                status=status,
                child_version_higher=child_version_higher)

    def isDerivedSeries(self):
        """See `IDistroSeries`."""
        return not self.getParentSeries() == []

    def isInitializing(self):
        """See `IDistroSeries`."""
        job = self.getInitializationJob()
        return job is not None and job.is_pending

    def isInitialized(self):
        """See `IDistroSeries`."""
        published = self.main_archive.getPublishedSources(distroseries=self)
        return not published.is_empty()

    def getInitializationJob(self):
        """See `IDistroSeries`."""
        return getUtility(IInitializeDistroSeriesJobSource).get(self)

    def getDifferenceComments(self, since=None, source_package_name=None):
        """See `IDistroSeries`."""
        comment_source = getUtility(IDistroSeriesDifferenceCommentSource)
        return comment_source.getForDistroSeries(
            self, since=since, source_package_name=source_package_name)


class DistroSeriesSet:
    implements(IDistroSeriesSet)

    def get(self, distroseriesid):
        """See `IDistroSeriesSet`."""
        return DistroSeries.get(distroseriesid)

    def translatables(self):
        """See `IDistroSeriesSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        # Join POTemplate distinctly to only get entries with available
        # translations.
        result_set = store.using((DistroSeries, POTemplate)).find(
            DistroSeries,
            DistroSeries.hide_all_translations == False,
            DistroSeries.id == POTemplate.distroseriesID)
        result_set = result_set.config(distinct=True)
        return result_set

    def findByName(self, name):
        """See `IDistroSeriesSet`."""
        return DistroSeries.selectBy(name=name)

    def queryByName(self, distribution, name):
        """See `IDistroSeriesSet`."""
        return DistroSeries.selectOneBy(distribution=distribution, name=name)

    def findByVersion(self, version):
        """See `IDistroSeriesSet`."""
        return DistroSeries.selectBy(version=version)

    def _parseSuite(self, suite):
        """Parse 'suite' into a series name and a pocket."""
        tokens = suite.rsplit('-', 1)
        if len(tokens) == 1:
            return suite, PackagePublishingPocket.RELEASE
        series, pocket = tokens
        try:
            pocket = PackagePublishingPocket.items[pocket.upper()]
        except KeyError:
            # No such pocket. Probably trying to get a hyphenated series name.
            return suite, PackagePublishingPocket.RELEASE
        else:
            return series, pocket

    def fromSuite(self, distribution, suite):
        """See `IDistroSeriesSet`."""
        series_name, pocket = self._parseSuite(suite)
        series = distribution.getSeries(series_name)
        return series, pocket

    def getCurrentSourceReleases(self, distro_series_source_packagenames):
        """See `IDistroSeriesSet`."""
        # Builds one query for all the distro_series_source_packagenames.
        # This may need tuning: its possible that grouping by the common
        # archives may yield better efficiency: the current code is
        # just a direct push-down of the previous in-python lookup to SQL.
        series_clauses = []
        distroseries_lookup = {}
        for distroseries, package_names in \
            distro_series_source_packagenames.items():
            source_package_ids = map(attrgetter('id'), package_names)
            # all_distro_archive_ids is just a list of ints, but it gets
            # wrapped anyway - and sqlvalues goes boom.
            archives = removeSecurityProxy(
                distroseries.distribution.all_distro_archive_ids)
            clause = """(spr.sourcepackagename IN %s AND
                spph.archive IN %s AND
                spph.distroseries = %s)
                """ % sqlvalues(source_package_ids, archives, distroseries.id)
            series_clauses.append(clause)
            distroseries_lookup[distroseries.id] = distroseries
        if not len(series_clauses):
            return {}
        combined_clause = "(" + " OR ".join(series_clauses) + ")"

        releases = IStore(SourcePackageRelease).find(
            (SourcePackageRelease, DistroSeries.id), SQL("""
                (SourcePackageRelease.id, DistroSeries.id) IN (
                    SELECT
                        DISTINCT ON (spr.sourcepackagename, spph.distroseries)
                        spr.id, spph.distroseries
                    FROM
                        SourcePackageRelease AS spr,
                        SourcePackagePublishingHistory AS spph
                    WHERE
                        spph.sourcepackagerelease = spr.id
                        AND spph.status IN %s
                        AND %s
                    ORDER BY
                        spr.sourcepackagename, spph.distroseries, spph.id DESC
                    )
                """
                % (sqlvalues(active_publishing_status) + (combined_clause,))))
        result = {}
        for sp_release, distroseries_id in releases:
            distroseries = distroseries_lookup[distroseries_id]
            sourcepackage = distroseries.getSourcePackage(
                sp_release.sourcepackagename)
            result[sourcepackage] = DistroSeriesSourcePackageRelease(
                distroseries, sp_release)
        return result

    def search(self, distribution=None, isreleased=None, orderBy=None):
        """See `IDistroSeriesSet`."""
        where_clause = ""
        if distribution is not None:
            where_clause += "distribution = %s" % sqlvalues(distribution.id)
        if isreleased is not None:
            if where_clause:
                where_clause += " AND "
            if isreleased:
                # The query is filtered on released releases.
                where_clause += "releasestatus in (%s, %s)" % sqlvalues(
                    SeriesStatus.CURRENT,
                    SeriesStatus.SUPPORTED)
            else:
                # The query is filtered on unreleased releases.
                where_clause += "releasestatus in (%s, %s, %s)" % sqlvalues(
                    SeriesStatus.EXPERIMENTAL,
                    SeriesStatus.DEVELOPMENT,
                    SeriesStatus.FROZEN)
        if orderBy is not None:
            return DistroSeries.select(where_clause, orderBy=orderBy)
        else:

            return DistroSeries.select(where_clause)

    def priorReleasedSeries(self, distribution, prior_to_date):
            """See `IDistroSeriesSet`."""
            store = Store.of(distribution)
            results = store.find(
                DistroSeries,
                DistroSeries.distributionID == distribution.id,
                DistroSeries.datereleased < prior_to_date,
                DistroSeries.datereleased != None
            ).order_by(Desc(DistroSeries.datereleased))

            return results
