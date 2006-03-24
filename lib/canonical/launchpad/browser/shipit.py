# Copyright 2005 Canonical Ltd

__metaclass__ = type

__all__ = [
    'StandardShipItRequestAddView', 'ShippingRequestApproveOrDenyView',
    'ShippingRequestsView', 'ShipItLoginView', 'ShipItRequestView',
    'ShipItUnauthorizedView', 'StandardShipItRequestsView',
    'ShippingRequestURL', 'StandardShipItRequestURL', 'ShipItExportsView',
    'ShipItNavigation', 'RedirectToOldestPendingRequest', 'ShipItReportsView',
    'StandardShipItRequestSetNavigation', 'ShippingRequestSetNavigation',
    'ShippingRequestAdminView']


from zope.event import notify
from zope.component import getUtility
from zope.interface import implements
from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import WidgetsError
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.config import config
from canonical.cachedproperty import cachedproperty
from canonical.lp.dbschema import ShipItFlavour, ShipItArchitecture
from canonical.launchpad.webapp.error import SystemErrorView
from canonical.launchpad.webapp.login import LoginOrRegister
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp import (
    canonical_url, Navigation, stepto, redirection)
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    IStandardShipItRequestSet, IShippingRequestSet, ILaunchBag,
    ShippingRequestStatus, ILaunchpadCelebrities, ICanonicalUrlData,
    IShippingRunSet, IShipItApplication, IShipItReportSet)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.layers import (
    ShipItUbuntuLayer, ShipItKUbuntuLayer, ShipItEdUbuntuLayer)
from canonical.launchpad import _


class ShippingRequestURL:
    implements(ICanonicalUrlData)
    inside = None

    def __init__(self, context):
        self.path = '/requests/%d' % context.id
        self.context = context


class StandardShipItRequestURL:
    implements(ICanonicalUrlData)
    inside = None

    def __init__(self, context):
        self.path = '/standardoptions/%d' % context.id
        self.context = context


class ShipItUnauthorizedView(SystemErrorView):

    response_code = 403
    forbidden_page = ViewPageTemplateFile('../templates/launchpad-forbidden.pt')

    def __call__(self):
        # Users should always go to shipit.ubuntu.com and login before
        # going to any other page.
        return self.forbidden_page()


# XXX: The LoginOrRegister class is not really designed to be reused. That
# class must either be fixed to allow proper reuse or we should write a new
# class which doesn't reuses LoginOrRegister here. -- GuilhermeSalgado
# 2005-09-09
class ShipItLoginView(LoginOrRegister):
    """Process the login form and redirect the user to the request page."""

    def getApplicationURL(self):
        return 'https://launchpad.net'

    def process_form(self):
        if getUtility(ILaunchBag).user is not None:
            # Already logged in.
            self._redirect()
            return
        LoginOrRegister.process_form(self)
        if self.login_success():
            self._redirect()

    def _redirect(self):
        """Redirect the logged in user to the request page.

        If the logged in user is a ShipIt administrator, then he's redirected
        to the 'requests' page, where all requests are shown.
        """
        user = getUtility(ILaunchBag).user
        assert user is not None
        if user.inTeam(getUtility(ILaunchpadCelebrities).shipit_admin):
            self.request.response.redirect('requests')
        else:
            self.request.response.redirect('myrequest')


class ShipItRequestView(GeneralFormView):
    """The view for people to create/edit ShipIt requests."""

    mail_template = """
The user %(recipientname)s, logged in with the email address %(recipientemail)s,
placed a new request in ShipIt, leaving also a comment. This might mean
(s)he's asking for more CDs, so this request is pending approval.

%(recipientname)s already has %(shipped_requests)d requests sent to the shipping
company.

This request can be seen at:
%(requesturl)s

The comment left by the user:

    %(reason)s
"""

    def __init__(self, context, request):
        GeneralFormView.__init__(self, context, request)
        self.user = getUtility(ILaunchBag).user
        if ShipItUbuntuLayer.providedBy(request):
            self.flavour = ShipItFlavour.UBUNTU
            self.from_email_address = config.shipit.shipit_ubuntu_from_email
        elif ShipItEdUbuntuLayer.providedBy(request):
            self.flavour = ShipItFlavour.EDUBUNTU
            self.from_email_address = config.shipit.shipit_edubuntu_from_email
        elif ShipItKUbuntuLayer.providedBy(request):
            self.flavour = ShipItFlavour.KUBUNTU
            self.from_email_address = config.shipit.shipit_kubuntu_from_email
        else:
            raise AssertionError(
                'This request must provide one of ShipItEdUbuntuLayer, '
                'ShipItKUbuntuLayer or ShipItUbuntuLayer')

    @property
    def initial_values(self):
        """Get initial values from this user's current request, if there's one.

        If this user has no current request, then get the initial values from
        any non-cancelled approved request placed by this user.
        """
        field_values = {}
        user = getUtility(ILaunchBag).user
        if user is None:
            return field_values
        current_order = user.currentShipItRequest()
        existing_order = current_order
        if existing_order is None:
            for order in user.pastShipItRequests():
                if not order.cancelled and order.approved:
                    existing_order = order
                    break

        if existing_order is not None:
            for name in self.fieldNames:
                if existing_order != current_order and name == 'reason':
                    # Don't use the reason provided for a request that was
                    # shipped already.
                    continue
                field_values[name] = getattr(existing_order, name)

        return field_values

    def standardShipItRequests(self):
        """Return all standard ShipIt Requests."""
        return getUtility(IStandardShipItRequestSet).getByFlavour(self.flavour)

    @cachedproperty
    def current_order_standard_id(self):
        """The current order's StandardShipItRequest id, or None in case
        there's no current order or the current order doesn't contain any CDs
        of self.flavour."""
        if self.current_order is None:
            return None
        quantities = self.current_order.getQuantitiesByFlavour(self.flavour)
        standard = getUtility(IStandardShipItRequestSet).getByNumbersOfCDs(
            self.flavour, quantities[ShipItArchitecture.X86].quantity,
            quantities[ShipItArchitecture.AMD64].quantity,
            quantities[ShipItArchitecture.PPC].quantity)
        return getattr(standard, 'id', None)

    @cachedproperty('_current_order')
    def current_order(self):
        return self.user.currentShipItRequest()

    def process_form(self):
        """Overwrite GeneralFormView's process_form() method because we want
        to be able to have a 'Cancel' button in a different <form> element.
        """
        if self.request.form.get('cancel') is not None:
            self.current_order.cancel(self.user)
            self.process_status = 'Request Cancelled'
        else:
            self.process_status = GeneralFormView.process_form(self)

        flush_database_updates()
        self._current_order = self.user.currentShipItRequest()
        return self.process_status

    def process(self, *args, **kw):
        """Process the submitted form, either creating a new request, or
        changing an existing one.
        """
        form = self.request.form
        request_type_id = form.get('ordertype')
        # self.validate() must ensure that the ordertype is not None.
        assert request_type_id is not None
        request_type = getUtility(IStandardShipItRequestSet).get(
            request_type_id)
        current_order = self.current_order
        need_notification = False
        if not current_order:
            current_order = getUtility(IShippingRequestSet).new(
                self.user, kw['recipientdisplayname'], kw['country'],
                kw['city'], kw['addressline1'], kw['phone'],
                kw['addressline2'], kw['province'], kw['postcode'],
                kw['organization'], kw['reason'])
        else:
            if current_order.reason is None and kw['reason'] is not None:
                # The user entered something in the 'reason' entry for the
                # first time. We need to mark this order as pending approval
                # and send an email to the shipit admins.
                need_notification = True
            for name in self.fieldNames:
                setattr(current_order, name, kw[name])

        current_order.setQuantitiesBasedOnStandardRequest(request_type)
        if need_notification:
            self._notifyShipItAdmins(current_order)
            if current_order.isApproved():
                current_order.clearApproval()
        elif not current_order.isApproved():
            current_order.approve()
        else:
            # Nothing to do
            pass
        return 'Done'

    def validate(self, data):
        errors = []
        # We use a custom template with some extra widgets, so we have to
        # cheat here and access self.request.form
        if not self.request.form.get('ordertype'):
            # XXX: Should we raise an UnexpectedFormData here? I haven't done
            # that because it inherits from AssertionError, and thus I don't
            # think it's going to be handled anywhere.
            errors.append(LaunchpadValidationError(_(
                'Please select the number of CDs you would like.')))

        country = data['country']
        code = data['country'].iso3166code2
        if (code in ('US', 'GB', 'FR', 'IT', 'DE', 'NO', 'SE', 'ES')
            and not data['postcode']):
            errors.append(LaunchpadValidationError(_(
                "Shipping to your country requires a postcode, but you didn't "
                "provide one. Please enter one below.")))

        if errors:
            raise WidgetsError(errors)

    def _notifyShipItAdmins(self, order):
        """Notify the shipit admins by email that there's a new request."""
        subject = '[ShipIt] New Request Pending Approval (#%d)' % order.id
        recipient = order.recipient
        headers = {'Reply-To': recipient.preferredemail.email}
        replacements = {'recipientname': order.recipientdisplayname,
                        'recipientemail': recipient.preferredemail.email,
                        'requesturl': canonical_url(order),
                        'shipped_requests':
                            recipient.shippedShipItRequests().count(),
                        'reason': order.reason}
        message = self.mail_template % replacements
        shipit_admins = config.shipit.shipit_admins_email
        simple_sendmail(
            self.from_email_address, shipit_admins, subject, message, headers)


class RedirectToOldestPendingRequest:
    """A simple view to redirect to the oldest pending request."""

    def __call__(self):
        oldest_pending = getUtility(IShippingRequestSet).getOldestPending()
        self.request.response.redirect(canonical_url(oldest_pending))


class ShippingRequestsView:
    """The view to list ShippingRequests that match a given criteria."""

    submitted = False
    selectedStatus = 'pending'
    selectedType = 'any'
    recipient_text = ''

    def standardShipItRequests(self):
        """Return a list with all standard ShipIt Requests."""
        return getUtility(IStandardShipItRequestSet).getAll()

    def processForm(self):
        """Process the form, if it was submitted."""
        request = self.request
        if not request.get('show'):
            self.batchNavigator = self._getBatchNavigator([])
            return

        self.submitted = True
        status = request.get('statusfilter')
        self.selectedStatus = status
        if status == 'pending':
            status = ShippingRequestStatus.PENDING
        elif status == 'approved':
            status = ShippingRequestStatus.APPROVED
        elif status == 'denied':
            status = ShippingRequestStatus.DENIED
        else:
            status = ShippingRequestStatus.ALL

        requestset = getUtility(IShippingRequestSet)
        self.selectedType = request.get('typefilter')
        # self.selectedType may be one of 'custom', 'standard', 'any' or the
        # id of a StandardShipItRequest.
        if self.selectedType in ('custom', 'standard', 'any'):
            # The user didn't select any specific standard type
            standard_type = None
            request_type = self.selectedType
        else:
            # In this case the user selected a specific standard type, which
            # means self.selectedType is the id of a StandardShipItRequest.
            assert self.selectedType.isdigit()
            self.selectedType = int(self.selectedType)
            standard_type = getUtility(IStandardShipItRequestSet).get(
                self.selectedType)
            request_type = 'standard'

        orderby = str(request.get('orderby'))
        self.recipient_text = request.get('recipient_text')
        results = requestset.search(
            request_type=request_type, standard_type=standard_type,
            status=status, recipient_text=self.recipient_text,
            orderBy=orderby)
        self.batchNavigator = self._getBatchNavigator(results)

    def _getBatchNavigator(self, results):
        return BatchNavigator(results, self.request)


class StandardShipItRequestsView:
    """The view for the list of all StandardShipItRequests."""

    def processForm(self):
        if self.request.method != 'POST':
            return

        for key, value in self.request.form.items():
            if value == 'Delete':
                id = int(key)
                getUtility(IStandardShipItRequestSet).get(id).destroySelf()


class StandardShipItRequestAddView(AddView):
    """The view to add a new Standard ShipIt Request."""

    def nextURL(self):
        return '.'

    def createAndAdd(self, data):
        flavour = data.get('flavour')
        quantityx86 = data.get('quantityx86')
        quantityamd64 = data.get('quantityamd64')
        quantityppc = data.get('quantityppc')
        # XXX: Need to do something about this 'isdefault' because we need a
        # default request for each flavour we have.
        isdefault = data.get('isdefault')
        request = getUtility(IStandardShipItRequestSet).new(
            flavour, quantityx86, quantityamd64, quantityppc, isdefault)
        notify(ObjectCreatedEvent(request))


class ShippingRequestAdminMixinView:

    def getWidgetsFromFieldsMapping(self):
        widgets = {}
        for flavour in ShipItFlavour.items:
            arches = {}
            for arch in ShipItArchitecture.items:
                widget_name = self.quantity_fields_mapping[flavour][arch]
                widget_name += '_widget'
                arches[arch] = getattr(self, widget_name)
            widgets[flavour] = arches
        return widgets


class ShippingRequestApproveOrDenyView(
        GeneralFormView, ShippingRequestAdminMixinView):
    """The page where admins can Approve/Deny existing requests."""

    __launchpad__facetname = 'overview'

    quantity_fields_mapping = {
        ShipItFlavour.UBUNTU:
            {ShipItArchitecture.X86: 'ubuntu_quantityx86approved',
             ShipItArchitecture.PPC: 'ubuntu_quantityppcapproved',
             ShipItArchitecture.AMD64: 'ubuntu_quantityamd64approved'},
        ShipItFlavour.KUBUNTU:
            {ShipItArchitecture.X86: 'kubuntu_quantityx86approved',
             ShipItArchitecture.PPC: 'kubuntu_quantityppcapproved',
             ShipItArchitecture.AMD64: 'kubuntu_quantityamd64approved'},
        ShipItFlavour.EDUBUNTU:
            {ShipItArchitecture.X86: 'edubuntu_quantityx86approved',
             ShipItArchitecture.PPC: 'edubuntu_quantityppcapproved',
             ShipItArchitecture.AMD64: 'edubuntu_quantityamd64approved'}
        }

    def process(self, *args, **kw):
        context = self.context
        action = self.request.form.get('FORM_SUBMIT')

        if 'Deny' not in action:
            quantities = {}
            for flavour in self.quantity_fields_mapping:
                quantities[flavour] = {}
                for arch in self.quantity_fields_mapping[flavour]:
                    field_name = self.quantity_fields_mapping[flavour][arch]
                    quantities[flavour][arch] = kw[field_name]

        if action == 'Approve':
            context.approve(whoapproved=getUtility(ILaunchBag).user)
            context.highpriority = kw['highpriority']
            context.setApprovedQuantities(quantities)
            self._nextURL = self._makeNextURL(previous_action='approved')
        elif action == 'Change Approved Totals':
            context.highpriority = kw['highpriority']
            context.setApprovedQuantities(quantities)
            self._nextURL = self._makeNextURL(previous_action='changed')
        elif action == 'Deny':
            context.deny()
            self._nextURL = self._makeNextURL(previous_action='denied')
        else:
            # Do something here to tell the user this action is not expected.
            pass

        return 'Done'

    def _makeNextURL(self, previous_action):
        # Need to flush all updates so that getOldestPending() can see the
        # updated values.
        flush_database_updates()
        url = '.'
        next_order = getUtility(IShippingRequestSet).getOldestPending()
        if next_order:
            url = '%s?previous=%d&%s=1' % (canonical_url(next_order),
                                           self.context.id, previous_action)
        return url

    @property
    def initial_values(self):
        initial = {}
        initial['highpriority'] = self.context.highpriority
        requested = self.context.getRequestedCDsGroupedByFlavourAndArch()
        for flavour in self.quantity_fields_mapping:
            for arch in self.quantity_fields_mapping[flavour]:
                field_name = self.quantity_fields_mapping[flavour][arch]
                requested_cds = requested[flavour][arch]
                initial[field_name] = requested_cds.quantityapproved
        return initial

    def recipientHasOtherShippedRequests(self):
        """Return True if the recipient has other requests that were already
        sent to the shipping company."""
        shipped_requests = self.context.recipient.shippedShipItRequests()
        if not shipped_requests:
            return False
        elif (shipped_requests.count() == 1 
              and shipped_requests[0] == self.context):
            return False
        else:
            return True

    def contextCancelledOrShipped(self):
        """Return true if the context was cancelled or shipped."""
        return self.context.cancelled or self.context.shipment is not None


class ShippingRequestAdminView(GeneralFormView, ShippingRequestAdminMixinView):
    """The page where admins can create new requests or change existing ones."""

    __launchpad__facetname = 'overview'

    quantity_fields_mapping = {
        ShipItFlavour.UBUNTU:
            {ShipItArchitecture.X86: 'ubuntu_quantityx86',
             ShipItArchitecture.PPC: 'ubuntu_quantityppc',
             ShipItArchitecture.AMD64: 'ubuntu_quantityamd64'},
        ShipItFlavour.KUBUNTU:
            {ShipItArchitecture.X86: 'kubuntu_quantityx86',
             ShipItArchitecture.PPC: 'kubuntu_quantityppc',
             ShipItArchitecture.AMD64: 'kubuntu_quantityamd64'},
        ShipItFlavour.EDUBUNTU:
            {ShipItArchitecture.X86: 'edubuntu_quantityx86',
             ShipItArchitecture.PPC: 'edubuntu_quantityppc',
             ShipItArchitecture.AMD64: 'edubuntu_quantityamd64'}
        }

    current_order = None
    shipping_details_fields = [
        'recipientdisplayname', 'country', 'city', 'addressline1', 'phone',
        'addressline2', 'province', 'postcode', 'organization']

    def __init__(self, context, request):
        order_id = request.form.get('order')
        if order_id is not None and order_id.isdigit():
            self.current_order = getUtility(IShippingRequestSet).get(
                int(order_id))
        GeneralFormView.__init__(self, context, request)

    @property
    def initial_values(self):
        initial = {}
        if self.current_order is None:
            return initial

        order = self.current_order
        initial['highpriority'] = order.highpriority
        requested = order.getRequestedCDsGroupedByFlavourAndArch()
        for flavour in self.quantity_fields_mapping:
            for arch in self.quantity_fields_mapping[flavour]:
                field_name = self.quantity_fields_mapping[flavour][arch]
                requested_cds = requested[flavour][arch]
                initial[field_name] = requested_cds.quantityapproved

        for field in self.shipping_details_fields:
            initial[field] = getattr(order, field)
        return initial

    def validate(self, data):
        errors = []
        country = data['country']
        code = data['country'].iso3166code2
        if (code in ('US', 'GB', 'FR', 'IT', 'DE', 'NO', 'SE', 'ES')
            and not data['postcode']):
            errors.append(LaunchpadValidationError(_(
                "Shipping to your country requires a postcode, but you didn't "
                "provide one. Please enter one below.")))

        if errors:
            raise WidgetsError(errors)

    def process(self, *args, **kw):
        user = getUtility(ILaunchBag).user
        form = self.request.form
        current_order = self.current_order
        if not current_order:
            current_order = getUtility(IShippingRequestSet).new(
                user, kw['recipientdisplayname'], kw['country'],
                kw['city'], kw['addressline1'], kw['phone'],
                kw['addressline2'], kw['province'], kw['postcode'],
                kw['organization'])
        else:
            for name in self.shipping_details_fields:
                setattr(current_order, name, kw[name])

        quantities = {}
        for flavour in self.quantity_fields_mapping:
            quantities[flavour] = {}
            for arch in self.quantity_fields_mapping[flavour]:
                field = self.quantity_fields_mapping[flavour][arch]
                quantities[flavour][arch] = kw[field]

        current_order.highpriority = kw['highpriority']
        current_order.setQuantities(quantities)
        if not current_order.isApproved():
            current_order.approve()
        return 'Done'


class ShipItReportsView(LaunchpadView):
    """The view for the list of shipit reports."""

    @property
    def reports(self):
        return getUtility(IShipItReportSet).getAll()


class ShipItExportsView:
    """The view for the list of shipit exports."""

    def process_form(self):
        """Process the form, marking the choosen ShippingRun as 'sent for
        shipping'.
        """
        if self.request.method != 'POST':
            return

        for key, value in self.request.form.items():
            if key.isdigit() and value == 'Yes':
                try:
                    shippingrun_id = int(key)
                except ValueError:
                    # The form can only be mangled by the end-user, so
                    # just ignore any poisoning issue if it exists.
                    continue
                shippingrun = getUtility(IShippingRunSet).get(shippingrun_id)
                shippingrun.sentforshipping = True
                break
        flush_database_updates()

    def sent_exports(self):
        """Return all exports that were sent to the shipping companies."""
        return getUtility(IShippingRunSet).getShipped()

    def unsent_exports(self):
        """Return all exports that weren't sent to the shipping companies."""
        return getUtility(IShippingRunSet).getUnshipped()

    def no_exports(self):
        """Return True if there's no generated exports."""
        return not (self.unsent_exports() or self.sent_exports())


class ShipItNavigation(Navigation):

    usedfor = IShipItApplication

    # Support bookmarks to the old shipit application that used cgi scripts.
    redirection('user.cgi', '.', status=301)

    @stepto('requests')
    def requests(self):
        # XXX: permission=launchpad.Admin
        return getUtility(IShippingRequestSet)

    @stepto('standardoptions')
    def standardoptions(self):
        # XXX: permission=launchpad.Admin
        return getUtility(IStandardShipItRequestSet)


class ShippingRequestSetNavigation(Navigation):

    usedfor = IShippingRequestSet

    def traverse(self, name):
        return self.context.get(name)


class StandardShipItRequestSetNavigation(Navigation):

    usedfor = IStandardShipItRequestSet

    def traverse(self, name):
        return self.context.get(name)

