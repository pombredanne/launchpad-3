# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

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
        return POTemplate.select().count()

    def pofile_count(self):
        """See IRosettaApplication."""
        return POFile.select().count()

    def pomsgid_count(self):
        """See IRosettaApplication."""
        return POMsgID.select().count()

    def translator_count(self):
        """See IRosettaApplication."""
        return Person.select("POSubmission.person=Person.id",
            clauseTables=['POSubmission'], distinct=True).count()

    def language_count(self):
        """See IRosettaApplication."""
        return Language.select("POFile.language=Language.id",
            clauseTables=['POFile'], distinct=True).count()
        
    name = 'Rosetta'

