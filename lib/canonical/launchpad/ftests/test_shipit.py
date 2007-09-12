# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getMultiAdapter

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests import login
from canonical.launchpad.systemhomes import ShipItApplication
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.database import (
    ShippingRequest, ShippingRequestSet, StandardShipItRequest)
from canonical.launchpad.layers import (
    setFirstLayer, ShipItEdUbuntuLayer, ShipItKUbuntuLayer, ShipItUbuntuLayer)
from canonical.launchpad.interfaces import (
    ShipItDistroSeries, ShipItFlavour, ShippingRequestPriority,
    ShippingRequestStatus)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest


class TestShippingRequestSet(LaunchpadFunctionalTestCase):

    def test_getTotalsForRequests(self):
        requests = ShippingRequest.select(limit=5)
        totals = ShippingRequestSet().getTotalsForRequests(requests)
        for request in requests:
            total_requested, total_approved = totals[request.id]
            self.failUnless(
                total_requested == request.getTotalCDs()
                and total_approved == request.getTotalApprovedCDs())


class TestFraudDetection(LaunchpadFunctionalTestCase):
    """Ensure repeated requests of a given user are marked as PENDING[SPECIAL]
    and requests using an address already used by two other users are marked
    as DUPLICATEDADDRESS.
    """

    flavours_to_layers_mapping = {
        ShipItFlavour.UBUNTU: ShipItUbuntuLayer,
        ShipItFlavour.KUBUNTU: ShipItKUbuntuLayer,
        ShipItFlavour.EDUBUNTU: ShipItEdUbuntuLayer}

    def _get_standard_option(self, flavour):
        return StandardShipItRequest.selectBy(flavour=flavour)[0]

    def _ship_request(self, request):
        if not request.isApproved():
            request.approve()
        shippingrun = ShippingRequestSet()._create_shipping_run([request.id])
        flush_database_updates()

    def _create_request_and_ship_it(self, flavour, user_email=None, form=None):
        request = self._make_new_request_through_web(
            flavour, user_email=user_email, form=form)
        self._ship_request(request)
        return request

    def _make_new_request_through_web(
            self, flavour, user_email=None, form=None, distroseries=None):
        if user_email is None:
            user_email = 'guilherme.salgado@canonical.com'
        if form is None:
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
        request = LaunchpadTestRequest(form=form)
        setFirstLayer(request, self.flavours_to_layers_mapping[flavour])
        login(user_email)
        view = getMultiAdapter(
            (ShipItApplication(), request), name='myrequest')
        if distroseries is not None:
            view.series = distroseries
        view.renderStandardrequestForm()
        errors = getattr(view, 'errors', None)
        self.failUnlessEqual(errors, None)
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

    def test_requests_with_similar_address_but_different_users(self):
        """Requests from different users with similar addresses may be marked
        as DUPLICATEDADDRESS.
        """
        form = {
            'field.recipientdisplayname': 'My Name',
            'field.addressline1': 'Rua Antonio Rodrigues Cajado,',
            'field.addressline2': '1506 - Ap. 703 - Vila Monteiro',
            'field.city': 'Sao Jose dos Campos',
            'field.province': 'Sao Paulo',
            'field.postcode': '12242790',
            'field.phone': '43242352',
            'field.country': '226',
            'FORM_SUBMIT': 'Request',
            }
        flavour = ShipItFlavour.UBUNTU
        option = self._get_standard_option(flavour)
        form['ordertype'] = str(option.id)
        # The first request with a given address is approved.
        request = self._make_new_request_through_web(
            flavour, user_email='test@canonical.com', form=form)
        self.failUnless(request.isApproved(), flavour)

        # We can do some changes to the address here, because even if
        # they are slightly different, we'll consider them the same as
        # long as their normalized form match.
        form['field.addressline2'] = '1506 Ap: 703; Vila Monteiro'
        form['field.postcode'] = '12242-790'

        # If a different user makes a request for CDs of a different release,
        # using the same address, it'll still be approved.
        # We do that because people often make requests for one release and
        # then when they come back to ask CDs of a newer one they create a new
        # account because they no longer have access to the email they used
        # when creating the previous account.
        request2 = self._make_new_request_through_web(
            flavour, user_email='foo.bar@canonical.com', form=form,
            distroseries=ShipItDistroSeries.GUTSY)
        self.failUnless(request2.isApproved(), flavour)
        self.failIfEqual(request.distroseries, request2.distroseries)
        self.failUnlessEqual(
            request2.normalized_address, request.normalized_address)

        # Now when a second request for CDs of the same release are made using
        # the same address, it gets marked with the DUPLICATEDADDRESS status.
        request3 = self._make_new_request_through_web(
            flavour, user_email='karl@canonical.com', form=form)
        self.failUnlessEqual(request.distroseries, request3.distroseries)
        self.failUnless(request3.isDuplicatedAddress(), flavour)
        self.failUnlessEqual(
            request3.normalized_address, request.normalized_address)

        # The same happens for any subsequent requests for that release with
        # the same address.
        request4 = self._make_new_request_through_web(
            flavour, user_email='carlos@canonical.com', form=form)
        self.failUnlessEqual(request.distroseries, request3.distroseries)
        self.failUnless(request4.isDuplicatedAddress(), flavour)

        # As we said, this happens because all requests are considered to have
        # the same shipping address.
        requests = request.getRequestsWithSameAddressFromOtherUsers()
        self.failUnless(request3 in requests)
        self.failUnless(request4 in requests)

        # Note that the request itself is not included in the return value of
        # getRequestsWithSameAddressFromOtherUsers() because we're only
        # interested in the requests made by other users.
        self.failIf(request in requests)

        # Our second request (which was for a different release) is not
        # included in the return of getRequestsWithSameAddressFromOtherUsers()
        # either because that method only consider requests for CDs of the
        # same release.
        self.failIf(request2 in requests)


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

    def setUp(self):
        self.requestset = ShippingRequestSet()
        LaunchpadFunctionalTestCase.setUp(self)

    def test_recipient_email_for_users(self):
        # If a user is active, its requests will have his preferred email as
        # the recipient_email.
        requests = self.requestset.search(recipient_text='Kreutzmann')
        self.failIf(requests.count() == 0)
        request = requests[0]
        self.failUnlessEqual(
            request.recipient.preferredemail.email, request.recipient_email)

        # If the user becomes inactive (which can be done by having his
        # account closed by an admin or by the user himself), though, the
        # recipient_email will be just a piece of text explaining that.
        request.recipient.preferredemail.destroySelf()
        # Need to clean the cache because preferredemail is a cached property.
        request.recipient._preferredemail_cached = None
        self.failIf(request.recipient.preferredemail is not None)
        self.failUnlessEqual(
            u'inactive account -- no email address', request.recipient_email)

    def test_recipient_email_for_shipit_admins(self):
        # Requests made using the admin interface will have the shipit admins
        # team as the recipient and thus its recipient_email property will
        # return config.shipit.admins_email_address no matter what the email
        # address for that team is.
        requests = self.requestset.search(recipient_text='shipit-admins')
        self.failIfEqual(requests.count(), 0)
        for request in requests:
            self.failUnlessEqual(
                request.recipient_email, config.shipit.admins_email_address)

    def test_requests_that_can_be_approved_denied_or_changed(self):
        # Requests pending approval can be approved and denied but not
        # changed.
        pending_request = self.requestset.getOldestPending()
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
        shippingrun = self.requestset._create_shipping_run(
            [shipped_request.id])
        flush_database_updates()
        self.failUnless(shipped_request.isShipped())
        self.failIf(shipped_request.canBeApproved())
        self.failIf(shipped_request.canBeDenied())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

