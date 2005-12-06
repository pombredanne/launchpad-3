# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from datetime import datetime, timedelta

from zope.interface import implements
from zope.component import getUtility

import pytz

from canonical.launchpad.interfaces import (
    IRosettaApplication, IProductSet, IDistroReleaseSet,
    ITranslationGroupSet, ILaunchpadStatisticSet)
from canonical.launchpad.database import (
    POTemplate, POFile, Language, POMsgID, Person)
from canonical.database.constants import UTC_NOW


class RosettaApplication:
    implements(IRosettaApplication)

    def __init__(self):
        self.title = 'Rosetta: Translations in the Launchpad'
        self.name = 'Rosetta'

    @property
    def statsdate(self):
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.dateupdated('potemplate_count')

    def updateStatistics(self, ztm):
        stats = getUtility(ILaunchpadStatisticSet)
        stats.update('potemplate_count', POTemplate.select().count())
        ztm.commit()
        stats.update('pofile_count', POFile.select().count())
        ztm.commit()
        stats.update('pomsgid_count', POMsgID.select().count())
        ztm.commit()
        stats.update('translator_count', Person.select(
            "POSubmission.person=Person.id",
            clauseTables=['POSubmission'],
            distinct=True).count())
        ztm.commit()
        stats.update('language_count', Language.select(
            "POFile.language=Language.id",
            clauseTables=['POFile'],
            distinct=True).count())
        ztm.commit()

    def translatable_products(self):
        """See IRosettaApplication."""
        products = getUtility(IProductSet)
        return products.translatables()

    def translatable_distroreleases(self):
        """See IRosettaApplication."""
        distroreleases = getUtility(IDistroReleaseSet)
        return distroreleases.translatables()

    def translation_groups(self):
        """See IRosettaApplication."""
        return getUtility(ITranslationGroupSet)

    def potemplate_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('potemplate_count')

    def pofile_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('pofile_count')

    def pomsgid_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('pomsgid_count')

    def translator_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('translator_count')

    def language_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('language_count')

