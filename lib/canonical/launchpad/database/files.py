# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BinaryPackageFile', 'SourcePackageReleaseFile']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import \
    IBinaryPackageFile, ISourcePackageReleaseFile
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

