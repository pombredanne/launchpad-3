# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import IRosettaApplication
from canonical.publication import rootObject
from canonical.launchpad.database import POTemplate, Product

class RosettaApplication:
    implements(IRosettaApplication)

    __parent__ = rootObject

    def translatables(self, translationProject=None):
        """This will give a list of the translatables in the given
        Translation Project. For the moment it just returns every
        translatable product."""
        clauseTables = ['Product', 'POTemplate']
        query = """POTemplate.product=Product.id"""
        return Product.select(query, clauseTables=clauseTables)

