# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interfaces related to the hardware database."""

__metaclass__ = type

__all__ = [
    'HWSubmissionFormat',
    'HWSubmissionInvalidEmailAddress',
    'HWSubmissionKeyNotUnique',
    'HWSubmissionProcessingStatus',
    'IHWSubmission',
    'IHWSubmissionForm',
    'IHWSubmissionSet',
    'IHWSystemFingerprint',
    'IHWSystemFingerprintSet'
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    ASCIILine, Bool, Bytes, Choice, Datetime, Object, TextLine)

from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.validators import LaunchpadValidationError

def validate_new_submission_id(submission_id):
    """Check, if submission_id already exists in HWDBSubmission."""
    submission_set = getUtility(IHWSubmissionSet)
    if submission_set.submissionIdExists(submission_id):
        raise LaunchpadValidationError(
            'Submission ID already exists.')
    return True

class HWSubmissionKeyNotUnique(Exception):
    """Prevent two or more submission with identical submission_key."""

class HWSubmissionInvalidEmailAddress(Exception):
    """Reject submissions with invaild email addresses."""


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
    distroarchrelease = Attribute(
        _(u'The DistroArchSeries'))
    raw_submission = Object(
        schema=ILibraryFileAlias,
        title=_(u'The raw submission data'),
        required=True)
    system_fingerprint = Attribute(
        _(u'The system this submmission was made on'))


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
    livecd = Bool(
        title=_(u'Data from Live CD'), required=True)
    submission_id = ASCIILine(
        title=_(u'Unique Submission ID'), required=True,
        constraint=validate_new_submission_id)
    emailaddress = TextLine(
            title=_(u'Email address'), required=True)
    distribution = TextLine(
        title=_(u'Distribution'), required=True)
    distrorelease = TextLine(
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

    def getBySubmissionID(submission_key, user=None):
        """Return the submission with the given submission ID, or None.

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
        
