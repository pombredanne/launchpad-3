import os
import urlparse
import urllib2

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import quote, SQLBase
from canonical.launchpad.database import ProductReleaseFile, ProductRelease
from canonical.launchpad.database import ProductSeries
from canonical.librarian.client import FileUploadClient
from canonical.lp import dbschema


librarianHost = os.environ.get('LIBRARIAN_HOST', 'macaroni.ubuntu.com')
librarianPort = 9090


class ProductReleaseImporter:
    def __init__(self, product):
        self.product = product

    def addURL(self, url):
        """Fetch a URL of a product release, and put it in Launchpad.

        If this release isn't already in the system, this will:
            - put the file in the librarian;
            - create a product release in the db, if necessary;
            - and create a product file release.
        """
        filename = urlparse.urlsplit(url)[2].split('/')[-1]
        if self._alreadyImported(filename):
            # We're done!
            return

        # Download the file directly into the librarian
        aliasID = self._downloadIntoLibrarian(url, filename)

        # Get a product release object for this release -- constructing it if
        # necessary.
        pr = self._ensureProductRelease(filename)

        # Now create the release file
        ProductReleaseFile(productreleaseID=pr.id, libraryfileID=aliasID,
                           filetype=int(dbschema.UpstreamFileType.CODETARBALL))

        # ...and we're done!

    def _ensureProductRelease(self, filename):
        from cscvs.dircompare.path import split_version, name
        version = split_version(name(filename))[1]
        series = version.split('.')[0]
        existingSeries = ProductSeries.selectOneBy(productID=self.product.id,
            name=series)
        if existingSeries is None:
            # Create a new series using the first part of the version number
            # as the series name:
            ps = ProductSeries(productID=self.product.id, name=series,
                summary=version, ownerID=self.product.owner.id)
            # Yep, we do need to create a product release.
            # FIXME: We probably ought to use the last-modified-time reported
            # by the download, rather than just UTC_NOW.
            pr = ProductRelease(productseriesID=ps.id, datereleased=UTC_NOW,
                version=version, ownerID=self.product.owner.id)
        else:
            # The db schema guarantees there cannot be more than one result
            ps = existingSeries
            existingRelease = ProductRelease.selectOneBy(
                    productseriesID=ps.id, version=version)
            if existingRelease is None:
                # Yep, we do need to create a product release.
                # FIXME: We probably ought to use the last-modified-time
                # reported by the download, rather than just UTC_NOW.
                pr = ProductRelease(productID=self.product.id,
                    datereleased=UTC_NOW, version=version,
                    ownerID=self.product.owner.id)
            else:
                # The db schema guarantees there cannot be more than one result
                pr = existingRelease
        return pr

    def _downloadIntoLibrarian(self, url, filename):
        """Download a URL, and upload it directly into the librarian.

        Returns the library alias ID of the file.
        """
        # XXX: dsilvers 2004-12-14:
        #      Cope with web/ftp servers that don't give
        #      the size of files by first saving to a temporary file.
        # XXX: ddaa 2005-01-26:
        #      This isn't at all specific to this importer, and probably
        #      belongs as a utility in the librarian code somewhere.
        file = urllib2.urlopen(url)
        info = file.info()
        size = int(info['content-length'])
        librarian = FileUploadClient()
        librarian.connect(librarianHost, librarianPort)
        ids = librarian.addFile(filename, size, file, info.get('content-type'))
        aliasID = ids[1]

        # XXX: Andrew Bennetts 2005-01-27:
        #      Awful hack -- the librarian's updated the database, so we need
        #      to reset our connection so that we can see it.
        SQLBase._connection.rollback()
        SQLBase._connection.begin()
        return aliasID

    def _alreadyImported(self, filename):
        """Do we already have a file by this name for this product?"""
        existingFiles = ProductReleaseFile.select(
            'ProductReleaseFile.productrelease = ProductRelease.id '
            'AND ProductRelease.product = %d '
            'AND ProductReleaseFile.libraryfile = LibraryFileAlias.id '
            'AND LibraryFileAlias.filename = %s '
            % (self.product, quote(filename)),
            clauseTables=['ProductRelease', 'LibraryFileAlias']
        )

        return bool(existingFiles.count())

    def getReleases(self):
        """returns iterable of ProductReleases associated with the product that
        have a NULL manifest"""
        return ProductRelease.select(
            'manifest IS NULL AND product = %d' % self.product
        )

    def getLastManifest(self):
        """Return the last manifest for this product, or None."""
        from canonical.archivepublisher.debversion import deb_cmp

        releases = list(ProductRelease.select(
            'manifest IS NOT NULL AND product = %d' % self.product
        ))
        if releases:
            releases.sort(lambda x,y: deb_cmp(x.version, y.version))
            return releases[-1].manifest
        else:
            return None

