"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""
from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from sqlobject import ForeignKey, IntCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugProductInfestationSet, \
                                           IBugPackageInfestationSet, \
                                           IBugProductInfestation, \
                                           IBugPackageInfestation

from canonical.launchpad.database.bugset import BugSetBase
from canonical.lp import dbschema
from canonical.lp.dbschema import EnumCol


__all__ = ['BugProductInfestation', 'BugPackageInfestation',
           'BugProductInfestationSet',
           'BugPackageInfestationSet',
           'BugProductInfestationFactory',
           'BugPackageInfestationFactory'
           ]

class BugProductInfestation(SQLBase):
    implements(IBugProductInfestation)
    _table = 'BugProductInfestation'
    # field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    explicit = IntCol(notNull=True, default=False)
    productrelease = ForeignKey(
        dbName="productrelease", foreignKey='ProductRelease', notNull=False, default=None)
    infestationstatus = EnumCol(
        notNull=False, default=None, schema=dbschema.BugInfestationStatus)
    datecreated = UtcDateTimeCol(notNull=True)
    creator = ForeignKey(dbName="creator", foreignKey='Person', notNull=True)
    dateverified = UtcDateTimeCol(notNull=False)
    verifiedby = ForeignKey(
        dbName="verifiedby", foreignKey='Person', notNull=False, default=None)
    lastmodified = UtcDateTimeCol(notNull=True)
    lastmodifiedby = ForeignKey(dbName="lastmodifiedby", foreignKey='Person', notNull=True)

    # used for launchpad pages
    def _title(self):
        title = 'Malone Bug #' + str(self.bug.id) + ' infests '
        title += self.productrelease.productseries.product.displayname
        return title
    title = property(_title)
    



class BugPackageInfestation(SQLBase):
    implements(IBugPackageInfestation)
    _table = 'BugPackageInfestation'
    # field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    explicit = IntCol(dbName='explicit', notNull=True, default=False)
    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease', foreignKey='SourcePackageRelease', notNull=True)
    infestationstatus = EnumCol(dbName='infestationstatus', notNull=True,
        schema=dbschema.BugInfestationStatus)
    datecreated = UtcDateTimeCol(dbName='datecreated', notNull=True)
    creator = ForeignKey(dbName='creator', foreignKey='Person', notNull=True)
    dateverified = UtcDateTimeCol(dbName='dateverified')
    verifiedby = ForeignKey(dbName='verifiedby', foreignKey='Person')
    lastmodified = UtcDateTimeCol(dbName='lastmodified')
    lastmodifiedby = ForeignKey(dbName='lastmodifiedby', foreignKey='Person')

    # used for launchpad pages
    def _title(self):
        title = 'Malone Bug #' + str(self.bug.id) + ' infests '
        title += self.sourcepackagerelease.name
        return title
    title = property(_title)
    

class BugProductInfestationSet(BugSetBase):
    """A set for BugProductInfestation."""
    implements(IBugProductInfestationSet)
    table = BugProductInfestation

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row


class BugPackageInfestationSet(BugSetBase):
    """A set for BugPackageInfestation."""
    implements(IBugPackageInfestationSet)
    table = BugPackageInfestation

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row


def BugProductInfestationFactory(context, **kw):
    return BugProductInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=UTC_NOW,
        creatorID=context.request.principal.id,
        dateverified=UTC_NOW,
        verifiedbyID=context.request.principal.id,
        lastmodified=UTC_NOW,
        lastmodifiedbyID=context.request.principal.id,
        **kw)

def BugPackageInfestationFactory(context, **kw):
    return BugPackageInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=UTC_NOW,
        creatorID=context.request.principal.id,
        dateverified=UTC_NOW,
        verifiedbyID=context.request.principal.id,
        lastmodified=UTC_NOW,
        lastmodifiedbyID=context.request.principal.id,
        **kw)
