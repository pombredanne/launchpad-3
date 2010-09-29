# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for the update-bugzilla-remote-components cronscript"""

__metaclass__ = type
__all__ = [
    'BugzillaRemoteComponentFinder',
    'BugzillaComponentScraper',
    ]

import re
from StringIO import StringIO
import urllib
from urllib2 import (
        HTTPError,
        urlopen,
        )
from BeautifulSoup import BeautifulSoup
from canonical.launchpad.scripts.logger import log as default_log


class BugzillaRemoteComponentScraper:
    """Scrapes Bugzilla query.cgi page for lists of products and components"""

    re_cpts = re.compile(r'cpts\[(\d+)\] = \[(.*)\]')
    re_vers = re.compile(r'vers\[(\d+)\] = \[(.*)\]')

    def __init__(self, bzurl):
        self.products = {}

        # TODO:  Hack!!  This should be fixed in sampledata
        if (bzurl == "http://bugzilla.gnome.org/bugs" or
            bzurl == "http://bugzilla.gnome.org/"):
            bzurl = "http://bugzilla.gnome.org"
        elif (bzurl == "https://bugzilla.mozilla.org/"):
            bzurl = " https://bugzilla.mozilla.org"

        #TODO: All the sampledata urls are failing, just force it to fdo for now
        bzurl = "https://bugzilla.freedesktop.org"
        self.url = "%s/query.cgi?format=advanced" %(bzurl)

    def _getPage(self, url):
        return urlopen(url).read()

    def dictFromCSV(self, line):
        items_dict = {}
        for item in line.split(","):
            item = item.strip()
            item = item.replace("'", "")
            item = item.replace("\\", "")
            items_dict[item] = {
                'name': item,
                }
        return items_dict

    def parsePage(self, page):
        try:
            body = self._getPage(self.url)
            soup = BeautifulSoup(body)
        except HTTPError, error:
            #self.logger.error("Error fetching %s: %s" % (url, error))
            return None

        # Load products into a list since Bugzilla references them by index number
        products = []
        for product in soup.find(
            name='select',
            onchange="doOnSelectProduct(2);").contents:
            if product.string != "\n":
                products.append({
                    'name': product.string,
                    'components': {},
                    'versions': None
                    })

        for script_text in soup.findAll(name="script"):
            if script_text is None or script_text.string is None:
                continue
            for line in script_text.string.split(";"):
                m = self.re_cpts.search(line)
                if m:
                    num = int(m.group(1))
                    products[num]['components'] = self.dictFromCSV(m.group(2))

                m = self.re_vers.search(line)
                if m:
                    num = int(m.group(1))
                    products[num]['versions'] = self.dictFromCSV(m.group(2))

        # Re-map list into dict for easier lookups
        for product in products:
            product_name = product['name']
            self.products[product_name] = product

class BugzillaRemoteComponentFinder:
    """Updates remote components for all Bugzillas registered in Launchpad"""

    def __init__(self, txn, logger=None):
        self.txn = txn
        self.logger = logger
        if logger is None:
            self.logger = default_log

    
