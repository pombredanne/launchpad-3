# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.database import ShippingRequest, ShippingRequestSet


class TestShippingRequestSet(LaunchpadFunctionalTestCase):

    def test_getTotalsForRequests(self):
        requests = ShippingRequest.select(limit=5)
        totals = ShippingRequestSet().getTotalsForRequests(requests)
        for request in requests:
            total_requested, total_approved = totals[request.id]
            self.failUnless(
                total_requested == request.getTotalCDs()
                and total_approved == request.getTotalApprovedCDs())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

