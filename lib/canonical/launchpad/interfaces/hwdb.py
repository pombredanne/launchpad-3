# Copyright 2007, 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to the hardware database."""

__metaclass__ = type

__all__ = [
    'HWBus',
    'HWSubmissionFormat',
    'HWSubmissionKeyNotUnique',
    'HWSubmissionProcessingStatus',
    'IHWDevice',
    'IHWDeviceDriverLink',
    'IHWDeviceDriverLinkSet',
    'IHWDeviceNameVariant',
    'IHWDeviceNameVariantSet',
    'IHWDeviceSet',
    'IHWDriver',
    'IHWDriverSet',
    'IHWSubmission',
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
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    ASCIILine, Bool, Bytes, Choice, Datetime, Int, Object, TextLine)

from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.product import License
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.validators.email import valid_email


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

    date_created = Datetime(
        title=_(u'Date Created'), required=True)
    date_submitted = Datetime(
        title=_(u'Date Submitted'), required=True)
    format = Choice(
        title=_(u'Format Version'), required=True,
        vocabulary=HWSubmissionFormat)
    status = Choice(
        title=_(u'Submission Status'), required=True,
        vocabulary=HWSubmissionProcessingStatus)
    private = Bool(
        title=_(u'Private Submission'), required=True)
    contactable = Bool(
        title=_(u'Contactable'), required=True)
    submission_key = ASCIILine(
        title=_(u'Unique Submission ID'), required=True)
    owner = Attribute(
        _(u"The owner's IPerson"))
    distroarchseries = Attribute(
        _(u'The DistroArchSeries'))
    raw_submission = Object(
        schema=ILibraryFileAlias,
        title=_(u'The raw submission data'),
        required=True)
    system_fingerprint = Attribute(
        _(u'The system this submmission was made on'))
    raw_emailaddress = TextLine(
        title=_('Email address'), required=True)



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

    PCCARD = DBItem(13, 'PC Card')

    PCMCIA = DBItem(14, 'PCMCIA')


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


class IHWVendorID(Interface):
    """A list of vendor IDs for different busses associated with vendor names.
    """
    bus = Choice(
        title=u'The bus that connects a device to a computer',
        required=True, vocabulary=HWBus)

    vendor_id_for_bus = TextLine(title=u'Vendor ID', required=True)

    vendor_name = Attribute('Vendor Name')


class IHWVendorIDSet(Interface):
    """The set of vendor IDs."""
    def create(bus, vendor_id, name):
        """Create a vendor ID.

        :return: A new IHWVendorID instance.
        :param bus: the HWBus instance for this bus.
        :param vendor_id: a string containing the bus ID. Numeric IDs
            are represented as a hexadecimal string, prepended by '0x'.
        :param name: The IHWVendorName instance with the vendor name.
        """


class IHWDevice(Interface):
    """Core information to identify a device."""
    bus_vendor = Attribute(u'Ths bus and vendor of the device')

    bus_product_id = TextLine(title=u'The product identifier of the device',
                              required=True)

    variant = TextLine(title=u'A string that distiguishes different '
                              'devices with identical vendor/product IDs',
                       required=True)

    name = TextLine(title=u'The human readable name of the device.',
                    required=True)

    submissions = Int(title=u'The number of submissions with the device',
                      required=True)


class IHWDeviceSet(Interface):
    """The set of devices."""

    def create(bus, vendor_id, product_id, product_name, variant=None):
        """Create a new device entry.

        :return: A new IHWDevice instance.
        :param bus: A bus name as enumerated in HWBus.
        :param vendor_id: The vendor ID for the bus.
        :param product_id: The product ID.
        :param name: The human readable product name.
        :param variant: A string that allows to distinguish different devices
                        with identical product/vendor IDs.
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

        :return: The new IHWDeviceNameVariant.
        :param device: An IHWDevice instance.
        :param vendor_name: The alternative vendor name for the device.
        :param product_name: The alternative product name for the device.
        """


class IHWDriver(Interface):
    """Information about a device driver."""

    package_name = TextLine(title=u'Package Name', required=False,
        description=_("The name of the package written without spaces in "
                      "lowercase letters and numbers."))

    name = TextLine(title=u'Driver Name', required=True,
        description=_("The name of the driver written without spaces in "
                      "lowercase letters and numbers."))

    license = Choice(title=u'License of the Driver',
                     required=False, vocabulary=License)


class IHWDriverSet(Interface):
    """The set of device drivers."""

    def create(package_name, name, license):
        """Create a new IHWDriver instance.

        :return: The new IHWDriver instance.
        :param package_name: The name of the packages containing the driver.
        :param name: The name of the driver.
        :param license: The license of the driver.
        """


class IHWDeviceDriverLink(Interface):
    """Link a device with a driver."""

    device = Attribute(u'The Device.')

    driver = Attribute(u'The Driver.')


class IHWDeviceDriverLinkSet(Interface):
    """The set of device driver links."""

    def create(device, driver):
        """Create a new IHWDeviceDriver instance.

        :return: The new IHWDeviceDriver instance.
        :param device: The IHWDevice instance to be linked.
        :param driver: The IHWDriver instance to be linked.
        """

class IHWSubmissionDevice(Interface):
    """Link a submission to a IHWDeviceDriver row."""

    device_driver_link = Attribute(u'A device and driver appearing in a '
                                    'submission.')

    submission = Attribute(u'The submission the device and driver are '
                            'mentioned in.')

    parent = Attribute(u'The parent IHWSubmissionDevice entry of this '
                        ' device.')

class IHWSubmissionDeviceSet(Interface):
    """The set of IHWSubmissionDevices."""

    def create(device_driver_link, submission, parent):
        """Create a new IHWSubmissionDevice instance.

        :return: The new IHWSubmissionDevice instance.
        :param device_driver_link: An IHWDeviceDriverLink instance.
        :param submission: The submission the device/driver combination
            is mentioned in.
        :param parent: The parent of this device in the device tree in
            the submission.
        """
