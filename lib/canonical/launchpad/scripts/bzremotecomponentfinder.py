# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for the update-bugzilla-remote-components cronscript"""

__metaclass__ = type
__all__ = [
    'BugzillaRemoteComponentFinder',
    'LaunchpadBugTracker',
    ]

import os
import sys
import re
import pycurl
import time

from StringIO import StringIO


class BugzillaRemoteComponentFinder:

    re_products_select = re.compile(r'<select name="product".*onchange="doOnSelectProduct\(2\);">(.*?)</select>', re.DOTALL)
    re_product = re.compile(r'<option value="(.*)">(.*)</option>')
    re_cpts = re.compile(r'cpts\[(\d+)\] = \[(.*)\]')
    re_vers = re.compile(r'vers\[(\d+)\] = \[(.*)\]')

    def __init__(self, bzurl):
        self.products = {}
        self.url = "%s/query.cgi?format=advanced" %(bzurl)

    def _getPage(self, url):
        # TODO: Switch from pycurl to BeautifulSoup, to match sourceforge script
        curl = pycurl.Curl()
        headers = StringIO()
        response = StringIO()

        print "Pulling from %s" %(url)

        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.HEADERFUNCTION, headers.write)
        curl.setopt(pycurl.WRITEFUNCTION, response.write)
        curl.setopt(pycurl.SSL_VERIFYPEER, False)

        curl.perform()
        curl.close()

        #print headers.getvalue()
        return response.getvalue()

    def parseProductListFromBugzillaSearchPage(self, body):
        products = []
        m = self.re_products_select.search(body)
        if not m:
            print "Error: No products found at %s" %(url)
            sys.exit(1)
        products_line = m.group(1)
        for line in products_line.split("\n"):
            m = self.re_product.search(line)
            if m:
                product = {
                    'name': m.group(1),
                    'components': {},
                    'versions': None
                    }
                products.append(product)
        return products

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

    def retrieveProducts(self):
        body = self._getPage(self.url)

        # Load products into a list since Bugzilla references them by index number
        products = self.parseProductListFromBugzillaSearchPage(body)

        for line in body.split(";"):
            #print line
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


class LaunchpadBugTracker:
    def __init__(self, bugtracker_name):
        self.name = bugtracker_name
        self.products = {}

    def retrieveProducts(self):
        # TODO: Retrieve the bugtracker object from launchpad

        launchpad_components = {
            'libglx': {
                'name': 'libglx',
                'is_visible': True,
                'is_custom': False,
                },
            'DRM/ObsoleteDriver': {
                'name': 'DRM/ObsoleteDriver',
                'is_visible': True,
                'is_custom': False,
                },
            'DRM/other': {
                'name': 'DRM/other',
                'is_visible': False,
                'is_custom': False,
                },
            'DRM/fglrx': {
                'name': 'DRM/fglrx',
                'is_visible': True,
                'is_custom': True,
                },
            'deleted-custom-component': {
                'name': 'deleted-custom-component',
                'is_visible': False,
                'is_custom': True,
                }
            }

        self.products['DRI'] = {
            'name': 'DRI',
            'components': launchpad_components,
            }

    def components(self, product_name=None):
        if not product_name:
            product_name = 'default'

        if not product_name in self.products:
            return {}

        product = self.products[product_name]

        return product['components']


