# Zope imports
from zope.interface import implements
from zope.exceptions import NotFoundError

# SQLObject/SQLBase
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, IntCol, DateTimeCol, MultipleJoin

from canonical.database.sqlbase import SQLBase, quote

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageName
from canonical.launchpad.interfaces import ISourcePackageNameSet

#
#
#

class SourcePackageName(SQLBase):
    implements(ISourcePackageName)
    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True, unique=True,
        alternateID=True)

    potemplates = MultipleJoin('POTemplate', joinColumn='sourcepackagename')

    def __unicode__(self):
        return self.name

    def _ensure(klass, name):
        try:
            return klass.byName(name)
        except SQLObjectNotFound:
            return klass(name=name)

    ensure = classmethod(_ensure)

class SourcePackageNameSet(object):
    implements(ISourcePackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name

    def __iter__(self):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        for sourcepackagename in SourcePackageName.select():
            yield sourcepackagename

    def get(self, sourcepackagenameid):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.get(sourcepackagenameid)
        except SQLObjectNotFound:
            raise NotFoundError(sourcepackagenameid)

    def findByName(self, name):
        """Find sourcepackagenames by its name or part of it"""
        name = name.replace('%', '%%')
        query = ('name ILIKE %s'
                 %quote('%%' +name+ '%%'))
        return SourcePackageName.select(query)
