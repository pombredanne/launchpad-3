# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from canonical.launchpad.interfaces import IRosettaApplication, \
    IProductSet, IDistroReleaseSet
from canonical.publication import rootObject


class RosettaApplication:
    implements(IRosettaApplication)

    __parent__ = rootObject

    def __init__(self):
        self.title = 'Rosetta: Translations in the Launchpad'

    def translatable_products(self, translationProject=None):
        """This will give a list of the translatable products in the given
        Translation Project. For the moment it just returns every
        translatable product."""
        products = getUtility(IProductSet)
        return products.translatables(translationProject)

    def translatable_distroreleases(self):
        """This will give a list of the distroreleases in launchpad for
        which translations can be done."""
        distroreleases = getUtility(IDistroReleaseSet)
        return distroreleases.translatables()

    name = 'Rosetta'

