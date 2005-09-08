# Copyright 2005 Canonical Ltd.  All rights reserved.

__all__ = ['IStandardShipItRequest', 'IStandardShipItRequestSet',
           'IRequestedCDs', 'IShippingRequest', 'IShippingRequestSet',
           'ShippingRequestStatus']

from zope.schema import Bool, Int, Datetime, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


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

    totalCDs = Attribute(_('Total number of CDs in this request.'))
    quantityx86 = Int(title=_('Requested X86 CDs'), readonly=False)
    quantityppc = Int(title=_('Requested PowerPC CDs'), readonly=False)
    quantityamd64 = Int(title=_('Requested AMD64 CDs'), readonly=False)
    quantityx86approved = Int(title=_('Approved X86 CDs'), readonly=False)
    quantityppcapproved = Int(title=_('Approved PowerPC CDs'), readonly=False)
    quantityamd64approved = Int(title=_('Approved AMD64 CDs'), readonly=False)

    def isStandardRequest():
        """Return True if this is one of the Standard requests."""

    def clearApproval():
        """Mark this request as waiting for approval.

        This can only be used on approved requests.
        """

    def approve(whoapproved=None):
        """Approve this request with the exact quantities as it was submitted.

        This will set the approved attribute to True and the whoapproved
        attribute to whoapproved. If whoapproved is None, that means this
        request was auto approved.
        Also, the quantityx86approved, quantityppcapproved and
        quantityamd64approved will be changed to match the requested
        quantities.

        This method can only be called on non-cancelled requests. If a request
        is cancelled, it's necessary to reactivate() it first.
        """

    def cancel(whocancelled):
        """Cancel this request.
        
        This is done by setting cancelled=True and whocancelled=whocancelled
        on this request.
        This method will also set quantityx86approved, quantityppcapproved, 
        quantityamd64approved, approved and whoapproved to None.
        """

    def reactivate():
        """Reactivate this request, by unsetting its cancelled attribute.

        This will also unset the whocancelled attribute.

        This method can be called only on cancelled requests.
        """


class ShippingRequestStatus:
    """The status of a ShippingRequest."""

    UNAPPROVED = 'unapproved'
    APPROVED = 'approved'
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

