# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Hardware database related table classes."""

__all__ = [
    'HWDevice',
    'HWDeviceClass',
    'HWDeviceClassSet',
    'HWDeviceSet',
    'HWDeviceDriverLink',
    'HWDeviceDriverLinkSet',
    'HWDeviceNameVariant',
    'HWDeviceNameVariantSet',
    'HWDriver',
    'HWDriverSet',
    'HWSubmission',
    'HWSubmissionBug',
    'HWSubmissionBugSet',
    'HWSubmissionSet',
    'HWSubmissionDevice',
    'HWSubmissionDeviceSet',
    'HWSystemFingerprint',
    'HWSystemFingerprintSet',
    'HWVendorID',
    'HWVendorIDSet',
    'HWVendorName',
    'HWVendorNameSet',
    ]

import re

from zope.component import getUtility
from zope.interface import implements

from sqlobject import BoolCol, ForeignKey, IntCol, StringCol
from storm.expr import And, Not, Or, Select

from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.distroarchseries import DistroArchSeries
from canonical.launchpad.database.distroseries import DistroSeries
from canonical.launchpad.database.teammembership import TeamParticipation
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.hwdb import (
    HWBus, HWMainClass, HWSubClass, HWSubmissionFormat,
    HWSubmissionKeyNotUnique, HWSubmissionProcessingStatus, IHWDevice,
    IHWDeviceClass, IHWDeviceClassSet, IHWDeviceDriverLink,
    IHWDeviceDriverLinkSet, IHWDeviceNameVariant, IHWDeviceNameVariantSet,
    IHWDeviceSet, IHWDriver, IHWDriverSet, IHWSubmission, IHWSubmissionBug,
    IHWSubmissionBugSet, IHWSubmissionDevice, IHWSubmissionDeviceSet,
    IHWSubmissionSet, IHWSystemFingerprint, IHWSystemFingerprintSet,
    IHWVendorID, IHWVendorIDSet, IHWVendorName, IHWVendorNameSet,
    IllegalQuery, ParameterError)
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.product import License
from canonical.launchpad.validators.person import validate_public_person
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)

# The vendor name assigned to new, unknown vendor IDs. See
# HWDeviceSet.create().
UNKNOWN = 'Unknown'


class HWSubmission(SQLBase):
    """See `IHWSubmission`."""

    implements(IHWSubmission)

    _table = 'HWSubmission'

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_submitted = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    format = EnumCol(enum=HWSubmissionFormat, notNull=True)
    status = EnumCol(enum=HWSubmissionProcessingStatus, notNull=True)
    private = BoolCol(notNull=True)
    contactable = BoolCol(notNull=True)
    submission_key = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person',
                       storm_validator=validate_public_person)
    distroarchseries = ForeignKey(dbName='distroarchseries',
                                  foreignKey='DistroArchSeries')
    raw_submission = ForeignKey(dbName='raw_submission',
                                foreignKey='LibraryFileAlias',
                                notNull=False, default=DEFAULT)
    system_fingerprint = ForeignKey(dbName='system_fingerprint',
                                    foreignKey='HWSystemFingerprint',
                                    notNull=True)
    raw_emailaddress = StringCol()

    @property
    def devices(self):
        return HWSubmissionDeviceSet().getDevices(submission=self)


class HWSubmissionSet:
    """See `IHWSubmissionSet`."""

    implements(IHWSubmissionSet)

    def createSubmission(self, date_created, format, private, contactable,
                         submission_key, emailaddress, distroarchseries,
                         raw_submission, filename, filesize,
                         system_fingerprint):
        """See `IHWSubmissionSet`."""
        assert valid_name(submission_key), "Invalid key %s" % submission_key

        submission_exists = HWSubmission.selectOneBy(
            submission_key=submission_key)
        if submission_exists is not None:
            raise HWSubmissionKeyNotUnique(
                'A submission with this ID already exists')

        personset = getUtility(IPersonSet)
        if emailaddress is not None:
            owner = personset.getByEmail(emailaddress)
        else:
            owner = None

        fingerprint = HWSystemFingerprint.selectOneBy(
            fingerprint=system_fingerprint)
        if fingerprint is None:
            fingerprint = HWSystemFingerprint(fingerprint=system_fingerprint)

        libraryfileset = getUtility(ILibraryFileAliasSet)
        libraryfile = libraryfileset.create(
            name=filename,
            size=filesize,
            file=raw_submission,
            # XXX: kiko 2007-09-20: The hwdb client sends us bzipped XML, but
            # arguably other clients could send us other formats. The right
            # way to do this is either to enforce the format in the browser
            # code, allow the client to specify the format, or use a
            # magic module to sniff what it is we got.
            contentType='application/x-bzip2',
            expires=None)

        return HWSubmission(
            date_created=date_created,
            format=format,
            status=HWSubmissionProcessingStatus.SUBMITTED,
            private=private,
            contactable=contactable,
            submission_key=submission_key,
            owner=owner,
            distroarchseries=distroarchseries,
            raw_submission=libraryfile,
            system_fingerprint=fingerprint,
            raw_emailaddress=emailaddress)

    def _userHasAccessClause(self, user):
        """Limit results of HWSubmission queries to rows the user can access.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        if user is None:
            return " AND NOT HWSubmission.private"
        elif not user.inTeam(admins):
            return """
                AND (NOT HWSubmission.private
                     OR EXISTS
                         (SELECT 1
                             FROM HWSubmission as HWAccess, TeamParticipation
                             WHERE HWAccess.id=HWSubmission.id
                                 AND HWAccess.owner=TeamParticipation.team
                                 AND TeamParticipation.person=%i
                                 ))
                """ % user.id
        else:
            return ""

    def _userHasAccessStormClause(self, user):
        """Limit results of HWSubmission queries to rows the user can access.
        """
        submission_is_public = Not(HWSubmission.private)
        admins = getUtility(ILaunchpadCelebrities).admin
        janitor = getUtility(ILaunchpadCelebrities).janitor
        if user is None:
            return submission_is_public
        elif user.inTeam(admins) or user == janitor:
            return True
        else:
            public = Not(HWSubmission.private)
            subselect = Select(
                TeamParticipation.teamID,
                And(HWSubmission.ownerID == TeamParticipation.teamID,
                    TeamParticipation.personID == user.id))
            has_access = HWSubmission.ownerID.is_in(subselect)
            return Or(public, has_access)

    def getBySubmissionKey(self, submission_key, user=None):
        """See `IHWSubmissionSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            HWSubmission,
            And(HWSubmission.submission_key == submission_key,
                self._userHasAccessStormClause(user))).one()

    def getByFingerprintName(self, name, user=None):
        """See `IHWSubmissionSet`."""
        fp = HWSystemFingerprintSet().getByName(name)
        query = """
            system_fingerprint=%s
            AND HWSystemFingerprint.id = HWSubmission.system_fingerprint
            """ % sqlvalues(fp)
        query = query + self._userHasAccessClause(user)

        return HWSubmission.select(
            query,
            clauseTables=['HWSystemFingerprint'],
            prejoinClauseTables=['HWSystemFingerprint'],
            orderBy=['-date_submitted',
                     'HWSystemFingerprint.fingerprint',
                     'submission_key'])

    def getByOwner(self, owner, user=None):
        """See `IHWSubmissionSet`."""
        query = """
            owner=%i
            AND HWSystemFingerprint.id = HWSubmission.system_fingerprint
            """ % owner.id
        query = query + self._userHasAccessClause(user)

        return HWSubmission.select(
            query,
            clauseTables=['HWSystemFingerprint'],
            prejoinClauseTables=['HWSystemFingerprint'],
            orderBy=['-date_submitted',
                     'HWSystemFingerprint.fingerprint',
                     'submission_key'])

    def submissionIdExists(self, submission_key):
        """See `IHWSubmissionSet`."""
        rows = HWSubmission.selectBy(submission_key=submission_key)
        return rows.count() > 0

    def setOwnership(self, email):
        """See `IHWSubmissionSet`."""
        assert email.status in (EmailAddressStatus.VALIDATED,
                                EmailAddressStatus.PREFERRED), (
            'Invalid email status for setting ownership of an HWDB '
            'submission: %s' % email.status.title)
        submissions =  HWSubmission.selectBy(
            raw_emailaddress=email.email, owner=None)
        for submission in submissions:
            submission.ownerID = email.personID

    def getByStatus(self, status, user=None):
        """See `IHWSubmissionSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(HWSubmission,
                                HWSubmission.status == status,
                                self._userHasAccessStormClause(user))
        # Provide a stable order. Sorting by id, to get the oldest
        # submissions first. When date_submitted has an index, we could
        # sort by that first.
        result_set.order_by(HWSubmission.id)
        return result_set

    def search(self, user=None, device=None, driver=None, distribution=None,
               distroseries=None, architecture=None, owner=None):
        """See `IHWSubmissionSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        args = []
        if device is not None:
            args.append(HWDeviceDriverLink.device == HWDevice.id)
            args.append(HWDevice.id == device.id)
        if driver is not None:
            args.append(HWDeviceDriverLink.driver == HWDriver.id)
            args.append(HWDriver.id == driver.id)
        # HWDevice and HWDriver are linked to submissions via
        # HWDeviceDriverLink and HWSubmissionDevice.
        if args:
            args.append(HWSubmissionDevice.device_driver_link ==
                        HWDeviceDriverLink.id)
            args.append(HWSubmissionDevice.submission == HWSubmission.id)

        if (distribution is not None or distroseries is not None
            or architecture is not None):
            # We need to select a specific distribution, distroseries,
            # and/or processor architecture.
            if distribution and distroseries:
                raise IllegalQuery(
                    'Only one of `distribution` or '
                    '`distroseries` can be present.')
            args.append(HWSubmission.distroarchseries == DistroArchSeries.id)
            if architecture is not None:
                args.append(DistroArchSeries.architecturetag == architecture)
            if distribution is not None:
                args.append(DistroArchSeries.distroseries == DistroSeries.id)
                args.append(DistroSeries.distribution == Distribution.id)
                args.append(Distribution.id == distribution.id)
            if distroseries is not None:
                args.append(DistroArchSeries.distroseries == distroseries.id)
        if owner is not None:
            args.append(HWSubmission.owner == owner.id)

        result_set = store.find(
            HWSubmission,
            self._userHasAccessStormClause(user),
            *args)
        # Many devices are associated with more than one driver, even
        # for one submission, hence we may have more than one
        # HWSubmissionDevice record and more than one HWDeviceDriverLink
        # for one device and one submission matching the WHERE clause
        # defined above. This leads to duplicate results without a
        # DISTINCT clause.
        result_set.config(distinct=True)
        result_set.order_by(HWSubmission.id)
        # The Storm implementation of ResultSet.count() is incorrect if
        # the select query uses the distinct directive (see bug #217644).
        # DecoratedResultSet solves this problem by modifying the query
        # to count only the records appearing in a subquery.
        # We don't actually need to transform the results, which is why
        # the second argument is a no-op.
        return DecoratedResultSet(result_set, lambda result: result)


class HWSystemFingerprint(SQLBase):
    """Identifiers of a computer system."""

    implements(IHWSystemFingerprint)

    _table = 'HWSystemFingerprint'

    fingerprint = StringCol(notNull=True)


class HWSystemFingerprintSet:
    """A set of identifiers of a computer system."""

    implements(IHWSystemFingerprintSet)

    def getByName(self, fingerprint):
        """See `IHWSystemFingerprintSet`."""
        return HWSystemFingerprint.selectOneBy(fingerprint=fingerprint)

    def createFingerprint(self, fingerprint):
        """See `IHWSystemFingerprintSet`."""
        return HWSystemFingerprint(fingerprint=fingerprint)


class HWVendorName(SQLBase):
    """See `IHWVendorName`."""

    implements(IHWVendorName)

    _table = 'HWVendorName'

    name = StringCol(notNull=True)


class HWVendorNameSet:
    """See `IHWVendorNameSet`."""

    implements(IHWVendorNameSet)

    def create(self, name):
        """See `IHWVendorNameSet`."""
        return HWVendorName(name=name)

    def getByName(self, name):
        """See `IHWVendorNameSet`."""
        return HWVendorName.selectOne(
            'ulower(name)=ulower(%s)' % sqlvalues(name))


four_hex_digits = re.compile('^0x[0-9a-f]{4}$')
six_hex_digits = re.compile('^0x[0-9a-f]{6}$')
# The regular expressions for the SCSI vendor and product IDs are not as
# "picky" as the specification requires. Considering the fact that for
# example Microtek sold at least one scanner model that returns '        '
# as the vendor ID, it seems reasonable to allows also somewhat broken
# looking IDs.
scsi_vendor = re.compile('^.{8}$')
scsi_product = re.compile('^.{16}$')

validVendorID = {
    HWBus.PCI: four_hex_digits,
    HWBus.PCCARD: four_hex_digits,
    HWBus.USB: four_hex_digits,
    HWBus.IEEE1394: six_hex_digits,
    HWBus.SCSI: scsi_vendor,
    }

validProductID = {
    HWBus.PCI: four_hex_digits,
    HWBus.PCCARD: four_hex_digits,
    HWBus.USB: four_hex_digits,
    HWBus.SCSI: scsi_product,
    }

def isValidVendorID(bus, id):
    """Check that the string id is a valid vendor ID for this bus.

    :return: True, if id is valid, otherwise False
    :param bus: A `HWBus` indicating the bus type of "id"
    :param id: A string with the ID

    Some busses have constraints for IDs, while some can use arbitrary
    values, for example the "fake" busses HWBus.SYSTEM and HWBus.SERIAL.

    We use a hexadecimal representation of integers like "0x123abc",
    i.e., the numbers have the prefix "0x"; for the digits > 9 we
    use the lower case characters a to f.

    USB and PCI IDs have always four digits; IEEE1394 IDs have always
    six digits.

    SCSI vendor IDs consist of eight bytes of ASCII data (0x20..0x7e);
    if a vendor name has less than eight characters, it is padded on the
    right with spaces (See http://t10.org/ftp/t10/drafts/spc4/spc4r14.pdf,
    page 45).
    """
    if bus not in validVendorID:
        return True
    return validVendorID[bus].search(id) is not None


def isValidProductID(bus, id):
    """Check that the string id is a valid product for this bus.

    :return: True, if id is valid, otherwise False
    :param bus: A `HWBus` indicating the bus type of "id"
    :param id: A string with the ID

    Some busses have constraints for IDs, while some can use arbitrary
    values, for example the "fake" busses HWBus.SYSTEM and HWBus.SERIAL.

    We use a hexadecimal representation of integers like "0x123abc",
    i.e., the numbers have the prefix "0x"; for the digits > 9 we
    use the lower case characters a to f.

    USB and PCI IDs have always four digits.

    Since IEEE1394 does not specify product IDs, there is no formal
    check of them.

    SCSI product IDs consist of 16 bytes of ASCII data (0x20..0x7e);
    if a product name has less than 16 characters, it is padded on the
    right with spaces.
    """
    if bus not in validProductID:
        return True
    return validProductID[bus].search(id) is not None


class HWVendorID(SQLBase):
    """See `IHWVendorID`."""

    implements(IHWVendorID)

    _table = 'HWVendorID'

    bus = EnumCol(enum=HWBus, notNull=True)
    vendor_id_for_bus = StringCol(notNull=True)
    vendor_name = ForeignKey(dbName='vendor_name', foreignKey='HWVendorName',
                             notNull=True)

    def _create(self, id, **kw):
        bus = kw.get('bus')
        if bus is None:
            raise TypeError('HWVendorID() did not get expected keyword '
                            'argument bus')
        vendor_id_for_bus = kw.get('vendor_id_for_bus')
        if vendor_id_for_bus is None:
            raise TypeError('HWVendorID() did not get expected keyword '
                            'argument vendor_id_for_bus')
        if not isValidVendorID(bus, vendor_id_for_bus):
            raise ParameterError(
                '%s is not a valid vendor ID for %s'
                % (repr(vendor_id_for_bus), bus.title))
        SQLBase._create(self, id, **kw)


class HWVendorIDSet:
    """See `IHWVendorIDSet`."""

    implements(IHWVendorIDSet)

    def create(self, bus, vendor_id, vendor_name):
        """See `IHWVendorIDSet`."""
        vendor_name = HWVendorName.selectOneBy(name=vendor_name.name)
        return HWVendorID(bus=bus, vendor_id_for_bus=vendor_id,
                          vendor_name=vendor_name)

    def getByBusAndVendorID(self, bus, vendor_id):
        """See `IHWVendorIDSet`."""
        if not isValidVendorID(bus, vendor_id):
            raise ParameterError(
                '%s is not a valid vendor ID for %s'
                % (repr(vendor_id), bus.title))
        return HWVendorID.selectOneBy(bus=bus, vendor_id_for_bus=vendor_id)

    def get(self, id):
        """See `IHWVendorIDSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(HWVendorID, HWVendorID.id == id).one()

    def idsForBus(self, bus):
        """See `IHWVendorIDSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(HWVendorID, bus=bus)
        result_set.order_by(HWVendorID.vendor_id_for_bus)
        return result_set


class HWDevice(SQLBase):
    """See `IHWDevice.`"""

    implements(IHWDevice)
    _table = 'HWDevice'

    # XXX Abel Deuring 2008-05-02: The columns bus_vendor and
    # bus_product_id are supposed to be immutable. However, if they
    # are defined as "immutable=True", the creation of a new HWDevice
    # instance leads to an AttributeError in sqlobject/main.py, line 814.
    bus_vendor = ForeignKey(dbName='bus_vendor_id', foreignKey='HWVendorID',
                            notNull=True, immutable=False)
    bus_product_id = StringCol(notNull=True, dbName='bus_product_id',
                               immutable=False)
    variant = StringCol(notNull=False)
    name = StringCol(notNull=True)
    submissions = IntCol(notNull=True)

    @property
    def bus(self):
        return self.bus_vendor.bus

    @property
    def vendor_id(self):
        return self.bus_vendor.vendor_id_for_bus

    @property
    def vendor_name(self):
        return self.bus_vendor.vendor_name.name

    def _create(self, id, **kw):
        bus_vendor = kw.get('bus_vendor')
        if bus_vendor is None:
            raise TypeError('HWDevice() did not get expected keyword '
                            'argument bus_vendor')
        bus_product_id = kw.get('bus_product_id')
        if bus_product_id is None:
            raise TypeError('HWDevice() did not get expected keyword '
                            'argument bus_product_id')
        if not isValidProductID(bus_vendor.bus, bus_product_id):
            raise ParameterError(
                '%s is not a valid product ID for %s'
                % (repr(bus_product_id), bus_vendor.bus.title))
        SQLBase._create(self, id, **kw)

    def getSubmissions(self, driver=None, distribution=None,
                       distroseries=None, architecture=None, owner=None):
        """See `IHWDevice.`"""
        return HWSubmissionSet().search(
            device=self, driver=driver, distribution=distribution,
            distroseries=distroseries, architecture=architecture, owner=owner)

    @property
    def drivers(self):
        """See `IHWDevice.`"""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(HWDriver,
                                HWDeviceDriverLink.driver == HWDriver.id,
                                HWDeviceDriverLink.device == self)
        result_set.order_by((HWDriver.package_name, HWDriver.name))
        return result_set


class HWDeviceSet:
    """See `IHWDeviceSet`."""

    implements(IHWDeviceSet)

    def create(self, bus, vendor_id, product_id, product_name, variant=None):
        """See `IHWDeviceSet`."""
        vendor_id_record = HWVendorID.selectOneBy(bus=bus,
                                                  vendor_id_for_bus=vendor_id)
        if vendor_id_record is None:
            # The vendor ID may be unknown for two reasons:
            #   - we do not have anything like a subscription to newly
            #     assigned PCI or USB vendor IDs, so we may get submissions
            #     with IDs we don't know about yet.
            #   - we may get submissions with invalid IDs.
            # In both cases, we create a new HWVendorID entry with the
            # vendor name 'Unknown'.
            unknown_vendor = HWVendorName.selectOneBy(name=UNKNOWN)
            if unknown_vendor is None:
                unknown_vendor = HWVendorName(name=UNKNOWN)
            vendor_id_record = HWVendorID(bus=bus,
                                          vendor_id_for_bus=vendor_id,
                                          vendor_name=unknown_vendor)
        return HWDevice(bus_vendor=vendor_id_record,
                        bus_product_id=product_id, name=product_name,
                        variant=variant, submissions=0)

    def getByDeviceID(self, bus, vendor_id, product_id, variant=None):
        """See `IHWDeviceSet`."""
        if not isValidProductID(bus, product_id):
            raise ParameterError(
                '%s is not a valid product ID for %s'
                % (repr(product_id), bus.title))
        bus_vendor = HWVendorIDSet().getByBusAndVendorID(bus, vendor_id)
        return HWDevice.selectOneBy(bus_vendor=bus_vendor,
                                    bus_product_id=product_id,
                                    variant=variant)

    def getOrCreate(self, bus, vendor_id, product_id, product_name,
                    variant=None):
        """See `IHWDeviceSet`."""
        device = self.getByDeviceID(bus, vendor_id, product_id, variant)
        if device is None:
            return self.create(bus, vendor_id, product_id, product_name,
                               variant)
        return device

    def getByID(self, id):
        """See `IHWDeviceSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(HWDevice, HWDevice.id == id).one()

    def search(self, bus, vendor_id, product_id=None):
        """See `IHWDeviceSet`."""
        bus_vendor = HWVendorIDSet().getByBusAndVendorID(bus, vendor_id)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        args = []
        if product_id is not None:
            if not isValidProductID(bus, product_id):
                raise ParameterError(
                    '%s is not a valid product ID for %s'
                    % (repr(product_id), bus.title))
            args.append(HWDevice.bus_product_id == product_id)
        result_set = store.find(
            HWDevice, HWDevice.bus_vendor == bus_vendor, *args)
        result_set.order_by(HWDevice.id)
        return result_set


class HWDeviceNameVariant(SQLBase):
    """See `IHWDeviceNameVariant`."""

    implements(IHWDeviceNameVariant)
    _table = 'HWDeviceNameVariant'

    vendor_name = ForeignKey(dbName='vendor_name', foreignKey='HWVendorName',
                             notNull=True)
    product_name = StringCol(notNull=True)
    device = ForeignKey(dbName='device', foreignKey='HWDevice', notNull=True)
    submissions = IntCol(notNull=True)


class HWDeviceNameVariantSet:
    """See `IHWDeviceNameVariantSet`."""

    implements(IHWDeviceNameVariantSet)

    def create(self, device, vendor_name, product_name):
        """See `IHWDeviceNameVariantSet`."""
        vendor_name_record = HWVendorName.selectOneBy(name=vendor_name)
        if vendor_name_record is None:
            vendor_name_record = HWVendorName(name=vendor_name)
        return HWDeviceNameVariant(device=device,
                                   vendor_name=vendor_name_record,
                                   product_name=product_name,
                                   submissions=0)


class HWDriver(SQLBase):
    """See `IHWDriver`."""

    implements(IHWDriver)
    _table = 'HWDriver'

    # XXX: Abel Deuring 2008-12-10 bug=306265: package_name should
    # be declared notNull=True. This fixes the ambiguity that
    # "package_name is None" as well as "package_name == ''" can
    # indicate "we don't know to which package this driver belongs",
    # moreover, it gives a more clear meaning to the parameter value
    #package_name='' in webservice API calls.
    package_name = StringCol(notNull=False)
    name = StringCol(notNull=True)
    license = EnumCol(enum=License, notNull=False)

    def getSubmissions(self, distribution=None, distroseries=None,
                       architecture=None, owner=None):
        """See `IHWDriver.`"""
        return HWSubmissionSet().search(
            driver=self, distribution=distribution,
            distroseries=distroseries, architecture=architecture, owner=owner)


class HWDriverSet:
    """See `IHWDriver`."""

    implements(IHWDriverSet)

    def create(self, package_name, name, license):
        """See `IHWDriverSet`."""
        return HWDriver(package_name=package_name, name=name, license=license)

    def getByPackageAndName(self, package_name, name):
        """See `IHWDriverSet`."""
        return HWDriver.selectOneBy(package_name=package_name,
                                    name=name)

    def getOrCreate(self, package_name, name, license=None):
        """See `IHWDriverSet`."""
        link = HWDriver.selectOneBy(package_name=package_name,
                                    name=name)
        if link is None:
            return self.create(package_name, name, license)
        return link

    def search(self, package_name=None, name=None):
        """See `IHWDriverSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        args = []
        if package_name is not None:
            if len(package_name) == 0:
                args.append(Or(HWDriver.package_name == None,
                               HWDriver.package_name == ''))
            else:
                args.append(HWDriver.package_name == package_name)
        if name != None:
            args.append(HWDriver.name == name)
        result_set = store.find(HWDriver, *args)
        return result_set.order_by(HWDriver.id)

    def getByID(self, id):
        """See `IHWDriverSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(HWDriver, HWDriver.id == id).one()

    @property
    def package_names(self):
        """See `IHWDriverSet`."""
        # We want to return a distinct set of the values of the column
        # package_name. The attempt to do this the "standard way" with
        # Storm has two problems:
        # - The Storm API allows at present only the values None, True,
        #   False for result_set.config(distinct=...), but we would need
        #   here a value which results in the SQL clause
        #   DISTINCT ON (package_name)
        # - The result set entries would be tuples (package name, driver
        #   name), but the driver name is pure noise in this context.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.execute("""
            SELECT DISTINCT ON (package_name) package_name
                FROM HWDriver
                ORDER BY package_name
                """)
        # Return a shortlist, because returning result_set itself (which
        # is of type PostgresResult, while results of ordinary queries are
        # of type storm.store.ResultSet) would lead to ForbiddenAttribute
        # errors. We have currently (2009-02-12) ca. 350 distinct package
        # names, which is reasonably small.
        return shortlist([record[0] for record in result_set],
                         longest_expected=1000)


class HWDeviceDriverLink(SQLBase):
    """See `IHWDeviceDriverLink`."""

    implements(IHWDeviceDriverLink)
    _table = 'HWDeviceDriverLink'

    device = ForeignKey(dbName='device', foreignKey='HWDevice', notNull=True)
    driver = ForeignKey(dbName='driver', foreignKey='HWDriver', notNull=False)


class HWDeviceDriverLinkSet:
    """See `IHWDeviceDriverLinkSet`."""

    implements(IHWDeviceDriverLinkSet)

    def create(self, device, driver):
        """See `IHWDeviceDriverLinkSet`."""
        return HWDeviceDriverLink(device=device, driver=driver)

    def getByDeviceAndDriver(self, device, driver):
        """See `IHWDeviceDriverLink`."""
        return HWDeviceDriverLink.selectOneBy(device=device, driver=driver)

    def getOrCreate(self, device, driver):
        """See `IHWDeviceDriverLink`."""
        device_driver_link = self.getByDeviceAndDriver(device, driver)
        if device_driver_link is None:
            return self.create(device, driver)
        return device_driver_link


class HWDeviceClass(SQLBase):
    """See `IHWDeviceClass`."""
    implements(IHWDeviceClass)

    device = ForeignKey(dbName='device', foreignKey='HWDevice', notNull=True)
    main_class = EnumCol(enum=HWMainClass, notNull=True)
    sub_class = EnumCol(enum=HWSubClass)

    def _create(self, id, **kw):
        """Create a HWDeviceClass record.

        Ensure that main_class and sub_class have consistent values.
        """
        main_class = kw.get('main_class')
        if main_class is None:
            raise TypeError('HWDeviceClass() did not get expected keyword '
                            'argument main_class')
        sub_class = kw.get('sub_class')
        if sub_class is not None:
            if not sub_class.name.startswith(main_class.name + '_'):
                raise TypeError(
                    'HWDeviceClass() did not get matching argument values '
                    'for main_class: %r and sub_class: %r.'
                    % (main_class, sub_class))
        SQLBase._create(self, id, **kw)


class HWDeviceClassSet:
    """See `IHWDeviceClassSet`."""
    implements(IHWDeviceClassSet)

    def create(self, device, main_class, sub_class=None):
        """See `IHWDeviceClassSet`."""
        return HWDeviceClass(device=device, main_class=main_class,
                             sub_class=sub_class)


class HWSubmissionDevice(SQLBase):
    """See `IHWSubmissionDevice`."""

    implements(IHWSubmissionDevice)
    _table = 'HWSubmissionDevice'

    device_driver_link = ForeignKey(dbName='device_driver_link',
                                    foreignKey='HWDeviceDriverLink',
                                    notNull=True)
    submission = ForeignKey(dbName='submission', foreignKey='HWSubmission',
                            notNull=True)
    parent = ForeignKey(dbName='parent', foreignKey='HWSubmissionDevice',
                        notNull=False)

    hal_device_id = IntCol(notNull=True)

    @property
    def device(self):
        """See `IHWSubmissionDevice`."""
        return self.device_driver_link.device

    @property
    def driver(self):
        """See `IHWSubmissionDevice`."""
        return self.device_driver_link.driver


class HWSubmissionDeviceSet:
    """See `IHWSubmissionDeviceSet`."""

    implements(IHWSubmissionDeviceSet)

    def create(self, device_driver_link, submission, parent, hal_device_id):
        """See `IHWSubmissionDeviceSet`."""
        return HWSubmissionDevice(device_driver_link=device_driver_link,
                                  submission=submission, parent=parent,
                                  hal_device_id=hal_device_id)

    def getDevices(self, submission):
        """See `IHWSubmissionDeviceSet`."""
        return HWSubmissionDevice.selectBy(
            submission=submission,
            orderBy=['parent', 'device_driver_link', 'hal_device_id'])

    def get(self, id):
        """See `IHWSubmissionDeviceSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            HWSubmissionDevice, HWSubmissionDevice.id == id).one()


class HWSubmissionBug(SQLBase):
    """See `IHWSubmissionBug`."""

    implements(IHWSubmissionBug)
    _table = 'HWSubmissionBug'

    submission = ForeignKey(dbName='submission', foreignKey='HWSubmission',
                              notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)

class HWSubmissionBugSet:
    """See `IHWSubmissionBugSet`."""

    implements(IHWSubmissionBugSet)

    def create(self, submission, bug):
        """See `IHWSubmissionBugSet`."""
        return HWSubmissionBug(submission=submission, bug=bug)
