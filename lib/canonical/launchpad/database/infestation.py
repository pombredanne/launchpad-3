
"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
# SQL imports
from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import *
from canonical.launchpad.database.bugcontainer import BugContainerBase


__all__ = ['BugProductInfestation', 'BugPackageInfestation',
           'BugProductInfestationContainer',
           'BugPackageInfestationContainer',
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
    infestationstatus = IntCol(notNull=False, default=None)
    datecreated = DateTimeCol(notNull=True)
    creator = ForeignKey(dbName="creator", foreignKey='Person', notNull=True)
    dateverified = DateTimeCol(notNull=False)
    verifiedby = ForeignKey(
        dbName="verifiedby", foreignKey='Person', notNull=False, default=None)
    lastmodified = DateTimeCol(notNull=True)
    lastmodifiedby = ForeignKey(dbName="lastmodifiedby", foreignKey='Person', notNull=True)



class BugPackageInfestation(SQLBase):
    implements(IBugPackageInfestation)
    _table = 'BugPackageInfestation'
    # field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    explicit = IntCol(dbName='explicit', notNull=True, default=False)
    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease', foreignKey='SourcePackageRelease', notNull=True)
    infestationstatus = IntCol(dbName='infestationstatus', notNull=True)
    datecreated = DateTimeCol(dbName='datecreated', notNull=True)
    creator = ForeignKey(dbName='creator', foreignKey='Person', notNull=True)
    dateverified = DateTimeCol(dbName='dateverified')
    verifiedby = ForeignKey(dbName='verifiedby', foreignKey='Person')
    lastmodified = DateTimeCol(dbName='lastmodified')
    lastmodifiedby = ForeignKey(dbName='lastmodifiedby', foreignKey='Person')


class BugProductInfestationContainer(BugContainerBase):
    """A container for BugProductInfestation."""
    implements(IBugProductInfestationContainer)
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


class BugPackageInfestationContainer(BugContainerBase):
    """A container for BugPackageInfestation."""
    implements(IBugPackageInfestationContainer)
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
    now = datetime.utcnow()
    bpi = BugProductInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=now,
        creatorID=1, # XXX: (2004-10-08) Brad Bollenbach: Should be the real owner ID
        dateverified=now,
        verifiedbyID=1,
        lastmodified=now,
        lastmodifiedbyID=1,
        **kw)
    product_infested = BugProductInfestationAddedEvent(
        Bug.get(context.context.bug), bpi)
    notify(product_infested)
    return bpi


def BugPackageInfestationFactory(context, **kw):
    now = datetime.utcnow()
    bpi = BugPackageInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=now,
        creatorID=1, # XXX: (2004-10-11) Brad Bollenbach: Should be the real owner ID
        dateverified=now,
        verifiedbyID=1,
        lastmodified=now,
        lastmodifiedbyID=1,
        **kw)
    package_infested = BugPackageInfestationAddedEvent(
        Bug.get(context.context.bug), bpi)
    notify(package_infested)
    return bpi

