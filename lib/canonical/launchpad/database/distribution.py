
# Python imports
from sets import Set
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func

from canonical.database.sqlbase import SQLBase, quote
from canonical.launchpad.database.bugassignment import SourcePackageBugAssignment
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistribution
from canonical.launchpad.interfaces import IDistributionSet

__all__ = ['Distribution', 'DistributionSet']

class Distribution(SQLBase):

    implements(IDistribution)

    _table = 'Distribution'
    _defaultOrder='name'
    _columns = [
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        StringCol('domainname', dbName='domainname'),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
                   notNull=True)
        ]

    releases = MultipleJoin('DistroRelease', 
                            joinColumn='distribution') 
    role_users = MultipleJoin('DistributionRole', 
                              joinColumn='distribution')
   
    def getRelease(self, name):
        for release in self.releases:
            if release.name == name:
                return release
        raise IndexError, ('No distribution release called', name)

    def bugCounter(self):
        counts = []

        clauseTables = ("VSourcePackageInDistro",
                        "SourcePackage")
        severities = [
            dbschema.BugAssignmentStatus.NEW,
            dbschema.BugAssignmentStatus.ACCEPTED,
            dbschema.BugAssignmentStatus.REJECTED,
            dbschema.BugAssignmentStatus.FIXED]

        query = ("sourcepackagebugassignment.sourcepackage = sourcepackage.id AND "
                 "sourcepackage.sourcepackagename = vsourcepackageindistro.sourcepackagename AND "
                 "vsourcepackageindistro.distro = %s AND "
                 "sourcepackagebugassignment.bugstatus = %i")

        for severity in severities:
            query = query %(quote(self.id), severity)
            count = SourcePackageBugAssignment.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        return counts

    bugCounter = property(bugCounter)


class DistributionSet(object):
    """This class is to deal with Distribution related stuff"""

    implements(IDistributionSet)

    def getDistros(self):
        """Returns all Distributions available on the datasbase"""
        return Distribution.select()

    def getDistrosCounter(self):
        """Returns the number of Distributions available"""
        return Distribution.select().count()

    def getDistribution(self, name):
        """Returns a Distribution with name = name"""
        return Distribution.selectBy(name=name)[0]

