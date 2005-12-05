#!/usr/bin/python
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Script to generate reports with data from ShipIt orders."""

import _pythonpath

from datetime import datetime, date
import optparse
import sys

from zope.component import getUtility

import pytz

from canonical.config import config
from canonical.uuid import generate_uuid
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IShippingRequestSet, IShipItReportSet)


def _createLibraryFileAlias(csv_file, basename):
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


def main(argv):
    parser = optparse.OptionParser()
    # Add the verbose/quiet options.
    logger_options(parser)

    options, args = parser.parse_args(argv[1:])
    logger_obj = logger(options, 'shipit-reports')
    logger_obj.info('Generating ShipIt reports')

    ztm = initZopeless(implicitBegin=False)
    execute_zcml_for_scripts()
    requestset = getUtility(IShippingRequestSet)
    reportset = getUtility(IShipItReportSet)

    ztm.begin()
    csv_file = requestset.generateCountryBasedReport()
    reportset.new(_createLibraryFileAlias(csv_file, 'OrdersByCountry'))

    csv_file = requestset.generateShipmentSizeBasedReport()
    reportset.new(_createLibraryFileAlias(csv_file, 'OrdersBySize'))

    # XXX: For now this will be hardcoded as the date when we opened
    # ShipItNG. In future we'll have UI to specify a start/end date
    # for every report and then we'll be able to remove this.
    # -- Guilherme Salgado, 2005-11-24
    start_date = date(2005, 9, 14)
    end_date = date.today()
    csv_file = requestset.generateWeekBasedReport(start_date, end_date)
    reportset.new(_createLibraryFileAlias(csv_file, 'OrdersByWeek'))
    ztm.commit()

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

