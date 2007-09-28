# Copyright 2005 Canonical Ltd.  All rights reserved.

__all__ = ['IStandardShipItRequest', 'IStandardShipItRequestSet',
           'IRequestedCDs', 'IShippingRequest', 'IShippingRequestSet',
           'IShipment', 'IShippingRun', 'IShipItCountry', 'IShippingRunSet',
           'IShipmentSet', 'ShippingRequestPriority', 'IShipItReport',
           'IShipItReportSet', 'IShippingRequestAdmin', 'IShippingRequestEdit',
           'SOFT_MAX_SHIPPINGRUN_SIZE', 'ShipItConstants',
           'IShippingRequestUser', 'MAX_CDS_FOR_UNTRUSTED_PEOPLE',
           'ShipItDistroSeries', 'ShipItArchitecture', 'ShipItFlavour',
           'ShippingService', 'ShippingRequestStatus', 'ShippingRequestType']

from zope.schema import Bool, Choice, Int, Datetime, TextLine
from zope.interface import Interface, Attribute, implements
from zope.schema.interfaces import IChoice
from zope.app.form.browser.itemswidgets import DropdownWidget

from canonical.lazr import DBEnumeratedType, DBItem

from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.interfaces.validation import (
    validate_shipit_recipientdisplayname, validate_shipit_phone,
    validate_shipit_city, validate_shipit_addressline1,
    validate_shipit_addressline2, validate_shipit_organization,
    validate_shipit_province, validate_shipit_postcode)
from canonical.launchpad.fields import (
    ShipItRecipientDisplayname, ShipItOrganization, ShipItCity,
    ShipItProvince, ShipItAddressline1, ShipItAddressline2, ShipItPhone,
    ShipItReason, ShipItQuantity)

from canonical.launchpad import _

# The maximum number of requests in a single shipping run
SOFT_MAX_SHIPPINGRUN_SIZE = 10000

MAX_CDS_FOR_UNTRUSTED_PEOPLE = 5


class ShippingRequestStatus(DBEnumeratedType):
    """The status of a given ShippingRequest."""

    PENDING = DBItem(0, """
        Pending

        The request is pending approval.
        """)

    APPROVED = DBItem(1, """
        Approved (unshipped)

        The request is approved but not yet sent to the shipping company.
        """)

    DENIED = DBItem(2, """
        Denied

        The request is denied.
        """)

    CANCELLED = DBItem(3, """
        Cancelled

        The request is cancelled.
        """)

    SHIPPED = DBItem(4, """
        Approved (shipped)

        The request was sent to the shipping company.
        """)

    PENDINGSPECIAL = DBItem(5, """
        Pending Special Consideration

        This request needs special consideration.
        """)

    DUPLICATEDADDRESS = DBItem(6, """
        Pending Special Consideration (dupe address)

        This request needs special consideration because other users already
        requested CDs to the same address.
        """)


class ShippingService(DBEnumeratedType):
    """The Shipping company we use to ship CDs."""

    TNT = DBItem(1, """
        TNT

        The TNT shipping company.
        """)

    SPRING = DBItem(2, """
        Spring

        The Spring shipping company.
        """)


class ShipItFlavour(DBEnumeratedType):
    """The Distro Flavour, used only to link with ShippingRequest."""

    UBUNTU = DBItem(1, """
        Ubuntu

        The Ubuntu flavour.
        """)

    KUBUNTU = DBItem(2, """
        Kubuntu

        The Kubuntu flavour.
        """)

    EDUBUNTU = DBItem(3, """
        Edubuntu

        The Edubuntu flavour.
        """)


class ShipItArchitecture(DBEnumeratedType):
    """The Distro Architecture, used only to link with ShippingRequest."""

    X86 = DBItem(1, """
        PC

        Intel/X86 processors.
        """)

    AMD64 = DBItem(2, """
        64-bit PC

        AMD64 or EM64T based processors.
        """)

    PPC = DBItem(3, """
        Mac

        PowerPC processors.
        """)


class ShippingRequestType(DBEnumeratedType):
    """The type of a ShippingRequest."""

    CUSTOM = DBItem(1, """
        Custom

        A request in which the recipient specified how many CDs they want.
        """)

    STANDARD = DBItem(2, """
        Standard

        A request in which the recipient chose the number of CDs from one of
        our predefined options.
        """)


class ShipItDistroSeries(DBEnumeratedType):
    """The Distro Release, used only to link with ShippingRequest."""

    BREEZY = DBItem(1, """
        5.10 (Breezy Badger)

        The Breezy Badger release.
        """)

    DAPPER = DBItem(2, """
        6.06 LTS (Dapper Drake)

        The Dapper Drake lont-term-support release.
        """)

    EDGY = DBItem(3, """
        6.10 (Edgy Eft)

        The Edgy Eft release.
        """)

    FEISTY = DBItem(4, """
        7.04 (Feisty Fawn)

        The Feisty Fawn release.
        """)

    GUTSY = DBItem(5, """
        7.10 (Gutsy Gibbon)

        The Gutsy Gibbon release.
        """)


def _validate_positive_int(value):
    """Return True if the given value is a positive integer.

    If it's not a positive integer, then raise a LaunchpadValidationError.
    You must not pass non-unicode type objects to this function.
    """
    assert isinstance(value, int)
    if value < 0:
        raise LaunchpadValidationError(_(
            "Quantities must be greater than or equal 0."))
    else:
        return True


class ShipItConstants:
    ubuntu_url = 'https://shipit.ubuntu.com'
    kubuntu_url = 'https://shipit.kubuntu.com'
    edubuntu_url = 'https://shipit.edubuntu.com'
    current_distroseries = ShipItDistroSeries.GUTSY
    max_size_for_auto_approval = 16


class IEmptyDefaultChoice(IChoice):
    pass


class EmptyDefaultChoice(Choice):
    implements(IEmptyDefaultChoice)


# XXX Guilherme Salgado 2005-10-03:
# This sould probably be moved somewhere else, but as I need to get this
# in production ASAP I'm leaving it here for now.
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

    country = EmptyDefaultChoice(
        title=_('Country'), required=True, vocabulary='CountryName')


class IShippingRequest(Interface):
    """A shipping request."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    recipient = Int(title=_('Recipient'), required=True, readonly=True)

    daterequested = Datetime(
        title=_('Date of Request'), required=True, readonly=True)

    status = Choice(title=_('Request Status'), required=True, readonly=False,
                    vocabulary=ShippingRequestStatus)

    whoapproved = Int(
        title=_('Who Approved'), required=False, readonly=False,
        description=_('Automatically approved or someone approved?'))

    whocancelled = Int(
        title=_('Who Cancelled'), required=False, readonly=False)

    reason = ShipItReason(
        title=_('Want more CDs?'), required=True, readonly=False,
        description=_("If none of the options above suit your needs, please "
                      "explain here how many CDs you want and why."))

    highpriority = Bool(
        title=_('High Priority?'), required=False, readonly=False,
        description=_('Is this a high priority request?'))

    recipientdisplayname = ShipItRecipientDisplayname(
            title=_('Name'), required=True, readonly=False,
            constraint=validate_shipit_recipientdisplayname,
            description=_("The name of the person who's going to receive "
                          "this order.")
            )
    addressline1 = ShipItAddressline1(
            title=_('Address'), required=True, readonly=False,
            constraint=validate_shipit_addressline1,
            description=_('The address to where the CDs will be shipped '
                          '(Line 1)')
            )
    addressline2 = ShipItAddressline2(
            title=_(''), required=False, readonly=False,
            constraint=validate_shipit_addressline2,
            description=_('The address to where the CDs will be shipped '
                          '(Line 2)')
            )
    city = ShipItCity(
            title=_('City/Town/etc'), required=True, readonly=False,
            constraint=validate_shipit_city,
            description=_('The City/Town/Village/etc to where the CDs will be '
                          'shipped.')
            )
    province = ShipItProvince(
            title=_('State/Province'), required=False, readonly=False,
            constraint=validate_shipit_province,
            description=_('The State/Province/etc to where the CDs will be '
                          'shipped.')
            )
    country = EmptyDefaultChoice(
            title=_('Country'), required=True, readonly=False,
            vocabulary='CountryName',
            description=_('The Country to where the CDs will be shipped.')
            )
    postcode = TextLine(
            title=_('Postcode'), required=False, readonly=False,
            constraint=validate_shipit_postcode,
            description=_('The Postcode to where the CDs will be shipped.')
            )
    phone = ShipItPhone(
            title=_('Phone'), required=True, readonly=False,
            constraint=validate_shipit_phone,
            description=_('[(+CountryCode) number] e.g. (+55) 16 33619445')
            )
    organization = ShipItOrganization(
            title=_('Organization'), required=False, readonly=False,
            constraint=validate_shipit_organization,
            description=_('The Organization requesting the CDs')
            )
    normalized_address = TextLine(
            title=_("This request's normalized address"),
            description=_("This request's address, city, province and "
                          "postcode normalized and concatenated"))

    distroseries = Attribute(_(
        "The ShipItDistroSeries of the CDs contained in this request"))
    recipient_email = Attribute(_("The recipient's email address."))
    shipment = Int(title=_(
        "The request's Shipment or None if the request wasn't shipped yet."),
        readonly=True, required=True
        )
    countrycode = Attribute(
        _("The iso3166code2 code of this request's country. Can't be None."))
    shippingservice = Attribute(
        _("The shipping service used to ship this request. Can't be None."))
    status_desc = Attribute(_("A text description of this request's status."))

    def getTotalCDs():
        """Return the total number of CDs in this request."""

    def getTotalApprovedCDs():
        """Return the total number of approved CDs in this request."""

    def getContainedFlavours():
        """Return a set with all the flavours contained in this request.

        A request is said to contain a given flavour if the quantity of
        requested CDs of that flavour on this request is greater than 0.
        """

    def getAllRequestedCDs():
        """Return all RequestedCDs of this ShippingRequest."""

    def getRequestedCDsGroupedByFlavourAndArch():
        """Return a dictionary mapping ShipItFlavours and ShipItArchitectures
        to the RequestedCDs objects of that architecture and flavour.
        """

    def getQuantitiesOfFlavour(flavour):
        """Return a dictionary mapping architectures to the quantity of
        requested CDs of the given flavour.
        """

    def containsCustomQuantitiesOfFlavour(flavour):
        """Return True if this order contains custom quantities of CDs of the
        given flavour.
        """

    def setQuantities(quantities):
        """Set the quantities of this request by either creating new
        RequestedCDs objects or changing existing ones.

        :quantities: must be a dictionary mapping flavours to architectures
                     and quantities, i.e.
                     {ShipItFlavour.UBUNTU:
                        {ShipItArchitecture.X86: quantity1,
                         ShipItArchitecture.PPC: quantity2}
                     }
        """

    def setApprovedQuantities(quantities):
        """Set the approved quantities using the given values.

        :quantities: must be a dictionary mapping flavours to architectures
                     and quantities, i.e.
                     {ShipItFlavour.UBUNTU:
                        {ShipItArchitecture.X86: quantity1,
                         ShipItArchitecture.PPC: quantity2}
                     }

        You must not set approved quantities on a non-approved request.
        """

    def setRequestedQuantities(quantities):
        """Set the requested quantities using the given values.

        :quantities: must be a dictionary mapping flavours to architectures
                     and quantities, i.e.
                     {ShipItFlavour.UBUNTU:
                        {ShipItArchitecture.X86: quantity1,
                         ShipItArchitecture.PPC: quantity2}
                     }

        You must not set requested quantities on a shipped/cancelled request.
        """

    def isAwaitingApproval():
        """Return True if this request's status is PENDING."""

    def isDuplicatedAddress():
        """Return True if this request's status is DUPLICATEDADDRESS."""

    def isPendingSpecial():
        """Return True if this request's status is PENDINGSPECIAL."""

    def isDenied():
        """Return True if this request's status is DENIED."""

    def isShipped():
        """Return True if this request's status is SHIPPED."""

    def isApproved():
        """Return True if this request's status is APPROVED."""

    def isCancelled():
        """Return True if this request's status is CANCELLED."""

    def canBeApproved():
        """Can this request be approved?

        Only PENDING, PENDINGSPECIAL and DENIED requests can be denied.
        """

    def canBeDenied():
        """Can this request be denied?

        Only APPROVED, PENDING and PENDINGSPECIAL requests can be denied.
        """

    def markAsDuplicatedAddress():
        """Mark this request as having a duplicated address."""

    def markAsPendingSpecial():
        """Mark this request as pending special consideration."""

    def deny():
        """Deny this request."""

    def clearApproval():
        """Mark this request as waiting for approval.

        You must not use this method on non-approved requests.
        """

    def clearApprovedQuantities():
        """Set all approved quantities of this request to 0.

        You must not use this method on approved requests.
        """

    def approve(whoapproved=None):
        """Approve this request with the exact quantities as it was submitted.

        This will set the approved attribute to True and the whoapproved
        attribute to whoapproved. If whoapproved is None, that means this
        request was auto approved.

        This method can only be called on non-cancelled non-approved requests.
        """

    def cancel(whocancelled):
        """Cancel this request.

        This is done by setting cancelled=True and whocancelled=whocancelled
        on this request.
        This method will also set quantityx86approved, quantityppcapproved,
        quantityamd64approved, approved and whoapproved to None.
        """

    def addressIsDuplicated():
        """Return True if there is one or more requests made from another
        user using the same address and distroseries as this one.
        """

    def getRequestsWithSameAddressFromOtherUsers():
        """Return all non-cancelled non-denied requests with the same address
        and distroseries as this one but with a different recipient.
        """


class IShippingRequestSet(Interface):
    """The set of all ShippingRequests"""

    def new(recipient, recipientdisplayname, country, city, addressline1,
            phone, addressline2=None, province=None, postcode=None,
            organization=None, reason=None):
        """Create and return a new ShippingRequest.

        You must not create a new request for a recipient that already has a
        currentShipItRequest, unless the recipient is the shipit_admin
        celebrity. Refer to IPerson.currentShipItRequest() for more
        information about what is a current request.
        """

    def processRequests(status, new_status):
        """Change the status of requests with the given status to the new one.

        Also sends an email to the shipit admins listing all requests that
        were processed.
        """

    def exportRequestsToFiles(
            priority, ztm,
            distroseries=ShipItConstants.current_distroseries):
        """Export all approved, unshipped and non-cancelled into CSV files.

        Group approved, unshipped and non-cancelled requests into one or more
        ShippingRuns with at most SOFT_MAX_SHIPPINGRUN_SIZE requests each
        and for each ShippingRun export it into a CSV file and upload it to
        the Librarian.
        """

    def getOldestPending():
        """Return the oldest request with status PENDING.

        Return None if there's no requests with status PENDING.
        """

    def getTotalsForRequests(requests):
        """Return the requested and approved totals of the given requests.

        The return value is a dictionary of the form
        {request.id: (total_requested, total_approved)}.

        This method is meant to be used when listing a large numbers of
        requests, to avoid issuing queries on the RequestedCDs table for each
        request listed.
        """

    def getUnshippedRequestsIDs(
            priority, distroseries=ShipItConstants.current_distroseries):
        """Return the ID of all requests that are eligible for shipping.

        These are approved requests that weren't shipped yet.
        """

    def get(id, default=None):
        """Return the ShippingRequest with the given id.

        Return the default value if there's no ShippingRequest with this id.
        """

    def search(status=None, flavour=None, distroseries=None,
               recipient_text=None, include_cancelled=False):
        """Search for requests that match the given arguments."""

    def generateShipmentSizeBasedReport(current_series_only=False):
        """Generate a csv file with the size of shipments and the number of
        shipments of that size.

        If current_series_only is True, then include only requests for CDs of
        ShipItConstants.current_distroseries.
        """

    def generateCountryBasedReport(current_series_only=False):
        """Generate a csv file with statiscs about orders placed by country.

        If current_series_only is True, then include only requests for CDs of
        ShipItConstants.current_distroseries.
        """

    def generateWeekBasedReport(
            start_date, end_date, only_current_distroseries=False):
        """Generate a csv file with statistics about orders placed by week.

        If only_current_distroseries is True, then the requests included will
        be limited to those for CDs of ShipItConstants.current_distroseries.

        Only the orders placed between the first monday prior to start_date
        and the first sunday prior to end_date are considered.
        """

    def generateRequestDistributionReport():
        """Generate a csv file with the distribution of requests and shipments.

        For the current series, there will be 4 columns displaying the number
        of requests/shipments and the number of users which had that exact
        number of requests/shipments. The previous series we do the same but
        for requests/shipments across all series and only include people
        which requested the current series.
        """


class IRequestedCDs(Interface):

    request = Int(title=_('The ShippingRequest'), required=True, readonly=True)
    distroseries = Int(title=_('Series'), required=True, readonly=True)
    flavour = Choice(title=_('Distro Flavour'), required=True, readonly=True,
                     vocabulary=ShipItFlavour)
    architecture = Int(title=_('Architecture'), required=True, readonly=True)
    quantity = Int(
        title=_('The number of CDs'), required=True, readonly=False,
        description=_('Number of requested CDs for this architecture.'),
        constraint=_validate_positive_int)
    quantityapproved = Int(
        title=_('Quantity Approved'), required=False, readonly=False,
        description=_('Number of approved CDs for this architecture.'),
        constraint=_validate_positive_int)
    description = Attribute(_('A text description of this IRequestedCDs.'))


class IStandardShipItRequest(Interface):
    """A standard ShipIt request."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    flavour = Choice(title=_('Distribution Flavour'), required=True,
                     readonly=False, vocabulary=ShipItFlavour)
    quantityx86 = ShipItQuantity(
        title=_('PC CDs'), required=True, readonly=False,
        description=_('Number of PC CDs in this request.'),
        constraint=_validate_positive_int)

    quantityppc = ShipItQuantity(
        title=_('Mac CDs'), required=True, readonly=False,
        description=_('Number of Mac CDs in this request.'),
        constraint=_validate_positive_int)

    quantityamd64 = ShipItQuantity(
        title=_('64-bit PC CDs'), required=True, readonly=False,
        description=_('Number of 64-bit PC CDs in this request.'),
        constraint=_validate_positive_int)

    isdefault = Bool(
        title=_('Is this the default option?'),
        description=_('The default option is the one that is always '
                      'initially selected in the list of options the '
                      'user will see.'),
        required=False, readonly=False, default=False)

    quantities = Attribute(
        _('A dictionary mapping architectures to their quantities.'))
    totalCDs = Attribute(_('Total number of CDs in this request.'))
    user_description = TextLine(
        title=_('Description'), readonly=False, required=False,
        description=_(
            "This option's description. Leave it blank to use the default "
            "(e.g. 5 Ubuntu CDs (3 PC CDs, 2 64-bit PC CDs))."))
    description = TextLine(
        title=_('Description'), readonly=True, required=False,
        description=_(
            "If user_description is not empty it's used. Otherwise we "
            "generate a description based on the flavour and quantities"))

    def destroySelf():
        """Delete this object from the database."""


class IStandardShipItRequestSet(Interface):
    """The set of all standard ShipIt requests."""

    def new(flavour, quantityx86, quantityamd64, quantityppc, isdefault,
            description):
        """Create and return a new StandardShipItRequest."""

    def getByFlavour(flavour, user):
        """Return the standard ShipIt requests for the given flavour and user.

        If the given user is trusted in Shipit, then all options of that
        flavour are returned. Otherwise, only the options with less than
        MAX_CDS_FOR_UNTRUSTED_PEOPLE CDs are returned.

        To find out whether a user has made contributions or not, we use the
        is_trusted_on_shipit property of IPerson.
        """

    def get(id, default=None):
        """Return the StandardShipItRequest with the given id.

        Return the default value if nothing's found.
        """

    def getAllGroupedByFlavour():
        """Return a dictionary mapping ShipItFlavours to the
        StandardShipItRequests of that flavour.

        This is used in the admin interface to show all StandardShipItRequests
        to the shipit admins, so it doesn't need to check whether the user is
        trusted on shipit or not.
        """

    def getByNumbersOfCDs(flavour, quantityx86, quantityamd64, quantityppc):
        """Return the StandardShipItRequest with the given number of CDs for
        the given flavour.

        Return None if there's no StandardShipItRequest with the given number
        of CDs.
        """


class IShipment(Interface):
    """The shipment of a given request."""

    logintoken = TextLine(title=_('Token'), readonly=True, required=True)
    dateshipped = Datetime(
        title=_('Date Shipped'), readonly=True, required=True)
    shippingservice = Int(
        title=_('Shipping Service'), readonly=True, required=True)
    shippingrun = Int(title=_('Shipping Run'), readonly=True, required=True)
    request = Int(title=_('The ShipIt Request'), readonly=True, required=True)
    trackingcode = TextLine(
        title=_('Tracking Code'), readonly=True, required=False)


class IShipmentSet(Interface):
    """The set of Shipment objects."""

    def new(shippingservice, shippingrun, trackingcode=None, dateshipped=None):
        """Create a new Shipment object with the given arguments."""

    def getByToken(token):
        """Return the Shipment with the given token or None if it doesn't
        exist.
        """


class IShippingRun(Interface):
    """A set of requests that were sent to shipping at the same date."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    datecreated = Datetime(
        title=_('Date of Creation'), required=True, readonly=True)

    csvfile = Int(
        title=_('A csv file with all requests of this run.'),
        required=False, readonly=False)

    sentforshipping = Bool(
        title=_('Was this ShippingRun sent for shipping?'),
        required=False, readonly=False)

    requests = Attribute(_('All requests that are part of this shipping run.'))

    requests_count = Int(
        title=_('A cache of the number of requests'), readonly=False,
        description=_('This is necessary to avoid a COUNT(*) query which is '
                      'very expensive in this case, as we have lots of '
                      'requests on a ShippingRun'))

    def exportToCSVFile():
        """Generate a CSV file with all requests that are part of this
        shipping run, upload it to the Librarian and store the Librarian
        reference on the csvfile attribute.
        """


class IShippingRunSet(Interface):
    """The set of ShippingRun objects."""

    def new():
        """Create a new ShippingRun object."""

    def get(id):
        """Return the ShippingRun with the given id or None if it doesn't
        exist.
        """

    def getUnshipped():
        """Return all ShippingRuns that are not yet sent for shipping. """

    def getShipped():
        """Return all ShippingRuns that are already sent for shipping. """


class ShippingRequestPriority:
    """The priority of a given ShippingRequest."""

    HIGH = 'high'
    NORMAL = 'normal'


class IShipItReport(Interface):
    """A report based on shipit data."""

    datecreated = Datetime(
        title=_('Date of Creation'), required=True, readonly=True)

    csvfile = Int(
        title=_('A csv file with all requests of this run.'),
        required=True, readonly=True)


class IShipItReportSet(Interface):
    """The set of ShipItReport"""

    def new(csvfile):
        """Create a new ShipItReport object."""

    def getAll():
        """Return all ShipItReport objects."""


class IShippingRequestQuantities(Interface):
    """A schema used to render the quantity widgets for all different
    architectures and flavours.
    """

    ubuntu_quantityx86 = ShipItQuantity(
        title=_('PC'), description=_('Quantity of Ubuntu PC CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)
    ubuntu_quantityppc = ShipItQuantity(
        title=_('Mac'), description=_('Quantity of Ubuntu Mac CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)
    ubuntu_quantityamd64 = ShipItQuantity(
        title=_('64-bit PC'), description=_('Quantity of Ubuntu 64-bit PC CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)

    kubuntu_quantityx86 = ShipItQuantity(
        title=_('PC'), description=_('Quantity of Kubuntu PC CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)
    kubuntu_quantityamd64 = ShipItQuantity(
        title=_('64-bit PC'),
        description=_('Quantity of Kubuntu 64-bit PC CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)

    edubuntu_quantityx86 = ShipItQuantity(
        title=_('PC'), description=_('Quantity of Edubuntu PC CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)


class IShippingRequestUser(IShippingRequest, IShippingRequestQuantities):
    """A schema used to render and validate the page for shipit users to
    create/change ShippingRequests.
    """


class IShippingRequestAdmin(IShippingRequestQuantities):
    """A schema used to render and validate the page for shipit admins to
    create/change ShippingRequests.
    """

    highpriority = IShippingRequest.get('highpriority')
    recipientdisplayname = IShippingRequest.get('recipientdisplayname')
    addressline1 = IShippingRequest.get('addressline1')
    addressline2 = IShippingRequest.get('addressline2')
    city = IShippingRequest.get('city')
    province = IShippingRequest.get('province')
    country = IShippingRequest.get('country')
    postcode = IShippingRequest.get('postcode')
    phone = IShippingRequest.get('phone')
    organization = IShippingRequest.get('organization')


class IShippingRequestEdit(Interface):
    """A schema used to render and validate the page for shipit admins to
    approve/deny ShippingRequests.
    """

    ubuntu_quantityx86approved = ShipItQuantity(
        title=_('PC'), description=_('Quantity of Ubuntu X86 Approved CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)
    ubuntu_quantityppcapproved = ShipItQuantity(
        title=_('Mac'), description=_('Quantity of Ubuntu PPC Approved CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)
    ubuntu_quantityamd64approved = ShipItQuantity(
        title=_('64-bit PC'),
        description=_('Quantity of Ubuntu AMD64 Approved CDs'), required=False,
        readonly=False, constraint=_validate_positive_int)

    kubuntu_quantityx86approved = ShipItQuantity(
        title=_('PC'), description=_('Quantity of Kubuntu X86 Approved CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)
    kubuntu_quantityamd64approved = ShipItQuantity(
        title=_('64-bit PC'),
        description=_('Quantity of Kubuntu AMD64 Approved CDs'), required=False,
        readonly=False, constraint=_validate_positive_int)

    edubuntu_quantityx86approved = ShipItQuantity(
        title=_('PC'), description=_('Quantity of Edubuntu X86 Approved CDs'),
        required=False, readonly=False, constraint=_validate_positive_int)

    highpriority = IShippingRequest.get('highpriority')
