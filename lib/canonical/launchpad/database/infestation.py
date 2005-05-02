# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad Bug-related Database Table Objects."""

__metaclass__ = type
__all__ = ['BugProductInfestation',
           'BugPackageInfestation',
           'BugProductInfestationSet',
           'BugPackageInfestationSet',
           'BugProductInfestationFactory',
           'BugPackageInfestationFactory'
           ]

from datetime import datetime

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol

from canonical.launchpad.interfaces import \
    IBugProductInfestationSet, IBugPackageInfestationSet, \
    IBugProductInfestation, IBugPackageInfestation

from canonical.launchpad.database.bugset import BugSetBase
from canonical.lp import dbschema
from canonical.lp.dbschema import EnumCol


class BugProductInfestation(SQLBase):
    implements(IBugProductInfestation)

    _table = 'BugProductInfestation'

    # field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    explicit = IntCol(notNull=True, default=False)
    productrelease = ForeignKey(dbName="productrelease",
        foreignKey='ProductRelease', notNull=False, default=None)
    infestationstatus = EnumCol(
        notNull=False, default=None, schema=dbschema.BugInfestationStatus)
    datecreated = DateTimeCol(notNull=True)
    creator = ForeignKey(dbName="creator", foreignKey='Person', notNull=True)
    dateverified = DateTimeCol(notNull=False)
    verifiedby = ForeignKey(
        dbName="verifiedby", foreignKey='Person', notNull=False, default=None)
    lastmodified = DateTimeCol(notNull=True)
    lastmodifiedby = ForeignKey(
        dbName="lastmodifiedby", foreignKey='Person', notNull=True)

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
    sourcepackagerelease = ForeignKey(dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease', notNull=True)
    infestationstatus = EnumCol(dbName='infestationstatus', notNull=True,
        schema=dbschema.BugInfestationStatus)
    datecreated = DateTimeCol(dbName='datecreated', notNull=True)
    creator = ForeignKey(dbName='creator', foreignKey='Person', notNull=True)
    dateverified = DateTimeCol(dbName='dateverified')
    verifiedby = ForeignKey(dbName='verifiedby', foreignKey='Person')
    lastmodified = DateTimeCol(dbName='lastmodified')
    lastmodifiedby = ForeignKey(dbName='lastmodifiedby', foreignKey='Person')

    # used for launchpad pages
    def title(self):
        title = 'Malone Bug #' + str(self.bug.id) + ' infests '
        title += self.sourcepackagerelease.name
        return title
    title = property(title)


class BugProductInfestationSet(BugSetBase):
    """A set for BugProductInfestation."""
    implements(IBugProductInfestationSet)
    table = BugProductInfestation

    def __getitem__(self, id):
        item = self.table.selectOne(self.table.q.id == id)
        if item is None:
            raise KeyError, id
        return item

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row


class BugPackageInfestationSet(BugSetBase):
    """A set for BugPackageInfestation."""

    implements(IBugPackageInfestationSet)

    table = BugPackageInfestation

    def __getitem__(self, id):
        item = self.table.selectOne(self.table.q.id == id)
        if item is None:
            raise KeyError, id
        return item

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

