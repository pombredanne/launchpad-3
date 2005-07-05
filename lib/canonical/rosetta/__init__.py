# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from datetime import datetime, timedelta

from zope.interface import implements
from zope.component import getUtility

import pytz

from canonical.launchpad.interfaces import IRosettaApplication, \
    IProductSet, IDistroReleaseSet, ITranslationGroupSet
from canonical.launchpad.database import POTemplate, POFile, Language, \
    POMsgID, Person
from canonical.publication import rootObject


class RosettaApplication:
    implements(IRosettaApplication)

    __parent__ = rootObject

    def __init__(self):
        self.title = 'Rosetta: Translations in the Launchpad'
        self.statsdate = None

    def _update_stats(self):
        now = datetime.now(pytz.timezone('UTC'))
        aday = timedelta(1)
        if self.statsdate is not None and self.statsdate + aday > now:
            return
        self._potemplate_count = POTemplate.select().count()
        self._pofile_count = POFile.select().count()
        self._pomsgid_count = POMsgID.select().count()
        self._translator_count = Person.select(
                    "POSubmission.person=Person.id",
                    clauseTables=['POSubmission'],
                    distinct=True).count()
        self._language_count = Language.select(
                    "POFile.language=Language.id",
                    clauseTables=['POFile'],
                    distinct=True).count()
        self.statsdate = datetime.now(pytz.timezone('UTC'))

    def translatable_products(self, translationProject=None):
        """See IRosettaApplication."""
        products = getUtility(IProductSet)
        return products.translatables(translationProject)

    def translatable_distroreleases(self):
        """See IRosettaApplication."""
        distroreleases = getUtility(IDistroReleaseSet)
        return distroreleases.translatables()

    def translation_groups(self):
        """See IRosettaApplication."""
        return getUtility(ITranslationGroupSet)

    def potemplate_count(self):
        """See IRosettaApplication."""
        self._update_stats()
        return self._potemplate_count

    def pofile_count(self):
        """See IRosettaApplication."""
        self._update_stats()
        return self._pofile_count

    def pomsgid_count(self):
        """See IRosettaApplication."""
        self._update_stats()
        return self._pomsgid_count

    def translator_count(self):
        """See IRosettaApplication."""
        self._update_stats()
        return self._translator_count

    def language_count(self):
        """See IRosettaApplication."""
        self._update_stats()
        return self._language_count
        
    name = 'Rosetta'

