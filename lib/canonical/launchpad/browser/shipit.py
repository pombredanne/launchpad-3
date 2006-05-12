# Copyright 2005 Canonical Ltd

__metaclass__ = type

__all__ = [
    'StandardShipItRequestAddView', 'ShippingRequestApproveOrDenyView',
    'ShippingRequestsView', 'ShipItLoginView', 'ShipItRequestView',
    'ShipItUnauthorizedView', 'StandardShipItRequestsView',
    'ShippingRequestURL', 'StandardShipItRequestURL', 'ShipItExportsView',
    'ShipItNavigation', 'ShipItReportsView', 'ShippingRequestAdminView',
    'StandardShipItRequestSetNavigation', 'ShippingRequestSetNavigation']


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
from canonical.launchpad.helpers import intOrZero, get_email_template
from canonical.launchpad.webapp.error import SystemErrorView
from canonical.launchpad.webapp.login import LoginOrRegister
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp import (
    canonical_url, Navigation, stepto, redirection)
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces.validation import shipit_postcode_required
from canonical.launchpad.interfaces import (
    IStandardShipItRequestSet, IShippingRequestSet, ILaunchBag,
    ShippingRequestStatus, ILaunchpadCelebrities, ICanonicalUrlData,
    IShippingRunSet, IShipItApplication, IShipItReportSet, UnexpectedFormData)
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
    forbidden_page = ViewPageTemplateFile('../templates/shipit-forbidden.pt')

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

    possible_origins = {
        ShipItFlavour.UBUNTU: 'shipit-ubuntu',
        ShipItFlavour.KUBUNTU: 'shipit-kubuntu',
        ShipItFlavour.EDUBUNTU: 'shipit-edubuntu'}
        
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.flavour = _get_flavour_from_layer(request)
        self.origin = self.possible_origins[self.flavour]

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


def _get_flavour_from_layer(request):
    """Check what ShipIt Layer the given request provides and return the
    ShipItFlavour corresponding to that layer.
    """
    if ShipItUbuntuLayer.providedBy(request):
        return ShipItFlavour.UBUNTU
    elif ShipItEdUbuntuLayer.providedBy(request):
        return ShipItFlavour.EDUBUNTU
    elif ShipItKUbuntuLayer.providedBy(request):
        return ShipItFlavour.KUBUNTU
    else:
        raise AssertionError(
            'This request must provide one of ShipItEdUbuntuLayer, '
            'ShipItKUbuntuLayer or ShipItUbuntuLayer')


class ShipItRequestView(GeneralFormView):
    """The view for people to create/edit ShipIt requests."""

    from_email_addresses = {
        ShipItFlavour.UBUNTU: config.shipit.shipit_ubuntu_from_email,
        ShipItFlavour.EDUBUNTU: config.shipit.shipit_edubuntu_from_email,
        ShipItFlavour.KUBUNTU: config.shipit.shipit_kubuntu_from_email}

    def __init__(self, context, request):
        GeneralFormView.__init__(self, context, request)
        self.flavour = _get_flavour_from_layer(request)
        self.from_email_address = self.from_email_addresses[self.flavour]

    @property
    def is_edubuntu(self):
        return self.flavour == ShipItFlavour.EDUBUNTU

    @property
    def is_kubuntu(self):
        return self.flavour == ShipItFlavour.KUBUNTU

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
        """The current order's StandardShipItRequest id, or None.
        
        If there's no current order or the current order doesn't contain any
        CDs of self.flavour, None will be returned.
        """
        if self.current_order is None:
            return None

        quantities = self.current_order.getQuantitiesByFlavour(self.flavour)
        # self.current_order may contain no requested CDs for self.flavour,
        # and then quantities will be None.
        if quantities is None:
            return None

        x86_cds = quantities[ShipItArchitecture.X86]
        amd64_cds = quantities[ShipItArchitecture.AMD64]
        ppc_cds = quantities[ShipItArchitecture.PPC]

        # Any of {x86,amd64,ppc}_cds can be None here, so we use a default
        # value for getattr to make things easier.
        x86_quantity = getattr(x86_cds, 'quantity', 0)
        amd64_quantity = getattr(amd64_cds, 'quantity', 0)
        ppc_quantity = getattr(ppc_cds, 'quantity', 0)

        standard = getUtility(IStandardShipItRequestSet).getByNumbersOfCDs(
            self.flavour, x86_quantity, amd64_quantity, ppc_quantity)

        if standard is None:
            return None
        else:
            return standard.id

    @cachedproperty('_current_order')
    def current_order(self):
        return self.user.currentShipItRequest()

    def process_form(self):
        """Overwrite GeneralFormView's process_form() method because we want
        to be able to have a 'Cancel' button in a different <form> element.
        """
        if 'cancel' in self.request.form:
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
        reason = kw.get('reason')
        if not current_order:
            current_order = getUtility(IShippingRequestSet).new(
                self.user, kw.get('recipientdisplayname'), kw.get('country'),
                kw.get('city'), kw.get('addressline1'), kw.get('phone'),
                kw.get('addressline2'), kw.get('province'), kw.get('postcode'),
                kw.get('organization'), reason)
            if self.user.shippedShipItRequestsOfCurrentRelease() or reason:
                need_notification = True
        else:
            if current_order.reason is None and reason is not None:
                # The user entered something in the 'reason' entry for the
                # first time. We need to mark this order as pending approval
                # and send an email to the shipit admins.
                need_notification = True
            for name in self.fieldNames:
                setattr(current_order, name, kw.get(name))

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
        return (
            'Request accepted. Please note that requests usually take from '
            '4 to 6 weeks to deliver, depending on the country of shipping.')

    def validate(self, data):
        errors = []
        # We use a custom template with some extra widgets, so we have to
        # cheat here and access self.request.form
        if not self.request.form.get('ordertype'):
            errors.append(UnexpectedFormData(_(
                'The number of requested CDs was not provided.')))

        country = data['country']
        if shipit_postcode_required(country) and not data['postcode']:
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
        shipped_requests = recipient.shippedShipItRequestsOfCurrentRelease()
        replacements = {'recipientname': order.recipientdisplayname,
                        'recipientemail': recipient.preferredemail.email,
                        'requesturl': canonical_url(order),
                        'shipped_requests': shipped_requests.count(),
                        'reason': order.reason}
        message = get_email_template('shipit-custom-request.txt') % replacements
        shipit_admins = config.shipit.shipit_admins_email
        simple_sendmail(
            self.from_email_address, shipit_admins, subject, message, headers)


class ShippingRequestsView:
    """The view to list ShippingRequests that match a given criteria."""

    submitted = False
    selectedStatus = 'pending'
    selectedFlavour = 'any'
    recipient_text = ''

    def standardShipItRequests(self):
        """Return a list with all standard ShipIt Requests."""
        return getUtility(IStandardShipItRequestSet).getAll()

    def all_flavours(self):
        return ShipItFlavour.items

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
        self.selectedFlavour = request.get('flavourfilter')
        if self.selectedFlavour == 'any':
            flavour = None
        else:
            flavour = ShipItFlavour.items[self.selectedFlavour]

        orderby = str(request.get('orderby'))
        self.recipient_text = request.get('recipient_text')
        results = requestset.search(
            status=status, flavour=flavour, recipient_text=self.recipient_text,
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
        isdefault = data.get('isdefault')
        request = getUtility(IStandardShipItRequestSet).new(
            flavour, quantityx86, quantityamd64, quantityppc, isdefault)
        notify(ObjectCreatedEvent(request))


class ShippingRequestAdminMixinView:
    """Basic functionality for administering a ShippingRequest.

    Any class that inherits from this one should also inherit from
    GeneralFormView, or another class that stores the widgets as instance
    attributes, named like fieldname_widget.
    """

    # The name of the RequestedCDs' attribute from where we get the number we
    # use as initial value to our quantity widgets.
    quantity_attrname = None

    # This is the order in which we display the distribution flavours
    # in the UI
    ordered_flavours = [
        ShipItFlavour.UBUNTU, ShipItFlavour.KUBUNTU, ShipItFlavour.EDUBUNTU]

    # This is the order in which we display the quantity widgets for each
    # flavour in the UI
    ordered_architectures = [
        ShipItArchitecture.X86, ShipItArchitecture.AMD64,
        ShipItArchitecture.PPC]

    def widgetsMatrixWithFlavours(self):
        """Return a matrix in which each row contains a ShipItFlavour and one
        quantity widget for each ShipItArchitecture that we ship CDs. 

        The architectures of CDs that we ship are dependent on the
        flavour.

        The matrix returned by this method is meant to be used by the
        quantity_widgets macro, defined in templates/shipit-macros.pt.
        """
        matrix = []
        for flavour in self.ordered_flavours:
            row = [flavour.title]
            for arch in self.ordered_architectures:
                widget_name = self.quantity_fields_mapping[flavour][arch]
                if widget_name is not None:
                    widget_name += '_widget'
                    row.append(getattr(self, widget_name))
                else:
                    row.append(None)
            matrix.append(row)
        return matrix

    def getQuantityWidgetsInitialValuesFromExistingOrder(self, order):
        initial = {}
        requested = order.getRequestedCDsGroupedByFlavourAndArch()
        for flavour in self.quantity_fields_mapping:
            for arch in self.quantity_fields_mapping[flavour]:
                field_name = self.quantity_fields_mapping[flavour][arch]
                if field_name is None:
                    continue
                requested_cds = requested[flavour][arch]
                if requested_cds is not None:
                    value = getattr(requested_cds, self.quantity_attrname)
                else:
                    value = 0
                initial[field_name] = value
        return initial


class ShippingRequestApproveOrDenyView(
        GeneralFormView, ShippingRequestAdminMixinView):
    """The page where admins can Approve/Deny existing requests."""

    quantity_attrname = 'quantityapproved'

    quantity_fields_mapping = {
        ShipItFlavour.UBUNTU:
            {ShipItArchitecture.X86: 'ubuntu_quantityx86approved',
             ShipItArchitecture.PPC: 'ubuntu_quantityppcapproved',
             ShipItArchitecture.AMD64: 'ubuntu_quantityamd64approved'},
        ShipItFlavour.KUBUNTU:
            {ShipItArchitecture.X86: 'kubuntu_quantityx86approved',
             ShipItArchitecture.PPC: None,
             ShipItArchitecture.AMD64: 'kubuntu_quantityamd64approved'},
        ShipItFlavour.EDUBUNTU:
            {ShipItArchitecture.X86: 'edubuntu_quantityx86approved',
             ShipItArchitecture.PPC: None,
             ShipItArchitecture.AMD64: None}
        }

    def process(self, *args, **kw):
        """Process the submitted form.

        Depending on the button used to submit the form, this method will
        Approve, Deny or Change the approved quantities of this shipit request.
        """
        context = self.context
        form = self.request.form

        if 'DENY' not in form:
            quantities = {}
            for flavour in self.quantity_fields_mapping:
                quantities[flavour] = {}
                for arch in self.quantity_fields_mapping[flavour]:
                    field_name = self.quantity_fields_mapping[flavour][arch]
                    if field_name is None:
                        # We don't ship this arch for this flavour
                        continue
                    quantities[flavour][arch] = kw[field_name]

        if 'APPROVE' in form:
            context.approve(whoapproved=getUtility(ILaunchBag).user)
            context.highpriority = kw['highpriority']
            context.setApprovedQuantities(quantities)
            self._nextURL = self._makeNextURL(previous_action='approved')
        elif 'CHANGE' in form:
            context.highpriority = kw['highpriority']
            context.setApprovedQuantities(quantities)
            self._nextURL = self._makeNextURL(previous_action='changed')
        elif 'DENY' in form:
            context.deny()
            self._nextURL = self._makeNextURL(previous_action='denied')
        else:
            # Nothing to do.
            pass

    def submitted(self):
        # Overwrite GeneralFormView.submitted() because we have several
        # buttons on this page.
        form = self.request.form
        return 'APPROVE' in form or 'CHANGE' in form or 'DENY' in form

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
    def quantities_matrix(self):
        """Return a matrix of Flavours x Architectures where the values are
        the requested quantities for CDs of that Flavour and Architecture.
        """
        matrix = []
        quantities = self.context.getRequestedCDsGroupedByFlavourAndArch()
        for flavour in self.ordered_flavours:
            total = 0
            flavour_quantities = []
            for arch in self.ordered_architectures:
                requested_cds = quantities[flavour][arch]
                if requested_cds is not None:
                    quantity = requested_cds.quantity
                else:
                    quantity = 0
                total += quantity
                flavour_quantities.append(quantity)
            if total > 0:
                matrix.append([flavour.title] + flavour_quantities)
        return matrix

    @property
    def initial_values(self):
        order = self.context
        initial = self.getQuantityWidgetsInitialValuesFromExistingOrder(order)
        initial['highpriority'] = order.highpriority
        return initial

    def recipientHasOtherShippedRequests(self):
        """Return True if the recipient has other requests that were already
        sent to the shipping company."""
        recipient = self.context.recipient
        shipped_requests = recipient.shippedShipItRequestsOfCurrentRelease()
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

    quantity_attrname = 'quantity'

    quantity_fields_mapping = {
        ShipItFlavour.UBUNTU:
            {ShipItArchitecture.X86: 'ubuntu_quantityx86',
             ShipItArchitecture.PPC: 'ubuntu_quantityppc',
             ShipItArchitecture.AMD64: 'ubuntu_quantityamd64'},
        ShipItFlavour.KUBUNTU:
            {ShipItArchitecture.X86: 'kubuntu_quantityx86',
             ShipItArchitecture.PPC: None,
             ShipItArchitecture.AMD64: 'kubuntu_quantityamd64'},
        ShipItFlavour.EDUBUNTU:
            {ShipItArchitecture.X86: 'edubuntu_quantityx86',
             ShipItArchitecture.PPC: None,
             ShipItArchitecture.AMD64: None}
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
        if self.current_order is None:
            return {}

        order = self.current_order
        initial = self.getQuantityWidgetsInitialValuesFromExistingOrder(order)
        initial['highpriority'] = order.highpriority

        for field in self.shipping_details_fields:
            initial[field] = getattr(order, field)

        return initial

    def validate(self, data):
        # XXX: Even shipit admins shouldn't be allowed to make requests with 0
        # CDs. We need to check this here.
        # Guilherme Salgado, 2006-04-21
        errors = []
        country = data['country']
        if shipit_postcode_required(country) and not data['postcode']:
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
            msg = 'New request created successfully: %d' % current_order.id
        else:
            for name in self.shipping_details_fields:
                setattr(current_order, name, kw[name])
            msg = 'Request %d changed' % current_order.id

        quantities = {}
        for flavour in self.quantity_fields_mapping:
            quantities[flavour] = {}
            for arch in self.quantity_fields_mapping[flavour]:
                field_name = self.quantity_fields_mapping[flavour][arch]
                if field_name is None:
                    # We don't ship this arch for this flavour
                    continue
                quantities[flavour][arch] = intOrZero(kw[field_name])

        current_order.highpriority = kw['highpriority']
        current_order.setQuantities(quantities)
        if not current_order.isApproved():
            current_order.approve()
        self._nextURL = canonical_url(current_order)
        self.request.response.addNotification(msg)


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

