# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageFile, \
                                           ISourcePackageReleaseFile

class BinaryPackageFile(SQLBase):
    """A binary package to library link record."""

    implements(IBinaryPackageFile)

    _columns = [
        ForeignKey(name='binarypackage', foreignKey='Binarypackage', dbName='binarypackage'),
        ForeignKey(name='libraryfile', foreignKey='LibraryFileAlias', dbName='libraryfile'),
        IntCol('filetype'),
    ]

class SourcePackageReleaseFile(SQLBase):
    """A source package release to library link record."""

    implements(ISourcePackageReleaseFile)

    _columns = [
        ForeignKey(name='sourcepackagerelease', foreignKey='SourcePackageRelease', dbName='sourcepackagerelease'),
        ForeignKey(name='libraryfile', foreignKey='LibraryFileAlias', dbName='libraryfile'),
        IntCol('filetype'),
    ]

