#!/usr/bin/env python
"""Dyson.

Scan FTP and HTTP sites specified for each ProductSeries in the database
to identify files and create new ProductRelease records for them.
"""

import os
import mimetypes

from urllib import urlretrieve
from urlparse import urlsplit
from optparse import OptionParser

from zope.component import getUtility

from canonical.dyson.hose import Hose
from canonical.dyson.filter import Cache
from canonical.launchpad.interfaces import IProductSet, IProductReleaseSet
from canonical.librarian.interfaces import IFileUploadClient
from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)

from hct.util import path


def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)
    (options, args) = parser.parse_args()

    global log
    log = logger(options, "dyson")
    ztm = initZopeless(dbuser=config.dyson.dbuser, implicitBegin=False)

    cache = Cache(config.dyson.cache_path, log_parent=log)
    try:
        for product_name, filters in get_filters(ztm):
            hose = Hose(filters, cache)
            for series_name, url in hose:
                if series_name is not None:
                    new_release(ztm, product_name, series_name, url)
                else:
                    log.warning("File in %s found that matched no glob: %s",
                                product_name, url)
    finally:
        cache.save()

def get_filters(ztm):
    """Build the list of products and filters.

    Returns a list of (product_name, filters) for each product in the database,
    where the filter keys are series names.
    """
    todo = []

    ztm.begin()
    products = getUtility(IProductSet)
    for product in products:
        filters = {}

        for series in product.serieslist:
            if series.releasefileglob is None or series.releasefileglob == "":
                continue
            else:
                releasefileglob = series.releasefileglob

            if series.releaseroot is None or series.releaseroot == "":
                if product.releaseroot is None or product.releaseroot == "":
                    continue
                else:
                    releaseroot = product.releaseroot
            else:
                releaseroot = series.releaseroot

            filters[series.name] = (releaseroot, releasefileglob)

        if not len(filters):
            continue

        log.info("%s has %d series with information", product.name,
                 len(filters))

        todo.append((product.name, filters))
    ztm.abort()

    return todo

def new_release(ztm, product_name, series_name, url):
    """Create a new ProductRelease.

    Downloads the file and creates a new ProductRelease associated with
    the series.
    """
    filename = urlsplit(url)[2]
    slash = filename.rfind("/")
    if slash != -1:
        filename = filename[slash + 1:]
    log.debug("Filename portion is %s", filename)

    version = path.split_version(path.name(filename))[1]
    log.debug("Version is %s", version)
    if version is None:
        log.error("Unable to parse version from %s", url)
        return

    (mimetype, encoding) = mimetypes.guess_type(url)
    log.debug("Mime Type is %s", mimetype)
    if mimetype is None:
        mimetype = "application/octet-stream"

    log.debug("Downloading %s", url)
    try:
        (local, headers) = urlretrieve(url)
        stat = os.stat(local)
    except IOError:
        log.error("Download of %s failed, can't create release")
        return
    except OSError:
        log.error("Unable to stat downloaded file, can't create release")
        return

    open_file = open(local, "r")
    os.unlink(local)
    try:
        ztm.begin()
        try:
            product = getUtility(IProductSet)[product_name]
            series = product.getSeries(series_name)
            log.info("Creating new release %s for %s %s",
                     version, product.name, series.name)

            release = getUtility(IProductReleaseSet).\
                      new(version, series, product.owner)
            log.debug("Created ProductRelease %d", release.id)

            alias_id = getUtility(IFileUploadClient).\
                       addFile(filename, stat.st_size, open_file, mimetype)
            log.debug("Created LibraryFileAlias %d", alias_id)

            release.addFileAlias(alias_id)
            ztm.commit()
        except:
            ztm.abort()
            raise
    finally:
        open_file.close()


if __name__ == "__main__":
    execute_zcml_for_scripts()

    main()
