#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403
import _pythonpath

import logging
import sys

from lp.services.scripts.base import LaunchpadScript
from lp.registry.scripts.entitlement import (
    EntitlementExchange, EntitlementImporter)


class ImportEntitlementsScript(LaunchpadScript):
    """Script for to import entitlement data into Launchpad."""

    description = "Create or update entitlements."
    usage = ("usage: %s [-c|--create | -u|--update] file_name" %
             sys.argv[0])

    loglevel = logging.INFO

    def add_my_options(self):
        """See `LaunchpadScript`."""
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
        """See `LaunchpadScript`."""

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
        entitlement_writer = EntitlementImporter(self.logger)
        importer = EntitlementImporter(self.logger)
        if action == 'create':
            out_data = importer.createEntitlements(reader)
        elif action == 'update':
            out_data = importer.updateEntitlements(reader)
        elif action is None:
            self.logger.error("No action specified.  Use either -c or -u.")
            return 1
        else:
            self.logger.error("Invalid action: %s\n" % action)
            return 1

        self.txn.commit()

        if out_data:
            writer = EntitlementExchange.writerFactory(out_file)
            writer.writerows(out_data)
        return 0

if __name__ == '__main__':
    script = ImportEntitlementsScript(
        'canonical.launchpad.scripts.entitlements')
    script.run()
