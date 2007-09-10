# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Hardware database related table classes."""

__all__ = ['HWSubmission',
           'HWSubmissionSet',
           'HWSystemFingerprint',
           'HWSystemFingerprintSet'
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
    HWSubmissionError, HWSubmissionFormat, HWSubmissionStatus,
    IHWSubmission, IHWSubmissionSet, IHWSystemFingerprint,
    IHWSystemFingerprintSet, ILibraryFileAliasSet, IPersonSet,
    PersonCreationRationale)

class HWSubmission(SQLBase):
    """Raw submission data"""

    implements(IHWSubmission)
    _table = 'HWSubmission'
    
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_submitted = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    format = EnumCol(enum=HWSubmissionFormat, notNull=True)
    status = EnumCol(enum=HWSubmissionStatus, notNull=True)
    private = BoolCol(notNull=True)
    contactable = BoolCol(notNull=True)
    live_cd = BoolCol(notNull=True, default=False)
    submission_id = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person')
    distroarchrelease = ForeignKey(dbName='distroarchseries',
                                   foreignKey='Distroarchrelease')
    raw_submission = ForeignKey(dbName='raw_submission',
                                foreignKey='LibraryFileAlias')
    system_fingerprint = ForeignKey(dbName='system_fingerprint',
                                    foreignKey='HWSystemFingerprint')


class HWSubmissionSet:
    """See `IHWSubmissionSet`."""

    implements(IHWSubmissionSet)

    def createSubmission(self, date_created, format, private, contactable,
                         live_cd, submission_id, emailaddress,
                         distroarchseries, raw_submission, filename,
                         filesize, system_fingerprint):
        """See `IHWSubmissionSet`."""
        
        submission_exists = HWSubmission.select(
            'submission_id=%s' % sqlvalues(submission_id)).count() > 0
        if submission_exists:
            raise HWSubmissionError(
                'A submission with this ID already exists')
        
        personset = getUtility(IPersonSet)
        owner = personset.getByEmail(emailaddress)
        if owner is None:
            owner, email = personset.createPersonAndEmail(
                emailaddress,
                PersonCreationRationale.OWNER_SUBMITTED_HARDWARE_TEST)
            if owner is None:
                raise HWSubmissionError, 'invalid email address'

        fingerprint = HWSystemFingerprint.selectOneBy(
            fingerprint=system_fingerprint)
        if fingerprint is None:
            fingerprint = HWSystemFingerprint(fingerprint=system_fingerprint)

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

        return HWSubmission(
            date_created=date_created,
            date_submitted=datetime.now(pytz.timezone('UTC')),
            format=format,
            status=HWSubmissionStatus.SUBMITTED,
            private=private,
            contactable=contactable,
            live_cd=live_cd,
            submission_id=submission_id,
            owner=owner,
            distroarchrelease=distroarchseries,
            raw_submission=libraryfile,
            system_fingerprint=fingerprint)

    def getBySubmissionID(self, submission_id, user=None):
        """See `IHWSubmissionSet`."""
        if user is None:
            query = "submission_id=%s AND not private"
            query = query % sqlvalues(submission_id)
        else:
            query = "submission_id=%s AND (not private OR owner=%s)"
            query = query % sqlvalues(submission_id, user)
        return HWSubmission.selectOne(query)

    def getByFingerprintName(self, name, user=None):
        """See `IHWSubmissionSet`."""
        fp = HWSystemFingerprintSet().getByName(name)
        if user is None:
            # Sorting is done by system name first, i.e., by a column
            # of the "foreign" table HWSystemFingerprint. Unfortunately,
            # the straightforward way to add the parameters
            # "orderBy=['HWSystemFingerprint.fingerprint']" and
            # "prejoins=['system']" to the select() call does not work,
            # because SQLObject creates the the SQL expression
            # "LEFT OUTER JOIN HWSystemFingerprint AS _prejoin0", which
            # means that the orderBy expression would be
            # "_prejoin0.fingerprint", which does not look not very obvious,
            # and depends on implementation details. Hence the table
            # HWSystemFingerprint is explicitly joined a second time, and
            # the sorting done on the column of this "second join".
            query = """
                system_fingerprint=%s
                AND not private
                AND HWSystemFingerprint.id = HWSubmission.system_fingerprint
                """ % sqlvalues(fp)
        else:
            query = """
                system_fingerprint=%s
                AND (not private OR owner=%s)
                AND HWSystemFingerprint.id = HWSubmission.system_fingerprint
                """ % sqlvalues(fp, user)
        return HWSubmission.select(
            query,
            prejoins=['system_fingerprint'],
            clauseTables=['HWSystemFingerprint'],
            prejoinClauseTables=['HWSystemFingerprint'],
            orderBy=['HWSystemFingerprint.fingerprint',
                     'date_submitted',
                     'submission_id'])

    def getByOwner(self, owner, user=None):
        """See `IHWSubmissionSet`."""
        if user is None:
            query = """
                owner=%s
                AND not private
                AND HWSystemFingerprint.id = HWSubmission.system_fingerprint
                """ % sqlvalues(owner)
        else:
            query = """
                owner=%s
                AND (not private OR owner=%s)
                AND HWSystemFingerprint.id = HWSubmission.system_fingerprint
                """ % sqlvalues(owner, user)
        return HWSubmission.select(
            query,
            clauseTables=['HWSystemFingerprint'],
            prejoinClauseTables=['HWSystemFingerprint'],
            orderBy=['HWSystemFingerprint.fingerprint',
                     'date_submitted',
                     'submission_id'])


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
