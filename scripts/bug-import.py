#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

import logging

import _pythonpath

from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import IProductSet

from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.bugimport import BugImporter


class BugImportScript(LaunchpadScript):

    description = "Import bugs into Launchpad from XML."
    loglevel = logging.INFO

    def add_my_options(self):
        self.parser.add_option('-p', '--product', metavar='PRODUCT',
                               action='store',
                               help='Which product to export',
                               type='string', dest='product', default=None)
        self.parser.add_option('--cache', metavar='FILE', action='store',
                               help='Cache for bug ID mapping',
                               type='string', dest='cache_filename',
                               default='bug-map.pickle')
        # XXX: jamesh 2007-04-11 bugs=86352
        # Not verifying users created by a bug import can result in
        # problems with mail notification, so should not be used for
        # imports.
        self.parser.add_option('--dont-verify-users', dest='verify_users',
                               help="Don't verify newly created users",
                               action='store_false', default=True)

    def main(self):
        if self.options.product is None:
            self.parser.error('No product specified')
        if len(self.args) != 1:
            self.parser.error('Please specify a bug XML file to import')
        bugs_filename = self.args[0]
        
        # don't send email
        config.zopeless.send_email = False
        self.login('bug-importer@launchpad.net')
        
        product = getUtility(IProductSet).getByName(self.options.product)
        if product is None:
            self.parser.error('Product %s does not exist'
                              % self.options.product)

        importer = BugImporter(product, bugs_filename,
                               self.options.cache_filename,
                               verify_users=self.options.verify_users)
        importer.importBugs(self.txn)


if __name__ == '__main__':
    script = BugImportScript('canonical.launchpad.scripts.bugimport')
    script.run()
