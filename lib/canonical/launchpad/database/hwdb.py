# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Hardware database related table classes."""

__all__ = ['HWSubmission',
           'HWSubmissionSet',
           'HWSystemFingerprint',
           'HWSystemFingerprintSet'
          ]

from zope.component import getUtility
from zope.interface import implements

from sqlobject import BoolCol, ForeignKey, StringCol

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import (
    EmailAddressStatus, HWSubmissionFormat, HWSubmissionKeyNotUnique,
    HWSubmissionProcessingStatus, IHWSubmission, IHWSubmissionSet,
    IHWSystemFingerprint, IHWSystemFingerprintSet, ILaunchpadCelebrities,
    ILibraryFileAliasSet, IPersonSet)


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
    owner = ForeignKey(dbName='owner', foreignKey='Person')
    distroarchseries = ForeignKey(dbName='DistroArchSeries',
                                  foreignKey='DistroArchSeries',
                                  notNull=True)
    raw_submission = ForeignKey(dbName='raw_submission',
                                foreignKey='LibraryFileAlias',
                                notNull=True)
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
        """Limit results of HWSubmission queries to rows the user can access."""
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
        return bool(rows)
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
