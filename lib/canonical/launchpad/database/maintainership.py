# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from datetime import datetime

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import DateTimeCol, ForeignKey, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import \
        IMaintainership, IMaintainershipSet


__all__ = [
    'Maintainership',
    'MaintainershipSet'
    ]

class Maintainership(SQLBase):
    """A Maintainership."""

    implements(IMaintainership)

    _table = 'Maintainership'

    #
    # db field names
    #
    distribution = ForeignKey(foreignKey="Distribution",
                              dbName="distribution",
                              notNull=True)

    maintainer = ForeignKey(foreignKey="Person", dbName="maintainer",
                            notNull=True)

    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename',
                                   notNull=True)

class MaintainershipSet:

    implements(IMaintainershipSet)

    def __init__(self, distribution=None, distrorelease=None):
        self.title = "Launchpad Maintainers"
        if distribution is not None and distrorelease is not None:
            raise TypeError, 'May instantiate MaintainershipSet with distribution or distrorelease, not both'
        if distribution:
            self.distribution = distribution
            self.distrorelease = distribution.currentrelease
        elif distrorelease:
            self.distribution = distrorelease.distribution
            self.distrorelease = distrorelease
        else:
            self.distribution = None
            self.distrorelease = None
    # XXX sabdfl 24/03/2005 not yet completed

    def getByPersonID(self, personID, distribution=None):
        if distribution is None and self.distribution is not None:
            distribution = self.distribution
        querystr = "maintainer = %d" % personID
        if distribution:
            querystr += " AND "
            querystr += "distribution = %d" % distribution.id
        return Maintainership.select(querystr,
                                    orderBy='SourcePackageName')

    def get(self, distribution, sourcepackagename):
        querystr = "sourcepackagename = %d AND distribution = %d" % (
                    sourcepackagename.id, distribution.id )
        ret = Maintainership.select(querystr)
        if ret.count() == 0:
            return None
        assert ret.count() == 1
        return ret[0].maintainer

