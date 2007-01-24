#!/usr/bin/env python

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""A cron script that fetches the latest database of CVE details and ensures
that all of the known CVE's are fully registered in Launchpad."""

__metaclass__ = type

import sys
import urllib2
import gzip
import StringIO
import timing
import _pythonpath

from optparse import OptionParser

import cElementTree

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.cveimport import CVEDB_NS, update_one_cve

_default_lock_file = '/var/lock/launchpad-update-cve.lock'

def parse_options():
    """Parse command line arguments."""
    parser = OptionParser()
    logger_options(parser)
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file used to lock this process.")
    parser.add_option("-f", "--cvefile", dest="cvefile",
        default=None, help="An XML file containing the CVE database.")
    parser.add_option("-u", "--cveurl", dest="cveurl",
        default=config.cveupdater.cve_db_url,
        help="The URL for the gzipped XML CVE database.")

    (options, args) = parser.parse_args()

    return options


def main(log, cvefile=None, cveurl=None):
    log.info('Initializing...')
    execute_zcml_for_scripts()
    txn = initZopeless(dbuser=config.cveupdater.dbuser)
    if cvefile is not None:
        try:
            cve_db = open(cvefile, 'r').read()
        except IOError:
            log.error('Unable to open CVE database in %s' % cvefile)
            return 1
    elif cveurl is not None:
        log.info("Downloading CVE database from %s..." % cveurl)
        try:
            url = urllib2.urlopen(cveurl)
        except (urllib2.HTTPError, urllib2.URLError), val:
            log.error('Unable to connect for CVE database %s' % cveurl)
            return 1
        cve_db_gz = url.read()
        log.info("%d bytes downloaded." % len(cve_db_gz))
        cve_db = gzip.GzipFile(fileobj=StringIO.StringIO(cve_db_gz)).read()
    else:
        log.error('No CVE database file or URL given.')
        return 1
    # start analysing the data
    timing.start()
    log.info("Processing CVE XML...")
    dom = cElementTree.fromstring(cve_db)
    items = dom.findall(CVEDB_NS + 'item')
    log.info("Updating database...")
    for item in items:
        txn.begin()
        update_one_cve(item, log)
        txn.commit()
    timing.finish()
    log.info('%d seconds to update database.' % timing.seconds())


if __name__ == '__main__':
    options = parse_options()
    log = logger(options, "updatecve")
    lockfile = GlobalLock(options.lockfilename, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.error('Lockfile %s in use' % options.lockfilename)
        sys.exit(1)
    try:
        main(log, options.cvefile, options.cveurl)
    finally:
        lockfile.release()

