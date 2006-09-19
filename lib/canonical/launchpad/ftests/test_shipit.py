# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.publisher.browser import TestRequest
from zope.component import getView

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests import login
from canonical.launchpad.systemhomes import ShipItApplication
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.database import (
    ShippingRequest, ShippingRequestSet, StandardShipItRequestSet)
from canonical.launchpad.layers import (
    ShipItUbuntuLayer, ShipItKUbuntuLayer, ShipItEdUbuntuLayer, setFirstLayer)
from canonical.launchpad.interfaces import ShippingRequestPriority
from canonical.lp.dbschema import ShipItFlavour, ShippingRequestStatus


class TestShippingRequestSet(LaunchpadFunctionalTestCase):

    def test_getTotalsForRequests(self):
        requests = ShippingRequest.select(limit=5)
        totals = ShippingRequestSet().getTotalsForRequests(requests)
        for request in requests:
            total_requested, total_approved = totals[request.id]
            self.failUnless(
                total_requested == request.getTotalCDs()
                and total_approved == request.getTotalApprovedCDs())


class TestSecondsAndThirdRequestsAreCorrectlyHandled(
        LaunchpadFunctionalTestCase):

    flavours_to_layers_mapping = {
        ShipItFlavour.UBUNTU: ShipItUbuntuLayer,
        ShipItFlavour.KUBUNTU: ShipItKUbuntuLayer,
        ShipItFlavour.EDUBUNTU: ShipItEdUbuntuLayer}

    def _get_standard_option(self, flavour):
        return StandardShipItRequestSet().getByFlavour(flavour)[0]

    def _ship_request(self, request):
        requestset = ShippingRequestSet()
        if not request.isApproved():
            request.approve()
        shippingrun = requestset._create_shipping_run([request.id])
        flush_database_updates()

    def _create_request_and_ship_it(self, flavour):
        request = self._make_new_request_through_web(flavour)
        self._ship_request(request)
        return request

    def _make_new_request_through_web(self, flavour):
        standardoption = self._get_standard_option(flavour)
        form = {
            'field.recipientdisplayname': 'Foo',
            'field.addressline1': 'Some street',
            'field.city': 'City',
            'field.province': 'Province',
            'field.postcode': '432432',
            'field.phone': '43242352',
            'field.country': '226',
            'ordertype': str(standardoption.id),
            'FORM_SUBMIT': 'Request',
            }
        request = TestRequest(form=form)
        request.notifications = []
        setFirstLayer(request, self.flavours_to_layers_mapping[flavour])
        login('guilherme.salgado@canonical.com')
        view = getView(ShipItApplication(), 'myrequest', request)
        view.renderStandardrequestForm()
        return view.current_order

    def test_first_request_is_approved(self):
        """The first request of a given flavour should always be approved."""
        for flavour in ShipItFlavour.items:
            request = self._make_new_request_through_web(flavour)
            self.failUnless(request.isApproved(), flavour)
            self._ship_request(request)
            flush_database_updates()

    def test_second_request_is_marked_pending(self):
        """The second request of a given flavour is always marked PENDING."""
        for flavour in ShipItFlavour.items:
            first_request = self._create_request_and_ship_it(flavour)
            second_request = self._make_new_request_through_web(flavour)
            self.failUnless(second_request.isAwaitingApproval(), flavour)
            self._ship_request(second_request)

    def test_third_request_is_marked_pending_special(self):
        """The third request of a given flavour is always marked
        PENDINGSPECIAL.
        """
        for flavour in ShipItFlavour.items:
            first_request = self._create_request_and_ship_it(flavour)
            second_request = self._create_request_and_ship_it(flavour)
            third_request = self._make_new_request_through_web(flavour)
            self.failUnless(third_request.isPendingSpecial(), flavour)
            self._ship_request(third_request)


class TestShippingRun(LaunchpadFunctionalTestCase):

    def test_create_shipping_run_sets_requests_count(self):
        requestset = ShippingRequestSet()
        approved_request_ids = requestset.getUnshippedRequestsIDs(
            ShippingRequestPriority.NORMAL)
        non_approved_request = requestset.getOldestPending()
        self.failIf(non_approved_request is None)
        run = requestset._create_shipping_run(
            approved_request_ids + [non_approved_request.id])
        self.failUnless(run.requests_count == len(approved_request_ids))


class TestShippingRequest(LaunchpadFunctionalTestCase):

    def test_requests_that_can_be_approved_denied_or_changed(self):
        requestset = ShippingRequestSet()

        # Requests pending approval can be approved and denied but not
        # changed.
        pending_request = requestset.getOldestPending()
        self.failUnless(pending_request.isAwaitingApproval())
        self.failUnless(pending_request.canBeApproved())
        self.failUnless(pending_request.canBeDenied())

        # Requests pending special consideration can be approved and denied
        # too.
        pending_special_request = pending_request
        pending_special_request.status = ShippingRequestStatus.PENDINGSPECIAL
        self.failUnless(pending_special_request.isPendingSpecial())
        self.failUnless(pending_special_request.canBeApproved())
        self.failUnless(pending_special_request.canBeDenied())

        # Denied requests can be approved but can't be denied.
        denied_request = pending_request
        denied_request.status = ShippingRequestStatus.DENIED
        self.failUnless(denied_request.isDenied())
        self.failUnless(denied_request.canBeApproved())
        self.failIf(denied_request.canBeDenied())

        # Cancelled requests can't be approved and denied.
        cancelled_request = denied_request
        cancelled_request.status = ShippingRequestStatus.CANCELLED
        self.failUnless(cancelled_request.isCancelled())
        self.failIf(cancelled_request.canBeApproved())
        self.failIf(cancelled_request.canBeDenied())

        # Like cancelled requests, shipped ones can't be approved, neither
        # denied.
        shipped_request = cancelled_request
        shipped_request.status = ShippingRequestStatus.APPROVED
        shippingrun = requestset._create_shipping_run([shipped_request.id])
        flush_database_updates()
        self.failUnless(shipped_request.isShipped())
        self.failIf(shipped_request.canBeApproved())
        self.failIf(shipped_request.canBeDenied())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

