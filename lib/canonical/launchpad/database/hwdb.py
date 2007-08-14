# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Hardware database related table classes."""

__all__ = ['HWDBSubmission',
           'HWDBSubmissionSet',
           'HWDBSystemFingerprint',
           'HWDBSystemFingerprintSet'
          ]

from datetime import datetime

import pytz

from zope.component import getUtility
from zope.interface import implements

from sqlobject import BoolCol, ForeignKey, StringCol

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import (
    HWDBSubmissionError, HWDBSubmissionFormat, HWDBSubmissionStatus,
    IHWDBSubmission, IHWDBSubmissionSet, IHWDBSystemFingerprint,
    IHWDBSystemFingerprintSet, ILibraryFileAliasSet, IPersonSet)

class HWDBSubmission(SQLBase):
    """Raw submission data"""

    implements(IHWDBSubmission)
    _table = 'HWDBSubmission'
    
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_submitted = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    format = EnumCol(enum=HWDBSubmissionFormat, notNull=True)
    status = EnumCol(enum=HWDBSubmissionStatus, notNull=True)
    private = BoolCol(notNull=True)
    contactable = BoolCol(notNull=True)
    livecd = BoolCol(notNull=True, default=False)
    submission_id = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person')
    emailaddress = StringCol(notNull=True)
    distroarchrelease = ForeignKey(dbName='distroarchrelease',
                                   foreignKey='DistroArchSeries')
    raw_submission = ForeignKey(dbName='raw_submission',
                                foreignKey='LibraryFileAlias')
    system = ForeignKey(dbName='system', foreignKey='HWDBSystemFingerprint')


class HWDBSubmissionSet:
    """See `IHWDBSubmissionSet`."""

    implements(IHWDBSubmissionSet)

    def createSubmission(self, date_created, format, private, contactable,
                         livecd, submission_id, emailaddress,
                         distroarchseries, raw_submission, filename,
                         filesize, system):
        """See `IHWDBSubmissionSet`."""
        
        submission_exists = HWDBSubmission.select(
            'submission_id=%s' % sqlvalues(submission_id)).count() > 0
        if submission_exists:
            raise HWDBSubmissionError(
                'A submission with this ID already exists')
        
        owner = getUtility(IPersonSet).getByEmail(emailaddress)
        
        fingerprint = HWDBSystemFingerprint.selectOneBy(fingerprint=system)
        if fingerprint is None:
            fingerprint = HWDBSystemFingerprint(fingerprint=system)

        libraryfileset = getUtility(ILibraryFileAliasSet)
        libraryfile = libraryfileset.create(
            name=filename,
            size=filesize,
            file=raw_submission,
            # We expect data in XML format, and simply assume here that we
            # received such data.  It will turn out later, when the data
            # is parsed, if this assumption is correct.
            contentType='text/xml',
            expires=None)

        return HWDBSubmission(
            date_created=date_created,
            date_submitted=datetime.now(pytz.timezone('UTC')),
            format=format,
            status=HWDBSubmissionStatus.SUBMITTED,
            private=private,
            contactable=contactable,
            livecd=livecd,
            submission_id=submission_id,
            owner=owner,
            emailaddress=emailaddress,
            distroarchrelease=distroarchseries,
            raw_submission=libraryfile,
            system=fingerprint)

    def getBySubmissionID(self, submission_id, user=None):
        """See `IHWDBSubmissionSet`."""
        if user is None:
            query = "submission_id=%s AND not private"
            query = query % sqlvalues(submission_id)
        else:
            query = "submission_id=%s AND (not private OR owner=%s)"
            query = query % sqlvalues(submission_id, user)
        return HWDBSubmission.selectOne(query)

    def getByFingerprintName(self, name, user=None):
        """See `IHWDBSubmissionSet`."""
        fp = HWDBSystemFingerprintSet().getByName(name)
        if user is None:
            # Sorting is done by system name first, i.e., by a column
            # of the "foreign" table HWDBSystemFingerprint. Unfortunately,
            # the straightforward way to add the parameters
            # "orderBy=['HWDBSystemFingerprint.fingerprint']" and
            # "prejoins=['system']" to the select() call does not work,
            # because SQLObject creates the the SQL expression
            # "LEFT OUTER JOIN HWDBSystemFingerprint AS _prejoin0", which
            # means that the orderBy expression would be
            # "_prejoin0.fingerprint", which does not look not very obvious,
            # and depends on implementation details. Hence the table
            # HWDBSystemFingerprint is explicitly joined a second time, and
            # the sorting done on the column of this "second join".
            query = """
                system=%s
                AND not private
                AND HWDBSystemFingerprint.id = HWDBSubmission.system
                """ % sqlvalues(fp)
        else:
            query = """
                system=%s
                AND (not private OR owner=%s)
                AND HWDBSystemFingerprint.id = HWDBSubmission.system
                """ % sqlvalues(fp, user)
        return HWDBSubmission.select(
            query,
            prejoins=['system'],
            clauseTables=['HWDBSystemFingerprint'],
            prejoinClauseTables=['HWDBSystemFingerprint'],
            orderBy=['HWDBSystemFingerprint.fingerprint',
                     'date_submitted',
                     'submission_id'])

    def getByOwner(self, owner, user=None):
        """See `IHWDBSubmissionSet`."""
        if user is None:
            query = """
                owner=%s
                AND not private
                AND HWDBSystemFingerprint.id = HWDBSubmission.system
                """ % sqlvalues(owner)
        else:
            query = """
                owner=%s
                AND (not private OR owner=%s)
                AND HWDBSystemFingerprint.id = HWDBSubmission.system
                """ % sqlvalues(owner, user)

        return HWDBSubmission.select(
            query,
            clauseTables=['HWDBSystemFingerprint'],
            prejoinClauseTables=['HWDBSystemFingerprint'],
            orderBy=['HWDBSystemFingerprint.fingerprint',
                     'date_submitted',
                     'submission_id'])

    def submissionIdExists(self, submission_id):
        """See `IHWDBSubmissionSet`."""
        rows = HWDBSubmission.selectBy(submission_id=submission_id)
        return rows.count() > 0


class HWDBSystemFingerprint(SQLBase):
    """Identifiers of a computer system."""

    implements(IHWDBSystemFingerprint)
    _table = 'HWDBSystemFingerprint'

    fingerprint = StringCol(notNull=True)


class HWDBSystemFingerprintSet:
    """A set of identifiers of a computer system."""

    implements(IHWDBSystemFingerprintSet)

    def getByName(self, fingerprint):
        """See `IHWDBSystemFingerprintSet`."""
        return HWDBSystemFingerprint.selectOneBy(fingerprint=fingerprint)

    def createFingerprint(self, fingerprint):
        """See `IHWDBSystemFingerprintSet`."""
        return HWDBSystemFingerprint(fingerprint=fingerprint)
