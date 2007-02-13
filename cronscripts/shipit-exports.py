#!/usr/bin/python
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Script to export ShipIt orders into csv files."""

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)
from canonical.launchpad.interfaces import (
    IShippingRequestSet, ShipItConstants, ShippingRequestPriority)
from canonical.lp.dbschema import ShipItDistroRelease


class ShipitExports(LaunchpadScript):
    usage = '%prog --priority=normal|high'
    def add_my_options(self):
        self.parser.add_option(
            '--priority',
            dest='priority',
            default=None,
            action='store',
            help='Export only requests with the given priority'
            )
        self.parser.add_option(
            '--distrorelease',
            dest='distrorelease',
            default=None,
            action='store',
            help='Export only requests for CDs of the given distrorelease'
            )

    def main(self):
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)
        self.logger.info('Exporting %s priority ShipIt orders'
            % self.options.priority)

        if self.options.priority == 'normal':
            priority = ShippingRequestPriority.NORMAL
        elif self.options.priority == 'high':
            priority = ShippingRequestPriority.HIGH
        else:
            raise LaunchpadScriptFailure('Wrong value for argument --priority: %s'
                % self.options.priority)

        distrorelease = ShipItConstants.current_distrorelease
        if self.options.distrorelease is not None:
            try:
                distrorelease = ShipItDistroRelease.items[
                    self.options.distrorelease.upper()]
            except KeyError:
                valid_names = ", ".join(
                    release.name for release in ShipItDistroRelease.items)
                raise LaunchpadScriptFailure(
                    'Invalid value for argument --distrorelease: %s. Valid '
                    'values are: %s' % (self.options.distrorelease, valid_names))

        requestset = getUtility(IShippingRequestSet)
        requestset.exportRequestsToFiles(priority, self.txn, distrorelease)

        self.logger.info('Done.')


if __name__ == '__main__':
    script = ShipitExports('shipit-export-orders', dbuser=config.shipit.dbuser)
    script.lock_and_run()

