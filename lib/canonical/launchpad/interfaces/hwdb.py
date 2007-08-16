# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interfaces related to the hardware database."""

__metaclass__ = type

__all__ = [
    'HWDBSubmissionError',
    'HWDBSubmissionFormat',
    'HWDBSubmissionStatus',
    'IHWDBSubmission',
    'IHWDBSubmissionSet',
    'IHWDBSystemFingerprint',
    'IHWDBSystemFingerprintSet'
    ]

from textwrap import dedent

from zope.interface import Interface, Attribute
from zope.schema import (ASCIILine, Bool, Bytes, Choice, Datetime, Object,
    TextLine)

from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.email import valid_email

class HWDBSubmissionError(Exception):
    """Prevent two or more submission with identical submission_id."""


class HWDBSubmissionStatus(DBEnumeratedType):
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

class HWDBSubmissionFormat(DBEnumeratedType):
    """The format version of the submitted data."""

    VERSION_1 = DBItem(1, "Version 1")


class IHWDBSubmission(Interface):
    """Raw submission data for the hardware database."""

    date_created = Datetime(
        title=_(u'Date Created'), required=True)
    date_submitted = Datetime(
        title=_(u'Date Submitted'), required=True)
    format = Choice(
        title=_(u'Format Version'), required=True,
        vocabulary=HWDBSubmissionFormat)
    status = Choice(
        title=_(u'Submission Status'), required=True,
        vocabulary=HWDBSubmissionStatus)
    private = Bool(
        title=_(u'Private Submission'), required=True)
    contactable = Bool(
        title=_(u'Contactable'), required=True)
    live_cd = Bool(
        title=_(u'Data from Live CD'), required=True)
    submission_id = ASCIILine(
        title=_(u'Unique Submission ID'), required=True)
    owner = Attribute(
        _(u"The owner's IPerson"))
    emailaddress = TextLine(
        title=_('Email address'), required=True)
    distroarchseries = Attribute(
        _(u'The DistroArchSeries'))
    raw_submission = Object(
        schema=ILibraryFileAlias,
        title=_(u'The raw submission data'),
        required=True)
    system_fingerprint = Attribute(
        _(u'The system this submmission was made on'))


class IHWDBSubmissionSet(Interface):
    """The set of HWDBSubmissions."""

    def createSubmission(date_created, format, private, contactable,
                         live_cd, submission_id, emailaddress,
                         distroarchseries, raw_submission, filename,
                         filesize, system):
        """Store submitted raw hardware information in a Librarian file.

        If a submission with an identical submission_id already exists,
        an HWDBSubmissionError is raised."""

    def getBySubmissionID(submission_id, user=None):
        """Return the submission with the given submission ID, or None.

        If a submission is marked as private, it is only returned, if
        user == HWDBSubmission.owner.
        """

    def getByFingerprintName(name, user=None):
        """Return the submissions for the given system fingerprint string.

        If a submission is marked as private, it is only returned, if
        user == HWDBSubmission.owner.
        """

    def getByOwner(owner, user=None):
        """Return the submissions for the given person.

        If a submission is marked as private, it is only returned, if
        user == HWDBSubmission.owner.
        """


class IHWDBSystemFingerprint(Interface):
    """Identifiers of a computer system."""

    fingerprint = Attribute(u'A unique identifier of a system')


class IHWDBSystemFingerprintSet(Interface):
    """The set of HWDBSystemFingerprints."""

    def getByName(fingerprint):
        """Lookup an IHWDBSystemFingerprint by its value.

        Return None, if a fingerprint `fingerprint` does not exist."""

    def createFingerprint(fingerprint):
        """Create an entry in the fingerprint list.

        Return the new entry."""
        
