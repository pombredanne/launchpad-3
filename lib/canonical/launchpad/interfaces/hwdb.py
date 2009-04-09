# Copyright 2007, 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to the hardware database."""

__metaclass__ = type

__all__ = [
    'HWBus',
    'HWMainClass',
    'HWSubClass',
    'HWSubmissionFormat',
    'HWSubmissionKeyNotUnique',
    'HWSubmissionProcessingStatus',
    'IHWDBApplication',
    'IHWDevice',
    'IHWDeviceClass',
    'IHWDeviceClassSet',
    'IHWDeviceDriverLink',
    'IHWDeviceDriverLinkSet',
    'IHWDeviceNameVariant',
    'IHWDeviceNameVariantSet',
    'IHWDeviceSet',
    'IHWDriver',
    'IHWDriverSet',
    'IHWSubmission',
    'IHWSubmissionBug',
    'IHWSubmissionBugSet',
    'IHWSubmissionForm',
    'IHWSubmissionSet',
    'IHWSubmissionDevice',
    'IHWSubmissionDeviceSet',
    'IHWSystemFingerprint',
    'IHWSystemFingerprintSet',
    'IHWVendorID',
    'IHWVendorIDSet',
    'IHWVendorName',
    'IHWVendorNameSet',
    'IllegalQuery',
    'ParameterError',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    ASCIILine, Bool, Bytes, Choice, Datetime, Int, List, TextLine)
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import License
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

from lazr.restful.fields import CollectionField, Reference
from lazr.restful.interface import copy_field
from lazr.restful.interfaces import ITopLevelEntryLink
from lazr.restful.declarations import (
    export_as_webservice_entry, export_read_operation, exported,
    operation_parameters, operation_returns_collection_of, webservice_error)


def validate_new_submission_key(submission_key):
    """Check, if submission_key already exists in HWDBSubmission."""
    if not valid_name(submission_key):
        raise LaunchpadValidationError(
            'Submission key can contain only lowercase alphanumerics.')
    submission_set = getUtility(IHWSubmissionSet)
    if submission_set.submissionIdExists(submission_key):
        raise LaunchpadValidationError(
            'Submission key already exists.')
    return True

def validate_email_address(emailaddress):
    """Validate an email address.

    Returns True for valid addresses, else raises LaunchpadValidationError.
    The latter allows convenient error handling by LaunchpadFormView.
    """
    if not valid_email(emailaddress):
        raise LaunchpadValidationError(
            'Invalid email address')
    return True

class HWSubmissionKeyNotUnique(Exception):
    """Prevent two or more submission with identical submission_key."""


class HWSubmissionProcessingStatus(DBEnumeratedType):
    """The status of a submission to the hardware database."""

    INVALID = DBItem(0, """
        Invalid submission

        The submitted data could not be parsed.
        """)

    SUBMITTED = DBItem(1, """
        Submitted

        The submitted data has not yet been processed.
        """)

    PROCESSED = DBItem(2, """
        Processed

        The submitted data has been processed.
        """)

class HWSubmissionFormat(DBEnumeratedType):
    """The format version of the submitted data."""

    VERSION_1 = DBItem(1, "Version 1")


class IHWSubmission(Interface):
    """Raw submission data for the hardware database.

    See doc/hwdb.txt for details about the attributes.
    """
    export_as_webservice_entry()

    date_created = exported(
        Datetime(
            title=_(u'Date Created'), required=True, readonly=True))
    date_submitted = exported(
        Datetime(
            title=_(u'Date Submitted'), required=True, readonly=True))
    format = exported(
        Choice(
            title=_(u'Format Version'), required=True,
            vocabulary=HWSubmissionFormat, readonly=True))
    status = exported(
        Choice(
            title=_(u'Submission Status'), required=True,
            vocabulary=HWSubmissionProcessingStatus, readonly=True))
    private = exported(
        Bool(
            title=_(u'Private Submission'), required=True))
    contactable = exported(
        Bool(
            title=_(u'Contactable'), required=True, readonly=True))
    submission_key = exported(
        TextLine(
            title=_(u'Unique Submission ID'), required=True, readonly=True))
    owner = exported(
        Reference(
            IPerson, title=_(u"The owner of this submission"), readonly=True))
    distroarchseries = Attribute(
        _(u'The DistroArchSeries'))
    raw_submission = exported(
        Bytes(title=_(u'The raw submission data'), required=True,
              readonly=True))
    system_fingerprint = Attribute(
        _(u'The system this submmission was made on'))
    raw_emailaddress = TextLine(
        title=_('Email address'), required=True)

    devices = exported(
        CollectionField(
            title=_(u"The HWSubmissionDevice records for this submission."),
            value_type=Reference(schema=Interface)))


class IHWSubmissionForm(Interface):
    """The schema used to build the HW submission form."""

    date_created = Datetime(
        title=_(u'Date Created'), required=True)
    format = Choice(
        title=_(u'Format Version'), required=True,
        vocabulary=HWSubmissionFormat)
    private = Bool(
        title=_(u'Private Submission'), required=True)
    contactable = Bool(
        title=_(u'Contactable'), required=True)
    submission_key = ASCIILine(
        title=_(u'Unique Submission Key'), required=True,
        constraint=validate_new_submission_key)
    emailaddress = TextLine(
            title=_(u'Email address'), required=True,
            constraint=validate_email_address)
    distribution = TextLine(
        title=_(u'Distribution'), required=True)
    distroseries = TextLine(
        title=_(u'Distribution Release'), required=True)
    architecture = TextLine(
        title=_(u'Processor Architecture'), required=True)
    system = TextLine(
        title=_(u'System name'), required=True)
    submission_data = Bytes(
        title=_(u'Submission data'), required=True)


class IHWSubmissionSet(Interface):
    """The set of HWDBSubmissions."""

    def createSubmission(date_created, format, private, contactable,
                         submission_key, emailaddress, distroarchseries,
                         raw_submission, filename, filesize, system):
        """Store submitted raw hardware information in a Librarian file.

        If a submission with an identical submission_key already exists,
        an HWSubmissionKeyNotUnique exception is raised."""

    def getBySubmissionKey(submission_key, user=None):
        """Return the submission with the given submission key, or None.

        If a submission is marked as private, it is only returned if
        user == HWSubmission.owner, of if user is an admin.
        """

    def getByFingerprintName(name, user=None):
        """Return the submissions for the given system fingerprint string.

        If a submission is marked as private, it is only returned if
        user == HWSubmission.owner, or if user is an admin.
        """

    def getByOwner(owner, user=None):
        """Return the submissions for the given person.

        If a submission is marked as private, it is only returned if
        user == HWSubmission.owner, or if user is an admin.
        """

    def submissionIdExists(submission_key):
        """Return True, if a record with ths ID exists, else return False."""

    def setOwnership(email):
        """Set the owner of a submission.

        If the email address given as the "ownership label" of a submission
        is not known in Launchpad at submission time, the field
        HWSubmission.owner is None. This method sets HWSubmission.owner
        to a Person record, when the given email address is verified.
        """

    def getByStatus(status, user=None):
        """Return the submissions with the given status.

        :param status: A status as enumerated in
            `HWSubmissionProcessingStatus`.
        :param user: The `IPerson` running the query.
        :return: The submissions having the given status.

        If no user is specified, only public submissions are returned.
        If a regular user is specified, public submissions and private
        submissions owned by the user are returned.
        For admins and for the janitor, all submissions with the given
        status are returned.
        """

    def search(user=None, device=None, driver=None, distribution=None,
               distroseries=None, architecture=None, owner=None):
        """Return the submissions matiching the given parmeters.

        :param user: The `IPerson` running the query. Private submissions
            are returned only if the person running the query is the
            owner or an admin.
        :param device: Limit results to submissions containing this
            `IHWDevice`.
        :param driver: Limit results to submissions containing devices
            that use this `IHWDriver`.
        :param distribution: Limit results to submissions made for
            this `IDistribution`.
        :param distroseries: Limit results to submissions made for
            this `IDistroSeries`.
        :param architecture: Limit results to submissions made for
            a specific architecture.
        :param owner: Limit results to submissions from this person.

        Only one of :distribution: or :distroseries: may be supplied.
        """


class IHWSystemFingerprint(Interface):
    """Identifiers of a computer system."""

    fingerprint = Attribute(u'A unique identifier of a system')


class IHWSystemFingerprintSet(Interface):
    """The set of HWSystemFingerprints."""

    def getByName(fingerprint):
        """Lookup an IHWSystemFingerprint by its value.

        Return None, if a fingerprint `fingerprint` does not exist."""

    def createFingerprint(fingerprint):
        """Create an entry in the fingerprint list.

        Return the new entry."""

class IHWDriver(Interface):
    """Information about a device driver."""
    export_as_webservice_entry()

    id = exported(
        Int(title=u'Driver ID', required=True, readonly=True))

    package_name = exported(
        TextLine(
            title=u'Package Name', required=False,
            description=_("The name of the package written without spaces in "
                          "lowercase letters and numbers."),
            default=u''))

    name = exported(
        TextLine(
            title=u'Driver Name', required=True,
            description=_("The name of the driver written without spaces in "
                          "lowercase letters and numbers.")))

    license = exported(
        Choice(
            title=u'License of the Driver', required=False,
            vocabulary=License))
    @operation_parameters(
        distribution=Reference(
            IDistribution,
            title=u'A Distribution',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given distribution.',
            required=False),
        distroseries=Reference(
            IDistroSeries,
            title=u'A Distribution Series',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given distribution series.',
            required=False),
        architecture = TextLine(
            title=u'A processor architecture',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given architecture.',
            required=False),
        owner = copy_field(IHWSubmission['owner']))
    @operation_returns_collection_of(IHWSubmission)
    @export_read_operation()
    def getSubmissions(distribution=None, distroseries=None,
                       architecture=None, owner=None):
        """List all submissions which mention this driver.

        :param distribution: Limit results to submissions for this
            `IDistribution`.
        :param distroseries: Limit results to submissions for this
            `IDistroSeries`.
        :param architecture: Limit results to submissions for this
            architecture.
        :param owner: Limit results to submissions from this person.

        Only submissions matching all given criteria are returned.
        Only one of :distribution: or :distroseries: may be supplied.
        """


class IHWDriverSet(Interface):
    """The set of device drivers."""

    def create(package_name, name, license):
        """Create a new IHWDriver instance.

        :param package_name: The name of the packages containing the driver.
        :param name: The name of the driver.
        :param license: The license of the driver.
        :return: The new IHWDriver instance.
        """

    def getByPackageAndName(package_name, name):
        """Return an IHWDriver instance for the given parameters.

        :param package_name: The name of the packages containing the driver.
        :param name: The name of the driver.
        :return: An IHWDriver instance or None, if no record exists for
            the given parameters.
        """

    def getOrCreate(package_name, name, license=None):
        """Return an IHWDriver instance or create one.

        :param package_name: The name of the packages containing the driver.
        :param name: The name of the driver.
        :param license: The license of the driver.
        :return: An IHWDriver instance or None, if no record exists for
            the given parameters.
        """

    def search(package_name=None, name=None):
        """Return the drivers matching the given parameters.

        :param package_name: The name of the packages containing the driver.
            If package_name is not given or None, the result set is
            not limited to a specific package name.
            If package_name == '', those records are returned where
            record.package_name == '' or record.package_name is None.
            Otherwise only records matching the given name are returned.
        :param name: The name of the driver.
            If name is not given or None, the result set is not limited to
            a specific driver name.
            Otherwise only records matching the given name are returned.
        :return: A sequence of IHWDriver instances.
        """

    def getByID(id):
        """Return an IHWDriver record with the given database ID.

        :param id: The database ID.
        :return: An IHWDriver instance.
        """

    package_names = List(
        title=u'Package Names',
        description=
            u'All known distinct package names appearing in HWDriver.',
        value_type=TextLine(),
        readonly=True)


# Identification of a hardware device.
#
# In theory, a tuple (bus, vendor ID, product ID) should identify
# a device unambiguously. In practice, there are several cases where
# this tuple can identify more than one device:
#
# - A USB chip or chipset may be used in different devices.
#   A real world example:
#     - Plustek sold different scanner models with the USB ID
#       0x7b3/0x0017. Some of these scanners have for example a
#       different maximum scan size.
#
# Hence we identify a device by tuple (bus, vendor ID, product ID,
# variant). In the example above, we might use (HWBus.USB, '0x7b3',
# '0x0017', 'OpticPro UT12') and (HWBus.USB, '0x7b3', '0x0017',
# 'OpticPro UT16')

class HWBus(DBEnumeratedType):
    """The bus that connects a device to a computer."""

    SYSTEM = DBItem(0, 'System')

    PCI = DBItem(1, 'PCI')

    USB = DBItem(2, 'USB')

    IEEE1394 = DBItem(3, 'IEEE1394')

    SCSI = DBItem(4, 'SCSI')

    PARALLEL = DBItem(5, 'Parallel Port')

    SERIAL = DBItem(6, 'Serial port')

    IDE = DBItem(7, 'IDE')

    ATA = DBItem(8, 'ATA')

    FLOPPY = DBItem(9, 'Floppy')

    IPI = DBItem(10, 'IPI')

    SATA = DBItem(11, 'SATA')

    SAS = DBItem(12, 'SAS')

    PCCARD = DBItem(13, 'PC Card (32 bit)')

    PCMCIA = DBItem(14, 'PCMCIA (16 bit)')


class HWMainClass(HWBus):
    """The device classes.

    This enumeration describes the capabilities of a device.
    """

    NETWORK = DBItem(10000, 'Network')

    STORAGE = DBItem(11000, 'Storage')

    DISPLAY = DBItem(12000, 'Display')

    VIDEO = DBItem(13000, 'Video')

    AUDIO = DBItem(14000, 'Audio')

    MODEM = DBItem(15000, 'Modem')

    INPUT = DBItem(16000, 'Input') # keyboard, mouse tetc.

    PRINTER = DBItem(17000, 'Printer')

    SCANNER = DBItem(18000, 'Scanner')


class HWSubClass(DBEnumeratedType):
    """The device subclasses.

    This enumeration gives more details for the "coarse" device class
    specified by HWDeviceClass.
    """
    NETWORK_ETHERNET = DBItem(10001, 'Ethernet')

    STORAGE_HARDDISK = DBItem(11001, 'Hard Disk')

    STORAGE_FLASH = DBItem(11002, 'Flash Memory')

    STORAGE_FLOPPY = DBItem(11003, 'Floppy')

    STORAGE_CDROM = DBItem(11004, 'CDROM Drive')

    STORAGE_CDWRITER = DBItem(11005, 'CD Writer')

    STORAGE_DVD = DBItem(11006, 'DVD Drive')

    STORAGE_DVDWRITER = DBItem(11007, 'DVD Writer')

    PRINTER_INKJET = DBItem(17001, 'Inkjet Printer')

    PRINTER_LASER = DBItem(17002, 'Laser Printer')

    PRINTER_MATRIX = DBItem(17003, 'Matrix Printer')

    SCANNER_FLATBED = DBItem(18001, 'Flatbed Scanner')

    SCANNER_ADF = DBItem(18002, 'Scanner with Automatic Document Feeder')

    SCANNER_TRANSPARENCY = DBItem(18003, 'Scanner for Transparent Documents')


class IHWVendorName(Interface):
    """A list of vendor names."""
    name = TextLine(title=u'Vendor Name', required=True)


class IHWVendorNameSet(Interface):
    """The set of vendor names."""
    def create(name):
        """Create and return a new vendor name.

        :return: A new IHWVendorName instance.

        An IntegrityError is raised, if the name already exists.
        """

    def getByName(name):
        """Return the IHWVendorName record for the given name.

        :param name: The vendor name.
        :return: An IHWVendorName instance where IHWVendorName.name==name
            or None, if no such instance exists.
        """


class IHWVendorID(Interface):
    """A list of vendor IDs for different busses associated with vendor names.
    """
    export_as_webservice_entry()
    id = exported(
        Int(title=u'The Database ID', required=True, readonly=True))

    bus = exported(
        Choice(
            title=u'The bus that connects a device to a computer',
            required=True, vocabulary=HWBus))

    vendor_id_for_bus = exported(
        TextLine(title=u'Vendor ID', required=True),
        exported_as='vendor_id')

    vendor_name = Attribute('Vendor Name')


class IHWVendorIDSet(Interface):
    """The set of vendor IDs."""
    def create(bus, vendor_id, name):
        """Create a vendor ID.

        :param bus: the HWBus instance for this bus.
        :param vendor_id: a string containing the bus ID. Numeric IDs
            are represented as a hexadecimal string, prepended by '0x'.
        :param name: The IHWVendorName instance with the vendor name.
        :return: A new IHWVendorID instance.
        """

    def getByBusAndVendorID(bus, vendor_id):
        """Return an IHWVendorID instance for the given bus and vendor_id.

        :param bus: An HWBus instance.
        :param vendor_id: A string containing the vendor ID. Numeric IDs
            must be represented as a hexadecimal string, prepended by '0x'.
        :return: The found IHWVendorID instance or None, if no instance
            for the given bus and vendor ID exists.
        """

    def get(id):
        """Return an IHWVendorID record with the given database ID.

        :param id: The database ID.
        :return: An IHWVendorID instance.
        """

    def idsForBus(bus):
        """Return all known IHWVendorID records with the given bus.

        :param bus: A HWBus instance.
        :return: A sequence of IHWVendorID instances.
        """


VENDOR_ID_DESCRIPTION = u"""Allowed values of the vendor ID depend on the
bus of the device.

Vendor IDs of PCI, PCCard and USB devices are hexadecimal string
representations of 16 bit integers in the format '0x01ab': The prefix
'0x', followed by exactly 4 digits; where a digit is one of the
characters 0..9, a..f. The characters A..F are not allowed.

SCSI vendor IDs are strings with exactly 8 characters. Shorter names are
right-padded with space (0x20) characters.

IDs for other buses may be arbitrary strings.
"""

PRODUCT_ID_DESCRIPTION = u"""Allowed values of the product ID depend on the
bus of the device.

Product IDs of PCI, PCCard and USB devices are hexadecimal string
representations of 16 bit integers in the format '0x01ab': The prefix
'0x', followed by exactly 4 digits; where a digit is one of the
characters 0..9, a..f. The characters A..F are not allowed.

SCSI product IDs are strings with exactly 16 characters. Shorter names are
right-padded with space (0x20) characters.

IDs for other buses may be arbitrary strings.
"""


class IHWDevice(Interface):
    """Core information to identify a device."""
    export_as_webservice_entry()

    id = exported(
        Int(title=u'Device ID', required=True, readonly=True))

    bus_vendor = Attribute(u'Ths bus and vendor of the device')

    bus_product_id = exported(
        TextLine(title=u'The product identifier of the device',
                 required=True, description=PRODUCT_ID_DESCRIPTION))

    variant = exported(
        TextLine(title=u'A string that distiguishes different '
                        'devices with identical vendor/product IDs',
                 required=True))

    name = exported(
        TextLine(title=u'The human readable name of the device.',
                 required=True))

    submissions = Int(title=u'The number of submissions with the device',
                      required=True)

    bus = exported(
        Choice(title=u'The bus of the device.', vocabulary=HWBus,
               readonly=True))

    vendor_id = exported(
        TextLine(title=u'The vendor iD.', readonly=True,
                 description=VENDOR_ID_DESCRIPTION))

    vendor_name = exported(
        TextLine(title=u'The vendor name.', readonly=True))

    @operation_parameters(
        driver=Reference(
            IHWDriver,
            title=u'A driver used for this device in a submission',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given distribution, distroseries or '
                'distroarchseries.',
            required=False),
        distribution=Reference(
            IDistribution,
            title=u'A Distribution',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given distribution.',
            required=False),
        distroseries=Reference(
            IDistroSeries,
            title=u'A Distribution Series',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given distribution series.',
            required=False),
        architecture = TextLine(
            title=u'A processor architecture',
            description=
                u'If specified, the result set is limited to sumbissions '
                'made for the given architecture.',
            required=False),
        owner = copy_field(IHWSubmission['owner']))
    @operation_returns_collection_of(IHWSubmission)
    @export_read_operation()
    def getSubmissions(driver=None, distribution=None,
                       distroseries=None, architecture=None, owner=None):
        """List all submissions which mention this device.

        :param driver: Limit results to devices that use the given
            `IHWDriver`.
        :param distribution: Limit results to submissions for this
            `IDistribution`.
        :param distroseries: Limit results to submissions for this
            `IDistroSeries`.
        :param architecture: Limit results to submissions for this
            architecture.
        :param owner: Limit results to submissions from this person.

        Only submissions matching all given criteria are returned.
        Only one of :distribution: or :distroseries: may be supplied.
        """

    drivers = exported(
        CollectionField(
            title=_(u"The IHWDriver records related to this device."),
            value_type=Reference(schema=IHWDriver)))


class IHWDeviceSet(Interface):
    """The set of devices."""

    def create(bus, vendor_id, product_id, product_name, variant=None):
        """Create a new device entry.

        :param bus: A bus name as enumerated in HWBus.
        :param vendor_id: The vendor ID for the bus.
        :param product_id: The product ID.
        :param product_name: The human readable product name.
        :param variant: A string that allows to distinguish different devices
                        with identical product/vendor IDs.
        :return: A new IHWDevice instance.
        """

    def getByDeviceID(bus, vendor_id, product_id, variant=None):
        """Return an IHWDevice record.

        :param bus: The bus name of the device as enumerated in HWBus.
        :param vendor_id: The vendor ID of the device.
        :param product_id: The product ID of the device.
        :param variant: A string that allows to distinguish different devices
                        with identical product/vendor IDs.
        :return: An IHWDevice instance.
        """

    def getOrCreate(bus, vendor_id, product_id, product_name, variant=None):
        """Return an IHWDevice record or create one.

        :param bus: The bus name of the device as enumerated in HWBus.
        :param vendor_id: The vendor ID of the device.
        :param product_id: The product ID of the device.
        :param product_name: The human readable product name.
        :param variant: A string that allows to distinguish different devices
                        with identical product/vendor IDs.
        :return: An IHWDevice instance.

        Return an existing IHWDevice record matching the given
        parameters or create a new one, if no existing record
        matches.
        """

    def getByID(self, id):
        """Return an IHWDevice record with the given database ID.

        :param id: The database ID.
        :return: An IHWDevice instance.
        """

    def search(bus, vendor_id, product_id=None):
        """Return HWDevice records matching the given parameters.

        :param vendor_id: The vendor ID of the device.
        :param product_id: The product ID of the device.
        :return: A sequence of IHWDevice instances.
        """


class IHWDeviceClass(Interface):
    """The capabilities of a device."""
    device = Attribute(u'The Device')
    main_class = Choice(
        title=u'The main class of this device', required=True,
        readonly=True, vocabulary=HWMainClass)
    sub_class = Choice(
        title=u'The sub class of this device', required=False,
        readonly=True, vocabulary=HWSubClass)


class IHWDeviceClassSet(Interface):
    """The set of device capabilities."""

    def create(device, main_class, sub_class=None):
        """Create a new IHWDevice record.

        :param device: The device described by the new record.
        :param main_class: A HWMainClass instance.
        :param sub_class: A HWSubClass instance.
        :return: An IHWDeviceClass instance.
        """

class IHWDeviceNameVariant(Interface):
    """Variants of a device name.

    We identify devices by (bus, vendor_id, product_id[, variant]),
    but many OEM products are sold by different vendors under different
    names. Users might want to look up device data by giving the
    vendor and product name as seen in a store; this table provides
    the "alias names" required for such a lookup.
    """
    vendor_name = Attribute(u'Vendor Name')

    product_name = TextLine(title=u'Product Name', required=True)

    device = Attribute(u'The device which has this name')

    submissions = Int(
        title=u'The number of submissions with this name variant',
        required=True)


class IHWDeviceNameVariantSet(Interface):
    """The set of device name variants."""

    def create(device, vendor_name, product_name):
        """Create a new IHWDeviceNameVariant instance.

        :param device: An IHWDevice instance.
        :param vendor_name: The alternative vendor name for the device.
        :param product_name: The alternative product name for the device.
        :return: The new IHWDeviceNameVariant.
        """


class IHWDeviceDriverLink(Interface):
    """Link a device with a driver."""

    device = Attribute(u'The Device.')

    driver = Attribute(u'The Driver.')


class IHWDeviceDriverLinkSet(Interface):
    """The set of device driver links."""

    def create(device, driver):
        """Create a new IHWDeviceDriver instance.

        :param device: The IHWDevice instance to be linked.
        :param driver: The IHWDriver instance to be linked.
        :return: The new IHWDeviceDriver instance.
        """

    def getByDeviceAndDriver(device, driver):
        """Return an IHWDeviceDriver instance.

        :param device: An IHWDevice instance.
        :param driver: An IHWDriver instance.
        :return: The IHWDeviceDriver instance matching the given
            parameters or None, if no existing instance matches.
        """
    def getOrCreate(device, driver):
        """Return an IHWDeviceDriverLink record or create one.

        :param device: The IHWDevice instance to be linked.
        :param driver: The IHWDriver instance to be linked.
        :return: An IHWDeviceDriverLink instance.

        Return an existing IHWDeviceDriverLink record matching te given
        parameters or create a new one, if no exitsing record
        matches.
        """


class IHWSubmissionDevice(Interface):
    """Link a submission to a IHWDeviceDriver row."""
    export_as_webservice_entry()

    id = exported(
        Int(title=u'HWSubmissionDevice ID', required=True, readonly=True))

    device_driver_link = Attribute(u'A device and driver appearing in a '
                                    'submission.')

    submission = Attribute(u'The submission the device and driver are '
                            'mentioned in.')

    parent = exported(
        # This is a reference to IHWSubmissionDevice itself, but we can
        # access the class only when the class has been defined.
        Reference(Interface, required=True))

    hal_device_id = exported(
        Int(
            title=u'The ID of the HAL node of this device in the submitted '
                'data',
            required=True))

    device = exported(
        Reference(
            IHWDevice,
            title=u'The device'))

    driver = exported(
        Reference(
            IHWDriver,
            title=u'The driver used for this device in this submission'))


# Fix cyclic references.
IHWSubmissionDevice['parent'].schema = IHWSubmissionDevice
IHWSubmission['devices'].value_type.schema = IHWSubmissionDevice


class IHWSubmissionDeviceSet(Interface):
    """The set of IHWSubmissionDevices."""

    def create(device_driver_link, submission, parent):
        """Create a new IHWSubmissionDevice instance.

        :param device_driver_link: An IHWDeviceDriverLink instance.
        :param submission: The submission the device/driver combination
            is mentioned in.
        :param parent: The parent of this device in the device tree in
            the submission.
        :return: The new IHWSubmissionDevice instance.
        """

    def getDevices(submission):
        """Return the IHWSubmissionDevice records of a submission

        :return: A sequence of IHWSubmissionDevice records.
        :param submission: An IHWSubmission instance.
        """

    def get(id):
        """Return an IHWSubmissionDevice record with the given database ID.

        :param id: The database ID.
        :return: An IHWSubmissionDevice instance.
        """


class IHWSubmissionBug(Interface):
    """Link a HWDB submission to a bug."""

    submission = Attribute(u'The HWDB submission referenced in a bug '
                              'report.')

    bug = Attribute(u'The bug the HWDB submission is referenced in.')


class IHWSubmissionBugSet(Interface):
    """The set of IHWSubmissionBugs."""

    def create(hwsubmission, bug):
        """Create a new IHWSubmissionBug instance.

        :return: The new IHWSubmissionBug instance.
        :param hwsubmission: An IHWSubmission instance.
        :param bug: An IBug instance.
        """

class IHWDBApplication(ILaunchpadApplication, ITopLevelEntryLink):
    """Hardware database application application root."""

    export_as_webservice_entry('hwdb')

    @operation_parameters(
        bus=Choice(
            title=u'The device bus', vocabulary=HWBus, required=True),
        vendor_id=TextLine(
            title=u'The vendor ID', required=True,
            description=VENDOR_ID_DESCRIPTION),
        product_id=TextLine(
            title=u'The product ID', required=False,
            description=PRODUCT_ID_DESCRIPTION))
    @operation_returns_collection_of(IHWDevice)
    @export_read_operation()
    def devices(bus, vendor_id, product_id=None):
        """Return the set of devices."""

    @operation_parameters(
        package_name=TextLine(
            title=u'The name of the package containing the driver.',
            required=False,
            description=
                u'If package_name is omitted, all driver records '
                'returned, optionally limited to those matching the '
                'parameter name. If package_name is '' (empty string), '
                'those records are returned where package_name is '' or '
                'None.'),
        name=TextLine(
            title=u'The name of the driver.', required=False,
            description=
                u'If name is omitted, all driver records are '
                'returned, optionally limited to those matching the '
                'parameter package_name.'))
    @operation_returns_collection_of(IHWDriver)
    @export_read_operation()
    def drivers(package_name=None, name=None):
        """Return the set of drivers."""

    @operation_parameters(
        bus=Choice(
            title=u'A Device Bus.', vocabulary=HWBus, required=True))
    @operation_returns_collection_of(IHWVendorID)
    @export_read_operation()
    def vendorIDs(bus):
        """Return the known vendor IDs for the given bus.

        :param bus: A `HWBus` value.
        :return: A list of strings with vendor IDs fr this bus,
        """

    package_names = exported(
        List(title=u'Package Names',
             description=
                 u'All known distinct package names appearing in HWDriver.',
             value_type=TextLine(),
             readonly=True))


class IllegalQuery(Exception):
    """Exception raised when trying to run an illegal submissions query."""
    webservice_error(400) #Bad request.

class ParameterError(Exception):
    """Exception raised when a method parameter does not match a constrint."""
    webservice_error(400) #Bad request.
