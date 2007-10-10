#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Script to generate reports with data from ShipIt orders."""

import _pythonpath

from datetime import datetime, date

from zope.component import getUtility

import pytz

from canonical.config import config
from canonical.uuid import generate_uuid
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IShippingRequestSet, IShipItReportSet)


class ShipitReporter(LaunchpadCronScript):
    def _createLibraryFileAlias(self, csv_file, basename):
        """Create and return a LibraryFileAlias containing the given csv file.

        The filename is generated using the given basename, the current date
        and a random string, in order for it to not be guessable.
        """
        fileset = getUtility(ILibraryFileAliasSet)
        csv_file.seek(0)
        now = datetime.now(pytz.timezone('UTC'))
        filename = ('%s-%s-%s.csv' 
                    % (basename, now.strftime('%y-%m-%d'), generate_uuid()))
        return fileset.create(
            name=filename, size=len(csv_file.getvalue()), file=csv_file,
            contentType='text/plain')

    def main(self):
        self.logger.info('Generating ShipIt reports')

        requestset = getUtility(IShippingRequestSet)
        reportset = getUtility(IShipItReportSet)

        self.txn.begin()
        csv_file = requestset.generateRequestDistributionReport()
        reportset.new(self._createLibraryFileAlias(
            csv_file, 'RequestDistribution'))
        self.txn.commit()

        self.txn.begin()
        csv_file = requestset.generateCountryBasedReport()
        reportset.new(self._createLibraryFileAlias(csv_file, 'OrdersByCountry'))
        self.txn.commit()

        self.txn.begin()
        csv_file = requestset.generateShipmentSizeBasedReport()
        reportset.new(self._createLibraryFileAlias(csv_file, 'OrdersBySize'))
        self.txn.commit()

        self.txn.begin()
        # XXX: salgado 2005-11-24:
        # For now this will be hardcoded as the date when a new ShipIt is
        # opened.
        start_date = date(2007, 4, 5)
        csv_file = requestset.generateWeekBasedReport(start_date, date.today())
        reportset.new(self._createLibraryFileAlias(csv_file, 'OrdersByWeek'))
        self.txn.commit()

        self.logger.info('Done.')


if __name__ == '__main__':
    script = ShipitReporter('shipit-reporter', dbuser=config.shipit.dbuser)
    script.lock_and_run(implicit_begin=False)

