from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import quote
from canonical.launchpad.database import ProductReleaseFile, ProductRelease
from canonical.librarian.client import FileUploadClient
from canonical.lp import dbschema

import urlparse, urllib2

# FIXME: Hard-coded config!
librarianHost = 'macaroni.ubuntu.com'
librarianPort = '9090'


def extractVersionFromFilename(filename):
    # XXX: We import this here because hct imports a ridiculous number of
    # dependencies we don't want.
    from hct.util.path import version_ext
    return version_ext.search(filename).group(1)


class ProductReleaseImporter:
    def __init__(self, product):
        self.product = product

    def addURL(self, url):
        # fetch it, plonk it in the librarian
        # construct product release & product release file appropriately
        # raise exception on failure
        
        filename = urlparse.urlsplit(url)[2].split('/')[-1]
        existingFiles = ProductReleaseFile.select(
            'ProductReleaseFile.productrelease = ProductRelease.id '
            'AND ProductRelease.product = %d '
            'AND ProductReleaseFile.libraryfile = LibraryFileAlias.id '
            'AND LibraryFileAlias.filename = %s '
            % (self.product, quote(filename)),
            clauseTables=['ProductRelease', 'LibraryFileAlias']
        )
        
        if existingFiles.count():
            # We already have a file by this name for this product release.
            # We're done!
            return

        # Download the file directly into the librarian
        # FIXME: cope with web/ftp servers that don't give the size of files by
        #        first saving to a temporary file.
        file = urllib2.open(url)
        info = file.info()
        size = int(info['content-length'])
        librarian = FileUploadClient()
        librarian.connect(librarianHost, librarianPort)
        ids = librarian.addFile(filename, size, file, info.get('content-type'))
        aliasID = ids[1]

        # We need to construct a product release file.  Figure out if we need to
        # construct a product release as well.
        version = extractVersionFromFilename(filename)
        existingReleases = ProductRelease.selectBy(productID=product,
                                                   version=version)
        if existingReleases.count() == 0:
            # Yep, we do need to create a product release.
            # FIXME: We probably ought to use the last-modified-time reported by
            # the download, rather than just UTC_NOW.
            pr = ProductRelease(productID=product, datereleased=UTC_NOW,
                                version=version, ownerID=product.owner)
        else:
            # The db schema guarantees there cannot be more than one result
            pr = existingReleases[0]

        # Now create the release file
        ProductReleaseFile(productreleaseID=pr, libraryfile=aliasID, 
                           filetype=dbschema.UpstreamFileType.CODETARBALL)

        # ...and we're done!

    def getReleases(self):
        """returns iterable of ProductReleases associated with the product that
        have a NULL manifest"""
        return ProductRelease.select(
            'manifest IS NULL AND product = %d' % self.product
        )

    def getLastManifest(self):
        """Return the last manifest for this product, or None."""
        from sourcerer.deb.version import deb_cmp

        releases = list(ProductRelease.select(
            'manifest IS NOT NULL AND product = %d' % self.product
        ))
        if releases:
            releases.sort(lambda x,y: deb_cmp(x.version, y.version))
            return releases[-1].manifest
        else:
            return None

