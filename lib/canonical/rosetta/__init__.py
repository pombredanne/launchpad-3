# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import IRosettaApplication, IProductSet
from canonical.publication import rootObject

class RosettaApplication:
    implements(IRosettaApplication)

    __parent__ = rootObject

    def translatables(self, translationProject=None):
        products = getUtility(IProductSet)

        return products.translatables(translationProject)
