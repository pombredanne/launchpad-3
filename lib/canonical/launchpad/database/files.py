# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BinaryPackageFile', 'SourcePackageReleaseFile']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    BinaryPackageFileType, IBinaryPackageFile, ISourcePackageReleaseFile,
    SourcePackageFileType)


class BinaryPackageFile(SQLBase):
    """See IBinaryPackageFile """
    implements(IBinaryPackageFile)
    _table = 'BinaryPackageFile'

    binarypackagerelease = ForeignKey(dbName='binarypackagerelease',
                                      foreignKey='BinaryPackageRelease',
                                      notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)
    filetype = EnumCol(dbName='filetype',
                       schema=BinaryPackageFileType)


class SourcePackageReleaseFile(SQLBase):
    """See ISourcePackageFile"""

    implements(ISourcePackageReleaseFile)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    libraryfile = ForeignKey(foreignKey='LibraryFileAlias',
                             dbName='libraryfile')
    filetype = EnumCol(schema=SourcePackageFileType)

