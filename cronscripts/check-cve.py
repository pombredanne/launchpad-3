#!/usr/bin/env python

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""A cron script that updates the status and title of the CVERefs registered
in Launchpad."""

__metaclass__ = type

import re
import sys
import urllib2
import _pythonpath

from BeautifulSoup import BeautifulSoup

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.lp.dbschema import CVEState
from canonical.launchpad.interfaces import ICVERefSet
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad import scripts

_default_lock_file = '/var/lock/launchpad-checkcve.lock'

_cve_data_table_pat = re.compile('<table border=2 cellpadding=2>.*</table>',
    re.DOTALL)

versioncache = {}

class CVEServiceConnectError(Exception):
    """An exception for errors when connecting to the CVE server."""
    def __init__(self, url, error):
        self.url = url
        self.error = str(error)

    def __str__(self):
        return "%s: %s" % (self.url, self.error)


def parse_options():
    """Parse command line arguments."""
    parser = OptionParser()
    scripts.logger_options(parser)
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file used to lock this process.")

    (options, args) = parser.parse_args()

    return options

def check_one_cve(cve):
    """Check the state of a single CVE item."""
    log.info("Checking CVE-%s", cve.cveref)
    try:
        url = urllib2.urlopen(cve.url)
    except (urllib2.HTTPError, urllib2.URLError), val:
        log.error('Unable to connect for %s' % cve.cveref)
        return
    cvepage = url.read()
    # find the CVE description
    soup = BeautifulSoup(cvepage)
    description_node = soup.firstText('Description')
    if description_node is None:
        log.error("Unable to find Description: CVE-%s" % cve.cveref)
        return
    description = str(description_node.findNext('font').string)
    if not description:
        log.error("Unable to find a description for CVE-%s" % cve.cveref)
        return
    # find out if the CVE is a candidate or an entry
    try:
        title_status = soup.html.head.title.string[:3]
    except IndexError:
        log.error('Unable to find page title for CVE-%s' % cve.cveref)
        return
    if title_status == 'CAN':
        status = 'Candidate'
    elif title_status == 'CVE':
        status = 'Entry'
    else:
        log.error('Unknown status for %s' % cve.cveref)
        return
    # update the CVE if needed
    if status not in ['Candidate', 'Entry', 'Deprecated']:
        log.error('Unknown status: %r' % status)
        return
    newcvestate = CVEState.items[status.upper()]
    if cve.cvestate <> newcvestate:
        log.info('CVE-%s changed from %s to %s' % (cve.cveref,
            cve.cvestate.title, newcvestate.title))
        cve.cvestate = newcvestate
    if cve.title <> description:
        log.info('CVE-%s updated description.' % cve.cveref)
        cve.title = description
    return


def main():
    execute_zcml_for_scripts()
    txn = initZopeless()
    cverefset = getUtility(ICVERefSet)
    for cveref in cverefset:
        txn.begin()
        check_one_cve(cveref)
        txn.commit()


if __name__ == '__main__':
    options = parse_options()
    log = scripts.logger(options, "checkwatches")
    lockfile = LockFile(options.lockfilename, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info('Lockfile %s in use' % options.lockfilename)
        sys.exit(1)
    try:
        main()
    finally:
        lockfile.release()

