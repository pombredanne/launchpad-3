# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageFile, \
                                           ISourcePackageReleaseFile
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import BinaryPackageFileType, SourcePackageFileType 

class BinaryPackageFile(SQLBase):
    """A binary package to library link record."""

    implements(IBinaryPackageFile)

    _columns = [
        ForeignKey(name='binarypackage', foreignKey='BinaryPackage',
                   dbName='binarypackage'),
        ForeignKey(name='libraryfile', foreignKey='LibraryFileAlias',
                   dbName='libraryfile'),
        EnumCol('filetype', schema=BinaryPackageFileType),
    ]

class SourcePackageReleaseFile(SQLBase):
    """A source package release to library link record."""

    implements(ISourcePackageReleaseFile)

    _columns = [
        ForeignKey(name='sourcepackagerelease',
                   foreignKey='SourcePackageRelease',
                   dbName='sourcepackagerelease'),
        ForeignKey(name='libraryfile', foreignKey='LibraryFileAlias',
                   dbName='libraryfile'),
        EnumCol('filetype', schema=SourcePackageFileType),
    ]

