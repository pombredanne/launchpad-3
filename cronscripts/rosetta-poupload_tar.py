#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import urllib2
import logging
import sys
from optparse import OptionParser
from datetime import datetime

from canonical.lp import initZopeless
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.database import DistributionSet, \
    SourcePackageInDistroSet

_default_lock_file = '/var/lock/launchpad-po-tar-attach.lock'

class AttachProcess:
    """Attach the .po and .pot files of a set of tarballs into Rosetta."""

    def __init__(self, baseurl, catalog):
        self._tm = initZopeless()
        self.baseurl = baseurl
        self.catalog = catalog
        self.distributionset = DistributionSet()

    def commit(self):
        self._tm.commit()

    def abort(self):
        self._tm.abort()

    def prepareEntry(self, catalogentry):
        """Check that the catalogentry has the needed fields and return them.

        Do some checks to catalogentry to be sure we have all needed
        information in our database and returns the sourcepackage and
        distrorelease objects associated with that catalogentry.
        """

        # Check that we have the needed distribution.
        try:
            distribution = self.distributionset[catalogentry['Distribution']]
        except KeyError, key:
            if key == 'Distribution':
                # The 'Distribution' key is missing from the catalog entry.
                logger.error('The catalog file has an error')
            else:
                # We don't have this distribution in our database, print a
                # warning so we can add it later and return.
                logger.warning("Don't have the distribution %s in the "
                                "database" % catalogentry['Distribution'])
            return None, None

        # Check that we have the needed release for the current distribution
        try:
            release = distribution[catalogentry['Release']]
        except KeyError, key:
            if key == 'Release':
                # The 'Release' key is missing from the catalog entry.
                logger.error('The catalog file has an error')
            else:
                # We don't have this release for the current distribution in
                # our database, print a warning so we can add it later and
                # return.
                logger.warning("Don't have the release %s for the "
                                "distribution %s in the database" % (
                                catalogentry['Release'],
                                catalogentry['Distribution']))
            return None, None

        # We get the list of packages a distro/release has
        spids = SourcePackageInDistroSet(release)

        # And look for the concrete sourcepackage we are interested on.
        try:
            sourcepackage = spids[catalogentry['Source']].sourcepackage
        except KeyError, key:
            if key == 'Source':
                # The 'Source' key is missing from the catalog entry.
                logger.error('The catalog file has an error')
            else:
                # We don't have this sourcepackage in our database, print
                # a warning so we can add it later and return.
                logger.warning("Don't have the sourcepackage %s for the "
                                "release %s and the distribution %s in the "
                                "database" % (
                                catalogentry['Source'],
                                catalogentry['Release'],
                                catalogentry['Distribution']))
            return None, None

        # This is only a sanity check
        if sourcepackage is None:
            logger.warning("Don't have the sourcepackage %s for the release "
                            "%s and the distribution %s in the database" % (
                            catalogentry['Source'],
                            catalogentry['Release'],
                            catalogentry['Distribution']))
            return None, None

        # Finally, we check for a product associated with this sourcepackage.
        if sourcepackage.product is None:
            logger.warning("Don't know the product associated with the "
                            "sourcepackage %s for the release %s and the "
                            "distribution %s in the database" % (
                            catalogentry['Source'],
                            catalogentry['Release'],
                            catalogentry['Distribution']))
            return None, None

        # At this point, all checks are done for the info we need to
        # accept this potemplate.
        return sourcepackage, release

    def attachURI(self, uri, sourcepackage, release, version):
        """Attach a .tar.gz file at uri to a sourcepackage."""

        try:
            tarfile = urllib2.urlopen(uri)
        except KeyError, key:
            logger.error('The catalog file has an error')
            return None, None
        except urllib2.HTTPError, e:
            logger.error('Got an error fetching the file %s: %s' % (uri, e))
            return None, None

        logger.debug("%s attached to %s product" % (
                     uri, sourcepackage.product.displayname))

        # Request to attach all .pot and .po files to this product.
        return sourcepackage.product.attachTranslations(
            tarfile,
            release.name,
            sourcepackage.sourcepackagename,
            release,
            version,
            logger)

    def run(self):
        try:
            for entry in self.catalog:
                (sourcepackage, release) = self.prepareEntry(entry)

                if sourcepackage is None or release is None:
                    # Don't have the needed entries in the database, Ignore
                    # this entry.
                    continue

                try:
                    updated, added, errors = self.attachURI(
                        self.baseurl + entry['File'],
                        sourcepackage,
                        release,
                        entry['Version'])
                except KeyError, key:
                    if key == 'File' or key == 'Version':
                        # The 'File' key is missing from the catalog entry.
                        logger.error('The catalog file has an error')
                    continue

                if len(updated) > 0:
                    logger.info("Templates updated (%s):" % entry['File'])
                    for template in updated:
                        logger.info(template)

                if len(added) > 0:
                    logger.warning("Templates added (%s):" % entry['File'])
                    for template in added:
                        logger.warning(template)
                if len(errors) > 0:
                    logger.warning("Files with errors (%s):" % entry['File'])
                    for file in errors:
                        logger.warning(file)

                if len(updated) == 0 and len(added) == 0 and len(errors) == 0:
                    logger.warning("We did nothing with %s" % entry['File'])

                self.commit()
        except:
            # If we have any exception, we log it before terminating the
            # process.
            logger.error('We got an unexpected exception', exc_info = 1)
            self.abort()

def parseCatalog(catalog):
    """Parses the file catalog and returns a dictionary with its keys."""

    res = []
    entry = {}
    for line in catalog.readlines():
        if line.isspace():
            # Next record.
            res.append(entry)
            entry = {}
        else:
            (key, value) = line.split(':', 1)
            entry[key] = value.strip()
    if len(entry) > 0:
        res.append(entry)
    return res

def fetch_dates_list(archive_uri):
    uri = archive_uri + 'directories.txt'

    try:
        dates_file = urllib2.urlopen(uri)
    except urllib2.HTTPError, e:
        logger.error('Got an error fetching the file %s: %s' % (uri, e))
        lockfile.release()
        sys.exit(1)

    dates_list = []
    for line in dates_file.readlines():
        dates_list.append(line.strip())

    return dates_list


def parse_options():
    parser = OptionParser()
    parser.add_option("-v", "--verbose", dest="verbose",
        default=0, action="count",
        help="Displays extra information.")
    parser.add_option("-q", "--quiet", dest="quiet",
        default=0, action="count",
        help="Display less information.")
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file the script should use to lock the process.")
    parser.add_option("-a", "--archive", dest="archivepath",
        default="http://people.ubuntu.com/~lamont/translations/",
        help="The location of the archive from where get translations")

    (options, args) = parser.parse_args()

    return options

def main():

    dates_list = fetch_dates_list(options.archivepath)

    for date in dates_list:
        # XXX Carlos Perello Marin 2005/01/20 We should create a special method to
        # join URLs like os.path.join as Steve suggested me today at
        # #launchpad-dev
        workurl = "%s/%s/" % (options.archivepath, date)

        uri = workurl + 'translations.txt'

        try:
            catalogfile = urllib2.urlopen(uri)
        except urllib2.HTTPError, e:
            logger.error('Got an error fetching the file %s: %s' % (uri, e))
            continue

        catalog = parseCatalog(catalogfile)

        process = AttachProcess(workurl, catalog)

        process.run()

def setUpLogger():
    loglevel = logging.WARN

    for i in range(options.verbose):
        if loglevel == logging.INFO:
            loglevel = logging.DEBUG
        elif loglevel == logging.WARN:
            loglevel = logging.INFO
    for i in range(options.quiet):
        if loglevel == logging.WARN:
            loglevel = logging.ERROR
        elif loglevel == logging.ERROR:
            loglevel = logging.CRITICAL

    hdlr = logging.StreamHandler(strm=sys.stderr)
    hdlr.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(message)s'
        ))
    logger.addHandler(hdlr)
    logger.setLevel(loglevel)


if __name__ == '__main__':

    options = parse_options()

    # Get the global logger for this task.
    logger = logging.getLogger("potarattach")
    # customized the logger output.
    setUpLogger()

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(options.lockfilename, logger=logger)
    try:
        lockfile.acquire()
    except OSError:
        logger.info("lockfile %s already exists, exiting",
                    options.lockfilename)
        sys.exit(0)

    try:
        main()
    finally:
        # Release the lock so next planned task can be executed.
        lockfile.release()
