# Python imports
from sets import Set
from datetime import datetime

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema
from canonical.launchpad.interfaces import IPublishedPackage, \
                                           IPublishedPackageSet


class PublishedPackage(SQLBase):
    """See IPublishedPackage for details."""

    implements(IPublishedPackage)

    _table = 'PublishedPackageView'

    distribution = IntCol(immutable=True)
    distrorelease = IntCol(immutable=True)
    distroreleasename = StringCol(immutable=True)
    processorfamily = IntCol(immutable=True)
    processorfamilyname = StringCol(immutable=True)
    packagepublishingstatus = IntCol(immutable=True)
    component = StringCol(immutable=True)
    section = StringCol(immutable=True)
    binarypackage = IntCol(immutable=True)
    binarypackagename = StringCol(immutable=True)
    binarypackageshortdesc = StringCol(immutable=True)
    binarypackagedescription = StringCol(immutable=True)
    binarypackageversion = StringCol(immutable=True)
    build = IntCol(immutable=True)
    datebuilt = DateTimeCol(immutable=True)
    sourcepackagerelease = IntCol(immutable=True)
    sourcepackagereleaseversion = StringCol(immutable=True)
    sourcepackage = IntCol(immutable=True)
    sourcepackagename = StringCol(immutable=True)



class PublishedPackageSet(object):

    implements(IPublishedPackageSet)

    def __iter__(self):
        return iter(PublishedPackage.select())

    def query(self, name=None, text=None, distribution=None,
              distrorelease=None, distroarchrelease=None):
        querytxt = '1=1'
        if name:
            name = name.lower().strip()
            querytxt += " AND binarypackagename ILIKE %s" % quote(name+"%")
            querytxt += " AND binarypackagename = %s" % quote(name)
        if text:
            raise NotImplementedError, 'Need FTI on BinaryPackages'
        if distribution:
            querytxt += " AND distribution = %d" % distribution
        if distrorelease:
            querytxt += " AND distrorelease = %d" % distrorelease
        if distroarchrelease:
            querytxt += " AND distroarchrelease = %d" % distroarchrelease
        if text:
            text = text.lower().strip()
            querytxt += " AND binarypackagefti @@ ftq(%s)" % text
        return PublishedPackage.select(querytxt)



