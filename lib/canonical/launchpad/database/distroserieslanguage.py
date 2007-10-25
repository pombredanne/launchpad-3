# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""An implementation of DistroSeriesLanguage objects."""

__metaclass__ = type

__all__ = [
    'DistroSeriesLanguage',
    'DistroSeriesLanguageSet',
    'DummyDistroSeriesLanguage',
    ]

from datetime import datetime
import pytz

from sqlobject import ForeignKey, IntCol
from zope.interface import implements
from zope.component import getUtility

from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.database.pofile import POFile, DummyPOFile
from canonical.launchpad.database.translator import Translator
from canonical.launchpad.interfaces import (
    IDistroSeriesLanguage, IDistroSeriesLanguageSet, IPersonSet)


class DistroSeriesLanguage(SQLBase, RosettaStats):
    """See `IDistroSeriesLanguage`.

    A SQLObject based implementation of IDistroSeriesLanguage.
    """
    implements(IDistroSeriesLanguage)

    _table = 'DistroReleaseLanguage'

    distroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='distrorelease', notNull=False, default=None)
    language = ForeignKey(foreignKey='Language', dbName='language',
        notNull=True)
    currentcount = IntCol(notNull=True, default=0)
    updatescount = IntCol(notNull=True, default=0)
    rosettacount = IntCol(notNull=True, default=0)
    unreviewed_count = IntCol(notNull=True, default=0)
    contributorcount = IntCol(notNull=True, default=0)
    dateupdated = UtcDateTimeCol(dbName='dateupdated', default=DEFAULT)

    @property
    def title(self):
        return '%s translations of applications in %s, %s' % (
            self.language.englishname,
            self.distroseries.distribution.displayname,
            self.distroseries.title)

    @property
    def pofiles(self):
        return POFile.select('''
            POFile.language = %s AND
            POFile.variant IS NULL AND
            POFile.potemplate = POTemplate.id AND
            POTemplate.distrorelease = %s AND
            POTemplate.iscurrent = TRUE
            ''' % sqlvalues(self.language.id, self.distroseries.id),
            clauseTables=['POTemplate'],
            prejoins=["potemplate.sourcepackagename",
                      "last_touched_pomsgset.reviewer"],
            orderBy=['-POTemplate.priority', 'POFile.id'])

    @property
    def po_files_or_dummies(self):
        """See IDistroSeriesLanguage."""
        pofiles = list(self.pofiles)
        # Note that only self.pofiles actually prejoins anything in;
        # this means that we issue additional queries for
        # SourcePackageName for every DummyPOFile when displaying the
        # list of templates per distribution series.
        translated_pots = set(pofile.potemplate for pofile in pofiles)
        all_pots = set(self.distroseries.getCurrentTranslationTemplates())
        untranslated_pots = all_pots - translated_pots
        dummies = [DummyPOFile(pot, self.language)
                   for pot in untranslated_pots]

        return sorted(pofiles + dummies,
                      key=lambda x: (-x.potemplate.priority,
                                     x.potemplate.name,
                                     x.potemplate.id))

    @property
    def translators(self):
        return Translator.select('''
            Translator.translationgroup = TranslationGroup.id AND
            Distribution.translationgroup = TranslationGroup.id AND
            Distribution.id = %s
            Translator.language = %s
            ''' % sqlvalues(self.distroseries.distribution.id,
                            self.language.id),
            orderBy=['id'],
            clauseTables=['TranslationGroup', 'Distribution',],
            distinct=True)

    @property
    def translator_count(self):
        translators = set()
        for translator in self.translators:
            translators = translators.union(translator.allmembers)
        return len(translators)

    @property
    def contributor_count(self):
        return self.contributorcount

    def messageCount(self):
        return self.distroseries.messagecount

    def currentCount(self, language=None):
        return self.currentcount

    def updatesCount(self, language=None):
        return self.updatescount

    def rosettaCount(self, language=None):
        return self.rosettacount

    def unreviewedCount(self):
        """See `IRosettaStats`."""
        return self.unreviewed_count

    def updateStatistics(self, ztm):
        current = 0
        updates = 0
        rosetta = 0
        unreviewed = 0
        for pofile in self.pofiles:
            current += pofile.currentCount()
            updates += pofile.updatesCount()
            rosetta += pofile.rosettaCount()
            unreviewed += pofile.unreviewedCount()
        self.currentcount = current
        self.updatescount = updates
        self.rosettacount = rosetta
        self.unreviewed_count = unreviewed

        personset = getUtility(IPersonSet)
        contributors = personset.getPOFileContributorsByDistroSeries(
            self.distroseries, self.language)
        self.contributorcount = contributors.count()

        self.dateupdated = UTC_NOW
        ztm.commit()


class DummyDistroSeriesLanguage(RosettaStats):
    """See `IDistroSeriesLanguage`

    Represents a DistroSeriesLanguage where we do not yet actually HAVE one
    for that language for this distribution series.
    """
    implements(IDistroSeriesLanguage)

    def __init__(self, distroseries, language):
        assert 'en' != language.code, (
            'English is not a translatable language.')
        self.id = None
        self.language = language
        self.distroseries = distroseries
        self.messageCount = distroseries.messagecount
        self.dateupdated = datetime.now(tz=pytz.timezone('UTC'))
        self.translator_count = 0
        self.contributor_count = 0
        self.title = '%s translations of applications in %s, %s' % (
            self.language.englishname,
            self.distroseries.distribution.displayname,
            self.distroseries.title)

    @property
    def pofiles(self):
        """We need to pretend that we have pofiles, so we will use
        DummyPOFile's."""
        pofiles = []
        for potemplate in self.distroseries.getCurrentTranslationTemplates():
            pofiles.append(DummyPOFile(potemplate, self.language))
        return pofiles

    @property
    def po_files_or_dummies(self):
        """In this case they are all dummy pofiles since we are a dummy
        ourselves."""
        return self.pofiles

    def currentCount(self):
        return 0

    def rosettaCount(self):
        return 0

    def updatesCount(self):
        return 0

    def nonUpdatesCount(self):
        return 0

    def translatedCount(self):
        return 0

    def untranslatedCount(self):
        return self.messageCount

    def unreviewedCount(self):
        return 0

    def currentPercentage(self):
        return 0.0

    def rosettaPercentage(self):
        return 0.0

    def updatesPercentage(self):
        return 0.0

    def nonUpdatesPercentage(self):
        return 0.0

    def translatedPercentage(self):
        return 0.0

    def untranslatedPercentage(self):
        return 100.0


class DistroSeriesLanguageSet:
    """See `IDistroSeriesLanguageSet`.

    Implements a means to get a DummyDistroSeriesLanguage.
    """
    implements(IDistroSeriesLanguageSet)

    def getDummy(self, distroseries, language):
        """See IDistroSeriesLanguageSet."""
        return DummyDistroSeriesLanguage(distroseries, language)

