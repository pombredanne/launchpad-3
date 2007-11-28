# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['LibraryFileContent', 'LibraryFileAlias', 'LibraryFileAliasSet']

from datetime import datetime, timedelta
import pytz

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces import (
    ILibraryFileContent, ILibraryFileAlias, ILibraryFileAliasSet)
from canonical.librarian.interfaces import ILibrarianClient, DownloadFailed
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from sqlobject import StringCol, ForeignKey, IntCol, SQLRelatedJoin, BoolCol


class LibraryFileContent(SQLBase):
    """A pointer to file content in the librarian."""

    implements(ILibraryFileContent)

    _table = 'LibraryFileContent'

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    datemirrored = UtcDateTimeCol(default=None)
    filesize = IntCol(notNull=True)
    sha1 = StringCol(notNull=True)
    md5 = StringCol()
    deleted = BoolCol(notNull=True, default=False)


class LibraryFileAlias(SQLBase):
    """A filename and mimetype that we can serve some given content with."""

    implements(ILibraryFileAlias)

    _table = 'LibraryFileAlias'
    date_created = UtcDateTimeCol(notNull=False, default=DEFAULT)
    content = ForeignKey(
            foreignKey='LibraryFileContent', dbName='content', notNull=True,
            )
    filename = StringCol(notNull=True)
    mimetype = StringCol(notNull=True)
    expires = UtcDateTimeCol(notNull=False, default=None)
    last_accessed = UtcDateTimeCol(notNull=True, default=DEFAULT)

    products = SQLRelatedJoin('ProductRelease', joinColumn='libraryfile',
                           otherColumn='productrelease',
                           intermediateTable='ProductReleaseFile')

    sourcepackages = SQLRelatedJoin('SourcePackageRelease',
                                 joinColumn='libraryfile',
                                 otherColumn='sourcepackagerelease',
                                 intermediateTable='SourcePackageReleaseFile')

    @property
    def http_url(self):
        """See ILibraryFileAlias.http_url"""
        return getUtility(ILibrarianClient).getURLForAlias(self.id)

    @property
    def https_url(self):
        """See ILibraryFileAlias.https_url"""
        url = self.http_url
        if url is None:
            return url
        return url.replace('http', 'https', 1)

    def getURL(self):
        """See ILibraryFileAlias.getURL"""
        if config.launchpad.vhosts.use_https:
            return self.https_url
        else:
            return self.http_url

    _datafile = None

    def open(self):
        client = getUtility(ILibrarianClient)
        self._datafile = client.getFileByAlias(self.id)
        if self._datafile is None:
            raise DownloadFailed(
                    "Unable to retrieve LibraryFileAlias %d" % self.id
                    )

    def read(self, chunksize=None):
        """See ILibraryFileAlias.read"""
        if not self._datafile:
            if chunksize is not None:
                raise RuntimeError("Can't combine autoopen with chunksize")
            self.open()
            autoopen = True
        else:
            autoopen = False

        if chunksize is None:
            rv = self._datafile.read()
            if autoopen:
                self.close()
            return rv
        else:
            return self._datafile.read(chunksize)

    def close(self):
        self._datafile.close()
        self._datafile = None

    def updateLastAccessed(self):
        """Update last_accessed if it has not been updated recently.

        This method relies on the system clock being vaguely sane, but
        does not cause real harm if this is not the case.
        """
        # XXX: stub 2007-04-10 Bug=86171: Feature disabled due to.
        return

        # Update last_accessed no more than once every 6 hours.
        precision = timedelta(hours=6)
        UTC = pytz.timezone('UTC')
        now = datetime.now(UTC)
        if self.last_accessed + precision < now:
            self.last_accessed = UTC_NOW

    products = SQLRelatedJoin('ProductRelease', joinColumn='libraryfile',
                           otherColumn='productrelease',
                           intermediateTable='ProductReleaseFile')

    sourcepackages = SQLRelatedJoin('SourcePackageRelease',
                                 joinColumn='libraryfile',
                                 otherColumn='sourcepackagerelease',
                                 intermediateTable='SourcePackageReleaseFile')


class LibraryFileAliasSet(object):
    """Create and find LibraryFileAliases."""

    implements(ILibraryFileAliasSet)

    def create(self, name, size, file, contentType, expires=None, debugID=None):
        """See ILibraryFileAliasSet.create"""
        client = getUtility(ILibrarianClient)
        fid = client.addFile(name, size, file, contentType, expires, debugID)
        return LibraryFileAlias.get(fid)

    def __getitem__(self, key):
        """See ILibraryFileAliasSet.__getitem__"""
        return LibraryFileAlias.get(key)

    def findBySHA1(self, sha1):
        """See ILibraryFileAliasSet."""
        return LibraryFileAlias.select("""
            content = LibraryFileContent.id
            AND LibraryFileContent.sha1 = '%s'
            """ % sha1, clauseTables=['LibraryFileContent'])

