#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import logging
import sys
import csv

import _pythonpath

from canonical.config import config

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.entitlement import (
    EntitlementExchange,
    EntitlementWriter,
    )

class ImportEntitlementsScript(LaunchpadScript):

    description = "Create or update entitlements."
    usage = ("usage: %s [-c|--create | -u|--update] file_name" %
             sys.argv[0])

    loglevel = logging.INFO

    def add_my_options(self):
        self.parser.add_option(
            '-c', '--create', action='store_const', const='create',
            help='Create new entitlements', dest='action')
        self.parser.add_option(
            '-u', '--update', action='store_const', const='update',
            help='Update existing entitlements', dest='action')
        self.parser.add_option(
            '-f', '--infile', action='store', default='-',
            help='Input file name ("-" for stdin)', dest='in_file_name')
        self.parser.add_option(
            '-o', '--outfile', action='store', default='-',
            help='Output file name ("-" for stdout)', dest='out_file_name')

    def main(self):

        action = self.options.action

        if self.options.in_file_name == '-':
            in_file = sys.stdin
        else:
            in_file = open(self.options.in_file_name, "rb")

        if self.options.out_file_name == '-':
            out_file = sys.stdout
        else:
            out_file = open(self.options.out_file_name, "wb")

        # get a reader and writer
        reader = EntitlementExchange.readerFactory(in_file)
        writer = EntitlementExchange.writerFactory(out_file)
        in_data = list(reader)
        entitlement_writer = EntitlementWriter(self.logger)
        if action == 'create':
            out_data = entitlement_writer.createEntitlements(in_data)
        elif action == 'update':
            out_data = entitlement_writer.updateEntitlements(in_data)
        else:
            self.logger.error("Invalid action: %s\n" % action)
            return 1

        self.txn.commit()

        if out_data:
            writer.writerows(out_data)
        return 0

if __name__ == '__main__':
    script = ImportEntitlementsScript('canonical.launchpad.scripts.entitlements')
    script.run()
