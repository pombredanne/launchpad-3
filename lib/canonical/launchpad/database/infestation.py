"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""
from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugProductInfestationSet, \
                                           IBugPackageInfestationSet, \
                                           IBugProductInfestation, \
                                           IBugPackageInfestation

from canonical.launchpad.database.bugset import BugSetBase


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
    now = datetime.utcnow()
    return BugProductInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=now,
        creatorID=context.request.principal.id,
        dateverified=now,
        verifiedbyID=context.request.principal.id,
        lastmodified=now,
        lastmodifiedbyID=context.request.principal.id,
        **kw)

def BugPackageInfestationFactory(context, **kw):
    now = datetime.utcnow()
    return BugPackageInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=now,
        creatorID=context.request.principal.id,
        dateverified=now,
        verifiedbyID=context.request.principal.id,
        lastmodified=now,
        lastmodifiedbyID=context.request.principal.id,
        **kw)
