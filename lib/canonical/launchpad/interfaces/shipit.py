# Copyright 2005 Canonical Ltd.  All rights reserved.

__all__ = ['IStandardShipItRequest', 'IStandardShipItRequestSet',
           'IRequestedCDs', 'IShippingRequest', 'IShippingRequestSet',
           'ShippingRequestStatus', 'IShipItCountry']

from zope.schema import Bool, Choice, Int, Datetime, Text, TextLine
from zope.interface import Interface, Attribute, implements
from zope.schema.interfaces import IChoice
from zope.app.form.browser.itemswidgets import DropdownWidget

from canonical.launchpad import _


class IEmptyDefaultChoice(IChoice):
    pass


class EmptyDefaultChoice(Choice):
    implements(IEmptyDefaultChoice)


# XXX: This sould probably be moved somewhere else, but as I need to get this
# in production ASAP I'm leaving it here for now. -- Guilherme Salgado
# 2005-10-03
class EmptyDefaultDropdownWidget(DropdownWidget):
    """A dropdown widget in which the default option is one that is not part
    of its vocabulary.
    """
    firstItem = True

    def renderItems(self, value):
        items = DropdownWidget.renderItems(self, value)
        option = '<option value="">Choose one</option>'
        items.insert(0, option)
        return items


class IShipItCountry(Interface):
    """This schema is only to get the Country widget."""

    country = EmptyDefaultChoice(title=_('Country'), required=True, 
                     vocabulary='CountryName')


class IShippingRequest(Interface):
    """A shipping request."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    recipient = Int(title=_('Recipient'), required=True, readonly=True)

    shipment = Int(title=_('Shipment'), required=True, readonly=False)

    daterequested = Datetime(
        title=_('Date of Request'), required=True, readonly=True)

    shockandawe = Int(title=_('Shock And Awe'), required=False, readonly=True)

    approved = Bool(
        title=_('Is This Request Approved?'), required=False, readonly=False)

    whoapproved = Int(
        title=_('Who Approved'), required=False, readonly=False,
        description=_('Automatically approved or someone approved?'))

    cancelled = Bool(
        title=_('Cancelled?'), required=False, readonly=False,
        description=_('The user can decide to cancel his request, or '
                      'the ShipIt operator can do it.'))

    whocancelled = Int(
        title=_('Who Cancelled'), required=False, readonly=False)

    reason = Text(
        title=_('Reason'), required=False, readonly=False,
        description=_('People who requests things other than the standard '
                      'options have to explain why they need that.'))

    highpriority = Bool(
        title=_('High Priority?'), required=False, readonly=False,
        description=_('Is this a high priority request?'))

    recipientdisplayname = TextLine(
            title=_('Name'), required=False, readonly=False,
            description=_("The name of the person who's going to receive "
                          "this order.")
            )
    addressline1 = TextLine(
            title=_('Address'), required=True, readonly=False,
            description=_('The address to where the CDs will be shipped '
                          '(Line 1)')
            )
    addressline2 = TextLine(
            title=_('Address'), required=False, readonly=False,
            description=_('The address to where the CDs will be shipped '
                          '(Line 2)')
            )
    city = TextLine(
            title=_('City'), required=True, readonly=False,
            description=_('The City/Town/Village/etc to where the CDs will be '
                          'shipped.')
            )
    province = TextLine(
            title=_('Province'), required=True, readonly=False,
            description=_('The State/Province/etc to where the CDs will be '
                          'shipped.')
            )
    country = EmptyDefaultChoice(
            title=_('Country'), required=True, readonly=False,
            vocabulary='CountryName',
            description=_('The Country to where the CDs will be shipped.')
            )
    postcode = TextLine(
            title=_('Postcode'), required=True, readonly=False,
            description=_('The Postcode to where the CDs will be shipped.')
            )
    phone = TextLine(
            title=_('Phone'), required=True, readonly=False,
            description=_('[(+CountryCode) number] e.g. (+55) 16 33619445')
            )
    organization = TextLine(
            title=_('Organization'), required=False, readonly=False,
            description=_('The Organization requesting the CDs')
            )
    totalCDs = Attribute(_('Total number of CDs in this request.'))
    totalapprovedCDs = Attribute(
        _('Total number of approved CDs in this request.'))
    quantityx86 = Int(title=_('Requested X86 CDs'), readonly=False)
    quantityppc = Int(title=_('Requested PowerPC CDs'), readonly=False)
    quantityamd64 = Int(title=_('Requested AMD64 CDs'), readonly=False)
    quantityx86approved = Int(title=_('Approved X86 CDs'), readonly=False)
    quantityppcapproved = Int(title=_('Approved PowerPC CDs'), readonly=False)
    quantityamd64approved = Int(title=_('Approved AMD64 CDs'), readonly=False)
    recipientname = Attribute(_("The recipient's name"))

    def isStandardRequest():
        """Return True if this is one of the Standard requests."""

    def isDenied():
        """Return True if this request was denied.
        
        A denied request has self.approved == False, while a request that's
        pending approval has self.approved == None.
        """

    def highlightColour():
        """Return the colour to highlight this request if it's high priority.

        Return None otherwise.
        """

    def isAwaitingApproval():
        """Return True if this request is still waiting for approval."""

    def isApproved():
        """Return True if this request was approved."""

    def deny():
        """Deny this request."""

    def clearApproval():
        """Mark this request as waiting for approval.

        This method should be used only on approved requests.
        """

    def setApprovedTotals(quantityx86approved, quantityamd64approved,
                          quantityppcapproved):
        """Set the approved quantities using the given values.

        This method can be used only on approved requests.
        """

    def approve(quantityx86approved, quantityamd64approved,
                quantityppcapproved, whoapproved=None):
        """Approve this request with the exact quantities as it was submitted.

        This will set the approved attribute to True and the whoapproved
        attribute to whoapproved. If whoapproved is None, that means this
        request was auto approved.

        quantityx86approved, quantityxamd64pproved and quantityppcapproved
        must be positive integers.

        This method can only be called on non-cancelled non-approved requests.
        """

    def cancel(whocancelled):
        """Cancel this request.
        
        This is done by setting cancelled=True and whocancelled=whocancelled
        on this request.
        This method will also set quantityx86approved, quantityppcapproved, 
        quantityamd64approved, approved and whoapproved to None.
        """


class ShippingRequestStatus:
    """The status of a ShippingRequest."""

    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    ALL = 'all'


class IShippingRequestSet(Interface):
    """The set of all ShippingRequests"""

    def new(recipient, quantityx86, quantityamd64, quantityppc, reason=None,
            shockandawe=None):
        """Create and return a new ShippingRequest.
        
        This method can't be used if recipient already has a
        currentShipItRequest. Refer to IPerson.currentShipItRequest() for more
        information about what is a current request.
        """

    def getOldestPending():
        """Return the oldest request with status PENDING.
        
        Return None if there's no requests with status PENDING.
        """

    def get(id, default=None):
        """Return the ShippingRequest with the given id.
        
        Return the default value if there's no ShippingRequest with this id.
        """

    def searchCustomRequests(status=ShippingRequestStatus.ALL,
                             omit_cancelled=True):
        """Search for custom requests and return the ones that match."""

    def searchStandardRequests(status=ShippingRequestStatus.ALL,
                               omit_cancelled=True, standard_type=None):
        """Search for standard requests and return the ones that match.
        
        :standard_type: Either None or a StandardShipItRequest object. If it's
                        not None, the search is restricted to requests of that
                        StandardShipItRequest only.
        """


class IRequestedCDs(Interface):

    id = Int(title=_('The unique ID'), required=True, readonly=True)
    request = Int(title=_('The ShippingRequest'), required=True, readonly=True)
    distrorelease = Int(title=_('Distro Release'), required=True, readonly=True)
    flavour = Int(title=_('Distro Flavour'), required=True, readonly=True)
    architecture = Int(title=_('Architecture'), required=True, readonly=True)
    quantity = Int(
        title=_('The number of CDs'), required=True, readonly=False,
        description=_('Number of requested CDs for this architecture.'),
        constraint=lambda value: value >= 0)
    quantityapproved = Int(
        title=_('Quantity Approved'), required=False, readonly=False,
        description=_('Number of approved CDs for this architecture.'),
        constraint=lambda value: value >= 0)


class IStandardShipItRequest(Interface):
    """A standard ShipIt request."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    quantityx86 = Int(
        title=_('Intel/x86 CDs'), required=True, readonly=False,
        description=_('Number of Intel/x86 CDs in this request.'),
        constraint=lambda value: value >= 0)

    quantityppc = Int(
        title=_('PowerPC CDs'), required=True, readonly=False,
        description=_('Number of PowerPC CDs in this request.'),
        constraint=lambda value: value >= 0)

    quantityamd64 = Int(
        title=_('AMD64 CDs'), required=True, readonly=False,
        description=_('Number of AMD64 CDs in this request.'),
        constraint=lambda value: value >= 0)

    description = TextLine(
        title=_('Description'),
        description=_('A short description for this request (e.g. 10 CDs: '
                      '5 Intel/x86, 3 AMD64, 2 PowerPC'),
        required=True, readonly=False)

    isdefault = Bool(
        title=_('Is this the default request?'),
        description=_('The default request is the one that is always '
                      'initially selected in the list of options the '
                      'user will see.'),
        required=False, readonly=False, default=False)

    totalCDs = Attribute(_('Total number of CDs in this request.'))

    def destroySelf():
        """Delete this object from the database."""


class IStandardShipItRequestSet(Interface):
    """The set of all standard ShipIt requests."""

    def new(quantityx86, quantityamd64, quantityppc, description, isdefault):
        """Create and return a new StandardShipItRequest."""

    def getAll():
        """Return all standard ShipIt requests."""

    def get(id, default=None):
        """Return the StandardShipItRequest with the given id.
        
        Return the default value if nothing's found.
        """

    def getByNumbersOfCDs(quantityx86, quantityamd64, quantityppc):
        """Return the StandardShipItRequest with the given number of CDs.

        Return None if there's no StandardShipItRequest with the given number
        of CDs.
        """

