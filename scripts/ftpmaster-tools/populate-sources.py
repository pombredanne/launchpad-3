#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type


import _pythonpath

import sys
import apt_pkg
import urllib
import os
import gzip
from optparse import OptionParser

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.librarian.utils import copy_and_close
from canonical.lp import (
    initZopeless, READ_COMMITTED_ISOLATION)
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket)


class SourceIndexLocation:
    """Handler to Archive Indexexes"""

    def __init__(self, distrorelease, component, log,
                 target_filename="Sources.gz",
                 archive_url = 'http://archive.ubuntu.com/ubuntu/'):
        """Store given attributes and populate the instance.

        self.target stores the file URL and self.location stores the
        path where it will be download/uncompresed.
        """
        self.distrorelease = distrorelease
        self.component = component
        self.log = log
        self.archive_url = archive_url
        self.target_filename = target_filename

        dist_name = distrorelease.name
        comp_name = component.name
        path = os.path.join(
            'dists', dist_name, comp_name, 'source', self.target_filename)
        self.target = urllib.basejoin(self.archive_url, path)

        self.location = "%s_%s" % (self.distrorelease.name,
                                   self.component.name)

    def _uncompress(self, filename):
        """Wrapper to available file uncompressors."""
        index_processor_map = {
            'Sources': self._plain,
            'Sources.gz': self._gunzip,
            'Sources.bz2': self._bunzip2
            }
        processor = index_processor_map[self.target_filename]
        processor(filename)

    def _plain(self, filename):
        """Copy downloaded file to end location."""
        self.log.debug("Copying: %s" % filename)
        end_file = open(self.location, "w")
        copy_and_close(gzip_file, end_file)

    def _gunzip(self, filename):
        """Gunzip index file """
        self.log.debug("Uncompressing: %s" % filename)
        gzip_file = gzip.GzipFile(filename=filename)
        end_file = open(self.location, "w")
        copy_and_close(gzip_file, end_file)

    def _bunzip2(self, filename):
        """Bunzip file into the end location."""
        raise NotImplementedError

    def _download(self):
        """Download and uncompress souce index.

        Skip the procedure if the content is already present.
        """
        if os.path.exists(self.location):
            self.log.info("Skipping: %s" % self.target)
            return

        filename = None
        try:
            self.log.info("Downloading: %s" % self.target)
            filename, info = urllib.urlretrieve(self.target)
            self._uncompress(filename)
        finally:
            if filename is not None:
                self.log.debug("Removing: %s" % filename)
                os.unlink(filename)

    def extractInfo(self):
        """Return the apt_pkg parsed information.

        Return a dictionary containing:
        key -> sourcename
        value -> apt_pkg correspondent section encapsulated into a dictionary.

        Download the index file if necessary.
        """
        self._download()
        extracted_info = {}
        self.log.info("Processing: %s" % self.location)

        sources = apt_pkg.ParseTagFile(open(self.location))
        while sources.Step():
            src_tmp = dict(sources.Section)
            sourcename = src_tmp['Package']
            extracted_info[sourcename] = src_tmp

        return extracted_info


def updateInfo(distrorelease, pocket, log):
    """Scan all components of given distrorelease and update source data.

    Retrieve archive index information and update required information.
    """
    for component in distrorelease.components:
        # Encapsulate archive index information.
        sources = SourceIndexLocation(distrorelease, component, log)
        info = sources.extractInfo()

        # dismiss this step is index file is empty for this suite/component
        if not info.keys():
            log.error("Empty Archive Index for %s" % sources.target)
            continue

        # retrive all published sources in this suite/component
        spphs = distrorelease.getSourcePackagePublishing(
            status=PackagePublishingStatus.PUBLISHED,
            pocket=pocket, component=component)

        # cross LPDB and index information
        for spph in spphs:
            sourcename = spph.sourcepackagerelease.name
            log.debug(30 * "=")
            log.debug("LPDB: %s " % spph.sourcepackagerelease.title)
            try:
                log.debug("ARID: %s - %s" % (info[sourcename]['Package'],
                                              info[sourcename]['Version']))
            except KeyError:
                log.error("Not Found: %s" % spph.sourcepackagerelease.title)
            log.debug(30 * "=")


def main():
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")

    parser.add_option("-d", "--distribution", metavar="DISTRIBUTION",
                      action="store", dest="distribution", default='ubuntu',
                      help="Distribution name.")

    parser.add_option("-s", "--suite", metavar="SUITE", default=None,
                      action="store", dest="suite", help="Suite name.")

    options, args = parser.parse_args()

    log = logger(options, "populate-sources")

    log.debug("Initialising connection.")

    ztm = initZopeless(dbuser='lucille', isolation=READ_COMMITTED_ISOLATION)
    execute_zcml_for_scripts()
    apt_pkg.init()

    try:
        distribution = getUtility(IDistributionSet)[options.distribution]
    except NotFoundError, info:
        log.error(info)
        return 1

    if options.suite:
        try:
            distrorelease, pocket = distribution.getDistroReleaseAndPocket(
                options.suite)
        except NotFoundError, info:
            log.error(info)
            return 1
    else:
        distrorelease = distribution.currentrelease
        pocket = PackagePublishingPocket.RELEASE


    try:
        updateInfo(distrorelease, pocket, log)
    except Exception:
        log.debug("Aborting transaction.")
        ztm.abort()
        return 1

    if not options.dryrun:
        log.debug("Committing transaction")
        ztm.commit()
    else:
        log.debug("Dry-Run mode, aborting transaction.")
        ztm.abort()

    return 0

if __name__ == "__main__":
    sys.exit(main())
