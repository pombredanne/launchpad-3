#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Script to process requests with a PENDINGSPECIAL status.

For now this script will just deny these PENDINGSPECIAL requests.
"""

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.launchpad.interfaces import (
    IShippingRequestSet, ShippingRequestStatus)


class ShipitRequestMassProcessing(LaunchpadScript):

    usage = '%prog --status=(pending-special|dupe) [--action(deny|approve)]'

    def add_my_options(self):
        self.parser.add_option(
            '--status', dest='status', default=None, action='store',
            help='Process the requests with the given status only.')
        self.parser.add_option(
            '--action', dest='action', default='deny', action='store',
            help='Approve or deny the requests.')

    def main(self):
        if self.options.status == 'pending-special':
            status = ShippingRequestStatus.PENDINGSPECIAL
        elif self.options.status == 'dupe':
            status = ShippingRequestStatus.DUPLICATEDADDRESS
        else:
            raise LaunchpadScriptFailure(
                'Unknown status: %s' % self.options.status)

        if self.options.action == 'approve':
            new_status = ShippingRequestStatus.APPROVED
        elif self.options.action == 'deny':
            new_status = ShippingRequestStatus.DENIED
        else:
            raise LaunchpadScriptFailure(
                'Unknown action: %s' % self.options.action)

        self.logger.info('Processing %s requests.' % status.name)

        self.txn.begin()
        requestset = getUtility(IShippingRequestSet)
        requestset.processRequests(status, new_status)
        self.txn.commit()

        self.logger.info('Done.')
        return 0


if __name__ == '__main__':
    script = ShipitRequestMassProcessing(
        'shipit-process-requests', dbuser=config.shipit.dbuser)
    script.lock_and_run()

