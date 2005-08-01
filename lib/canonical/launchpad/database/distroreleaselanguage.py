# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroReleaseLanguage', 'DummyDistroReleaseLanguage',
           'DistroReleaseLanguageSet']

from datetime import datetime

# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, IntCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol

# canonical imports
import pytz

from canonical.launchpad.interfaces import (IDistroReleaseLanguage,
    IDistroReleaseLanguageSet)
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.person import Person
from canonical.launchpad.database.pofile import POFile, DummyPOFile
from canonical.launchpad.database.translator import Translator
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.launchpad.components.rosettastats import RosettaStats

class DistroReleaseLanguage(SQLBase, RosettaStats):

    implements(IDistroReleaseLanguage)

    _table = 'DistroReleaseLanguage'

    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease', notNull=False, default=None)
    language = ForeignKey(foreignKey='Language', dbName='language',
        notNull=True)
    currentcount = IntCol(notNull=True, default=0)
    updatescount = IntCol(notNull=True, default=0)
    rosettacount = IntCol(notNull=True, default=0)
    contributorcount = IntCol(notNull=True, default=0)
    dateupdated = UtcDateTimeCol(dbName='dateupdated', default=DEFAULT)

    @property
    def title(self):
        return '%s translations of applications in %s, %s' % (
            self.language.englishname,
            self.distrorelease.distribution.displayname,
            self.distrorelease.title)

    @property
    def pofiles(self):
        return POFile.select('''
            POFile.language = %s AND
            POFile.potemplate = POTemplate.id AND
            POTemplate.distrorelease = %s
            ''' % sqlvalues(self.language.id, self.distrorelease.id),
            clauseTables=['POTemplate'],
            orderBy=['id'])

    @property
    def translators(self):
        return Translator.select('''
            Translator.translationgroup = TranslationGroup.id AND
            Distribution.translationgroup = TranslationGroup.id AND
            DistroRelease.distribution = Distribution.id AND
            DistroRelease.id = %s AND
            Translator.language = %s
            ''' % sqlvalues(self.distrorelease.id, self.language.id),
            orderBy=['id'],
            clauseTables=['TranslationGroup', 'Distribution',
                          'DistroRelease'],
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
        return self.distrorelease.messagecount

    def currentCount(self, language=None):
        return self.currentcount

    def updatesCount(self, language=None):
        return self.updatescount

    def rosettaCount(self, language=None):
        return self.rosettacount

    def updateStatistics(self):
        current = 0
        updates = 0
        rosetta = 0
        for pofile in self.pofiles:
            current += pofile.currentCount()
            updates += pofile.updatesCount()
            rosetta += pofile.rosettaCount()
        self.currentcount = current
        self.updatescount = updates
        self.rosettacount = rosetta
        self.contributorcount = Person.select('''
            Person.id = POSubmission.person AND
            POSubmission.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = %s AND
            POFile.potemplate = POTemplate.id AND
            POTemplate.distrorelease = %s
            ''' % sqlvalues(self.language.id, self.distrorelease.id),
            clauseTables=['POSubmission', 'POMsgSet', 'POFile',
                          'POTemplate'],
            distinct=True).count()
        self.dateupdated = UTC_NOW


class DummyDistroReleaseLanguage(RosettaStats):
    """
    Represents a DistroReleaseLanguage where we do not yet actually HAVE one
    for that language for this distro release.
    """
    implements(IDistroReleaseLanguage)

    def __init__(self, distrorelease, language):
        self.distrorelease = distrorelease
        self.language = language
        self.messageCount = distrorelease.messagecount
        self.dateupdated = datetime.now(tz=pytz.timezone('UTC'))
        self.translator_count = 0
        self.contributor_count = 0
        self.title = '%s translations of applications in %s, %s' % (
            self.language.englishname,
            self.distrorelease.distribution.displayname,
            self.distrorelease.title)

    @property
    def pofiles(self):
        """We need to pretend that we have pofiles, so we will use
        DummyPOFile's."""
        pofiles = []
        for potemplate in self.distrorelease.potemplates:
            pofiles.append(DummyPOFile(potemplate, self.language))
        return pofiles

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


class DistroReleaseLanguageSet:

    implements(IDistroReleaseLanguageSet)

    def getDummy(self, distrorelease, language):
        """See IDistroReleaseLanguageSet."""
        return DummyDistroReleaseLanguage(distrorelease, language)

