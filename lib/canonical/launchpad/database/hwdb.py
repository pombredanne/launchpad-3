# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Hardware database related table classes."""

__all__ = [
    'HWSubmission',
    'HWSubmissionSet',
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

from sqlobject import BoolCol, ForeignKey, StringCol

from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import (
    EmailAddressStatus, HWBus, HWSubmissionFormat, HWSubmissionKeyNotUnique,
    HWSubmissionProcessingStatus, IHWSubmission, IHWSubmissionSet,
    IHWSystemFingerprint, IHWSystemFingerprintSet, IHWVendorID,
    IHWVendorIDSet, IHWVendorName, IHWVendorNameSet, ILaunchpadCelebrities,
    ILibraryFileAliasSet, IPersonSet)
from canonical.launchpad.validators.person import validate_public_person


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
    raw_emailaddress = StringCol(notNull=True)


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
        owner = personset.getByEmail(emailaddress)

        fingerprint = HWSystemFingerprint.selectOneBy(
            fingerprint=system_fingerprint)
        if fingerprint is None:
            fingerprint = HWSystemFingerprint(fingerprint=system_fingerprint)

        libraryfileset = getUtility(ILibraryFileAliasSet)
        libraryfile = libraryfileset.create(
            name=filename,
            size=filesize,
            file=raw_submission,
            # XXX: The hwdb client sends us bzipped XML, but arguably
            # other clients could send us other formats. The right way
            # to do this is either to enforce the format in the browser
            # code, allow the client to specify the format, or use a
            # magic module to sniff what it is we got.
            #   -- kiko, 2007-09-20
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

    def getBySubmissionKey(self, submission_key, user=None):
        """See `IHWSubmissionSet`."""
        query = "submission_key=%s" % sqlvalues(submission_key)
        query = query + self._userHasAccessClause(user)

        return HWSubmission.selectOne(query)

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
        person = email.person
        submissions =  HWSubmission.selectBy(
            raw_emailaddress=email.email, owner=None)
        for submission in submissions:
            submission.owner = person


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
    HWBus.USB: four_hex_digits,
    HWBus.IEEE1394: six_hex_digits,
    HWBus.SCSI: scsi_vendor,
    }

validProductID = {
    HWBus.PCI: four_hex_digits,
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
            raise ValueError('%s is not a valid vendor ID for %s'
                             % (repr(vendor_id_for_bus),
                                bus.title))
        SQLBase._create(self, id, **kw)


class HWVendorIDSet:
    """See `IHWVendorIDSet`."""

    implements(IHWVendorIDSet)

    def create(self, bus, vendor_id, vendor_name):
        """See `IHWVendorIDSet`."""
        vendor_name = HWVendorName.selectOneBy(name=vendor_name.name)
        return HWVendorID(bus=bus, vendor_id_for_bus=vendor_id,
                          vendor_name=vendor_name)
