# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interfaces related to the hardware database."""

__metaclass__ = type

__all__ = [
    'HWSubmissionFormat',
    'HWSubmissionInvalidEmailAddress',
    'HWSubmissionKeyNotUnique',
    'HWSubmissionProcessingStatus',
    'IHWSubmission',
    'IHWSubmissionSet',
    'IHWSystemFingerprint',
    'IHWSystemFingerprintSet'
    ]

from zope.interface import Interface, Attribute
from zope.schema import ASCIILine, Bool, Choice, Datetime, Object

from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias

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


class IHWSubmissionSet(Interface):
    """The set of HWSubmissions."""

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
        
