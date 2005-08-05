#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

import sys
import urllib2
from xml.dom import minidom
import _pythonpath

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.lp.dbschema import CVEState
from canonical.launchpad.interfaces import ICVERefSet
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad import scripts

_default_lock_file = '/var/lock/launchpad-checkcve.lock'

versioncache = {}

class CVEServiceConnectError(Exception):
    """An exception for errors when connecting to the CVE server."""
    def __init__(self, url, error):
        self.url = url
        self.error = str(error)

    def __str__(self):
        return "%s: %s" % (self.url, self.error)


def parse_options():
    parser = OptionParser()
    scripts.logger_options(parser)
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file used to lock this process.")

    (options, args) = parser.parse_args()

    return options

def find_element_with_value(node, value):
    if node.nodeValue == value:
        return node
    for child in node.childNodes:
        candidate = find_element_with_value(child, value)
        if candidate is not None:
            return candidate
    return None

def check_one_cve(cve):
    log.info("Checking CVE-%s", cve.cveref)
    #try:
    #    url = urllib2.urlopen(cve.url)
    #except (urllib2.HTTPError, urllib2.URLError), val:
    #    raise CVEServiceConnectError(cve.url, val)
    #ret = url.read()
    ret = """
<div style="margin-left:4em">
  <table border="0" cellspacing="0" cellpadding="5">

    <tr valign="top">
      <td align="right"><b>CVE Name:</b></td>
      <td>CVE-1999-0067</td>
    </tr>
    <tr valign="top">
      <td align="right"><b>Status:</b></td>
      <td>Entry</td>

    </tr>
    <tr valign="top">
      <td align="right"><b>Description:</b></td>
      <td>CGI phf program allows remote command execution through shell metacharacters.</td>
    </tr>
    <tr valign="top">
      <td align="right"><b>References:</b></td>

      <td>&#8226; CERT:CA-96.06.cgi_example_code<br />
&#8226; XF:http-cgi-phf<br />
&#8226; BID:629<br />
&#8226; OSVDB:136      </td>
    </tr>
  </table>

  </div>
"""
    document = minidom.parseString(ret)
    statuslabelnode = find_element_with_value(document, 'Status:')
    if statuslabelnode is None:
        log.error("Unable to find Status: CVE-%s" % cve.cveref)
        return
    tr = statuslabelnode.parentNode.parentNode.parentNode
    status = tr.getElementsByTagName('td')[1].firstChild.nodeValue
    descriptionlabelnode = find_element_with_value(document, 'Description:')
    if descriptionlabelnode is None:
        log.error("Unable to find Description: CVE-%s" % cve.cveref)
        return
    tr = descriptionlabelnode.parentNode.parentNode.parentNode
    description = tr.getElementsByTagName('td')[1].firstChild.nodeValue
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

