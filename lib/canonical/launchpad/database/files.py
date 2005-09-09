# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BinaryPackageFile', 'SourcePackageReleaseFile', 'DownloadURL']

from urllib2 import URLError

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IBinaryPackageFile, ISourcePackageReleaseFile, IDownloadURL)

from canonical.librarian.interfaces import ILibrarianClient

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import BinaryPackageFileType, SourcePackageFileType 


class BinaryPackageFile(SQLBase):
    """See IBinaryPackageFile """
    implements(IBinaryPackageFile)
    _table = 'BinaryPackageFile'

    binarypackagerelease = ForeignKey(dbName='binarypackagerelease',
                                      foreignKey='BinaryPackageRelease',
                                      notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFile', notNull=True)
    filetype = EnumCol(dbName='filetype',
                       schema=BinaryPackageFileType)

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


class SourcePackageReleaseFile(SQLBase):
    """See ISourcePackageFile"""

    implements(ISourcePackageReleaseFile)

    _columns = [
        ForeignKey(name='sourcepackagerelease',
                   foreignKey='SourcePackageRelease',
                   dbName='sourcepackagerelease'),
        ForeignKey(name='libraryfile', foreignKey='LibraryFileAlias',
                   dbName='libraryfile'),
        EnumCol('filetype', schema=SourcePackageFileType),
    ]

    @property
    def url(self):
        downloader = getUtility(ILibrarianClient)

        try:
            url = downloader.getURLForAlias(self.libraryfile.id)
        except URLError:
            # Librarian not running or file not available.
            pass
        else:
            name = self.libraryfile.filename
            return DownloadURL(name, url)
            
class DownloadURL:
    implements(IDownloadURL)

    def __init__(self, filename, fileurl):
        self.filename = filename
        self.fileurl = fileurl
