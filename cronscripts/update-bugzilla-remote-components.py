#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import sys
import re
import pycurl
import time

from optparse import OptionParser
from StringIO import StringIO

class BugzillaRemoteComponentFinder:

    re_products_select = re.compile(r'<select name="product".*onchange="doOnSelectProduct\(2\);">(.*?)</select>', re.DOTALL)
    re_product = re.compile(r'<option value="(.*)">(.*)</option>')
    re_cpts = re.compile(r'cpts\[(\d+)\] = \[(.*)\]')
    re_vers = re.compile(r'vers\[(\d+)\] = \[(.*)\]')

    def __init__(self, bzurl):
        self.products = {}
        self.url = "%s/query.cgi?format=advanced" %(bzurl)

    def getUrlContent(self, url):
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
        body = self.getUrlContent(self.url)

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


class LaunchpadBugtracker:
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


class UpdateRemoteComponentsFromBugzilla:
    def __init__(self, dbuser):
        self.dbuser = dbuser

    def getBugzillas(self):
        # TODO: Lookup list of bugzillas from launchpad
        bugzillas = [
            {'name': 'freedesktop-bugs',
             'url': 'http://bugs.freedesktop.org'},
            {'name': 'gnome-bugs',
             'url': 'http://bugs.gnome.org'},
            ]
        return bugzillas

    def lock_and_run(self):
        # TODO: Replace this with the actual database object
        distro = 'ubuntu'

        for bugzilla in self.getBugzillas():
            lp_bugtracker = LaunchpadBugtracker(bugzilla['name'])
            lp_bugtracker.retrieveProducts()

            bz_bugtracker = BugzillaRemoteComponentFinder(bugzilla['url'])
            bz_bugtracker.retrieveProducts()

            for product in bz_bugtracker.products.itervalues():
                #print "%s: %s" %(product['name'], product['components'])

                bz_components = product['components']
                lp_components = lp_bugtracker.components(product['name'])

                new_comps = self.newComponents(bz_components, lp_components)
                rm_comps = self.removedComponents(bz_components, lp_components)

                # TODO: Apply changes to launchpad database
                print product['name']
                print " - add to database:  ", new_comps
                print " - rm from database:  ", rm_comps
                print


    def removedComponents(self, bugzilla_components, launchpad_components):
        deletes = []
        for component in launchpad_components.itervalues():
            if component['name'] in bugzilla_components:
                continue

            if component['is_visible'] and not component['is_custom']:
                deletes.append(component)
        return deletes

    def newComponents(self, bugzilla_components, launchpad_components):
        adds = []
        for component in bugzilla_components.itervalues():
            if component['name'] not in launchpad_components:
                adds.append(component)
        return adds


if __name__ == "__main__":
    usage = """
    %prog [bugzilla-url]
    """
    parser = OptionParser(usage=usage)
    #parser.add_option('-m', '--max-size',
    #    action='store', dest='maxsize',
    #    help='Maximum filesize for processing attachments')
    (options, args) = parser.parse_args()

    opt_dbuser = "TODO"

    updater = UpdateRemoteComponentsFromBugzilla(dbuser=opt_dbuser)

    # TODO: If a bz url was specified, run against only it

    start_time = time.time()

    updater.lock_and_run()
    
    run_time = time.time() - start_time
    print("Time for this run: %.3f seconds." % run_time)
