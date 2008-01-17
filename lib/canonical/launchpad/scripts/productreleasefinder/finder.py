# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductReleaseFinder'
    ]

import os
import mimetypes
import urlparse
import urllib

from cscvs.dircompare import path

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IProductSet, IProductReleaseSet, UpstreamFileType)
from canonical.launchpad.validators.version import sane_version
from canonical.launchpad.scripts.productreleasefinder.hose import Hose
from canonical.launchpad.scripts.productreleasefinder.filter import (
    FilterPattern)


class ProductReleaseFinder:

    def __init__(self, ztm, log):
        self.ztm = ztm
        self.log = log

    def findReleases(self):
        """Scan for new releases in all products."""
        for product_name, filters in self.getFilters():
            self.handleProduct(product_name, filters)

    def getFilters(self):
        """Build the list of products and filters.

        Returns a list of (product_name, filters) for each product in
        the database, where the filter keys are series names.
        """
        todo = []

        self.ztm.begin()
        products = getUtility(IProductSet)
        for product in products:
            filters = []

            for series in product.serieses:
                if not series.releasefileglob:
                    continue

                filters.append(FilterPattern(series.name,
                                             series.releasefileglob))

            if not len(filters):
                continue

            self.log.info("%s has %d series with information", product.name,
                             len(filters))

            todo.append((product.name, filters))
        self.ztm.abort()

        return todo

    def handleProduct(self, product_name, filters):
        """Scan for tarballs and create ProductReleases for the given product.
        """
        hose = Hose(filters, log_parent=self.log)
        for series_name, url in hose:
            if series_name is not None:
                try:
                    self.handleRelease(product_name, series_name, url)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    self.log.exception("Could not successfully process "
                                       "URL %s for %s/%s",
                                       url, product_name, series_name)
            else:
                self.log.debug("File in %s found that matched no glob: %s",
                               product_name, url)

    def hasReleaseTarball(self, product_name, series_name, release_name):
        """Return True if we have a tarball for the given product release."""
        has_tarball = False
        self.ztm.begin()
        try:
            product = getUtility(IProductSet).getByName(product_name)
            if product is not None:
                series = product.getSeries(series_name)
                if series is not None:
                    release = series.getRelease(release_name)
                    if release is not None:
                        for fileinfo in release.files:
                            if fileinfo.filetype == UpstreamFileType.CODETARBALL:
                                has_tarball = True
                                break
        finally:
            self.ztm.abort()
        return has_tarball

    def addReleaseTarball(self, product_name, series_name, release_name,
                          filename, size, file, content_type):
        """Create a ProductRelease (if needed), and attach tarball"""
        # Get the series.
        self.ztm.begin()
        try:
            product = getUtility(IProductSet).getByName(product_name)
            series = product.getSeries(series_name)
            release = series.getRelease(release_name)
            if release is None:
                release = getUtility(IProductReleaseSet).new(
                    owner=product.owner,
                    productseries=series,
                    version=release_name)
                self.log.info("Created new release %s for %s/%s",
                              release_name, product_name, series_name)

            # If we already have a code tarball, stop here.
            for fileinfo in release.files:
                if fileinfo.filetype == UpstreamFileType.CODETARBALL:
                    self.log.debug("%s/%s/%s already has a code tarball",
                                   product_name, series_name, release_name)
                    self.ztm.abort()
                    return

            alias = getUtility(ILibraryFileAliasSet).create(
                filename, size, file, content_type)
            release.addFileAlias(alias, signature=None, uploader=product.owner)
            self.ztm.commit()
        except:
            self.ztm.abort()
            raise

    def handleRelease(self, product_name, series_name, url):
        """If the given URL looks like a release tarball, download it
        and create a corresponding ProductRelease."""
        filename = urlparse.urlsplit(url)[2]
        slash = filename.rfind("/")
        if slash != -1:
            filename = filename[slash+1:]
        self.log.debug("Filename portion is %s", filename)

        version = path.split_version(path.name(filename))[1]

        if version is None:
            self.log.error("Unable to parse version from %s", url)
            return

        # Tarballs pulled from a Debian-style archive often have
        # ".orig" appended to the version number.  We don't want this.
        if version.endswith('.orig'):
            version = version[:-len('.orig')]

        self.log.debug("Version is %s", version)
        if not sane_version(version):
            self.log.error("Version number '%s' for '%s' is not sane",
                           version, url)
            return

        if self.hasReleaseTarball(product_name, series_name, version):
            self.log.debug("Already have a tarball for release %s", version)
            return

        mimetype, encoding = mimetypes.guess_type(url)
        self.log.debug("Mime type is %s", mimetype)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.log.info("Downloading %s", url)
        try:
            local, headers = urllib.urlretrieve(url)
            stat = os.stat(local)
        except IOError:
            self.log.error("Download of %s failed", url)
            raise
        except OSError:
            self.log.error("Unable to stat downloaded file")
            raise

        fp = open(local, 'r')
        os.unlink(local)
        self.addReleaseTarball(product_name, series_name, version,
                               filename, stat.st_size, fp, mimetype)
