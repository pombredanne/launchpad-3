# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BinaryPackageFile', 'SourcePackageReleaseFile', 'DownloadURL']

from urllib2 import URLError

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IBinaryPackageFile, ISourcePackageReleaseFile, IDownloadURL, ISoyuzFile)

from canonical.librarian.interfaces import ILibrarianClient

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import (
    BinaryPackageFileType, SourcePackageFileType)


class DownloadURL:
    """See IDownloadURL."""
    implements(IDownloadURL)

    def __init__(self, filename, fileurl):
        self.filename = filename
        self.fileurl = fileurl

class SoyuzFile:
    """See ISoyuzFile."""
    @property
    def url(self):
        """See IBinaryPackageFile."""
        downloader = getUtility(ILibrarianClient)
        try:
            url = downloader.getURLForAlias(self.libraryfile.id)
        except URLError:
            # librarian not runnig or file not avaiable
            pass
        else:
            name = self.libraryfile.filename
            return DownloadURL(name, url)


class BinaryPackageFile(SQLBase, SoyuzFile):
    """See IBinaryPackageFile """
    implements(IBinaryPackageFile, ISoyuzFile)
    _table = 'BinaryPackageFile'

    binarypackagerelease = ForeignKey(dbName='binarypackagerelease',
                                      foreignKey='BinaryPackageRelease',
                                      notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)
    filetype = EnumCol(dbName='filetype',
                       schema=BinaryPackageFileType)


class SourcePackageReleaseFile(SQLBase, SoyuzFile):
    """See ISourcePackageFile"""

    implements(ISourcePackageReleaseFile, ISoyuzFile)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    libraryfile = ForeignKey(foreignKey='LibraryFileAlias',
                             dbName='libraryfile')
    filetype = EnumCol(schema=SourcePackageFileType)

