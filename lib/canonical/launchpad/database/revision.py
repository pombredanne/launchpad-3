# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'Revision', 'RevisionAuthor', 'RevisionParent', 'RevisionProperty',
    'RevisionSet']

import email

from zope.component import getUtility
from zope.interface import implements
from sqlobject import (
    ForeignKey, IntCol, StringCol, SQLObjectNotFound, SQLMultipleJoin)

from canonical.database.sqlbase import quote, SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    EmailAddressStatus, IEmailAddressSet,
    IRevision, IRevisionAuthor, IRevisionParent, IRevisionProperty,
    IRevisionSet)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.validators.person import validate_public_person


class Revision(SQLBase):
    """See IRevision."""

    implements(IRevision)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    log_body = StringCol(notNull=True)
    gpgkey = ForeignKey(dbName='gpgkey', foreignKey='GPGKey', default=None)

    revision_author = ForeignKey(
        dbName='revision_author', foreignKey='RevisionAuthor', notNull=True)
    revision_id = StringCol(notNull=True, alternateID=True,
                            alternateMethodName='byRevisionID')
    revision_date = UtcDateTimeCol(notNull=False)

    properties = SQLMultipleJoin('RevisionProperty', joinColumn='revision')

    @property
    def parents(self):
        """See IRevision.parents"""
        return shortlist(RevisionParent.selectBy(
            revision=self, orderBy='sequence'))

    @property
    def parent_ids(self):
        """Sequence of globally unique ids for the parents of this revision.

        The corresponding Revision objects can be retrieved, if they are
        present in the database, using the RevisionSet Zope utility.
        """
        return [parent.parent_id for parent in self.parents]

    def getProperties(self):
        """See IRevision."""
        return dict((prop.name, prop.value) for prop in self.properties)


class RevisionAuthor(SQLBase):
    implements(IRevisionAuthor)

    _table = 'RevisionAuthor'

    name = StringCol(notNull=True, alternateID=True)

    @property
    def name_without_email(self):
        """Return the name of the revision author without the email address.

        If there is no name information (i.e. when the revision author only
        supplied their email address), return None.
        """
        if '@' not in self.name:
            return self.name
        return email.Utils.parseaddr(self.name)[0]

    email = StringCol(notNull=False, default=None)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=False,
                        storm_validator=validate_public_person, default=None)

    def linkToLaunchpadPerson(self):
        """See `IRevisionAuthor`."""
        if self.person is not None or self.email is None:
            return False
        lp_email = getUtility(IEmailAddressSet).getByEmail(self.email)
        # If not found, we didn't link this person.
        if lp_email is None:
            return False
        # Only accept an email address that is validated.
        if lp_email.status != EmailAddressStatus.NEW:
            self.person = lp_email.person
            return True
        else:
            return False


class RevisionParent(SQLBase):
    """The association between a revision and its parent."""

    implements(IRevisionParent)

    _table = 'RevisionParent'

    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)

    sequence = IntCol(notNull=True)
    parent_id = StringCol(notNull=True)


class RevisionProperty(SQLBase):
    """A property on a revision. See IRevisionProperty."""

    implements(IRevisionProperty)

    _table = 'RevisionProperty'

    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)
    name = StringCol(notNull=True)
    value = StringCol(notNull=True)


class RevisionSet:

    implements(IRevisionSet)

    def getByRevisionId(self, revision_id):
        return Revision.selectOneBy(revision_id=revision_id)

    def _createRevisionAuthor(self, revision_author):
        """Extract out the email and check to see if it matches a Person."""
        email_address = email.Utils.parseaddr(revision_author)[1]
        # If there is no @, then it isn't a real email address.
        if '@' not in email_address:
            email_address = None

        author = RevisionAuthor(name=revision_author, email=email_address)
        author.linkToLaunchpadPerson()
        return author

    def new(self, revision_id, log_body, revision_date, revision_author,
            parent_ids, properties):
        """See IRevisionSet.new()"""
        if properties is None:
            properties = {}
        # create a RevisionAuthor if necessary:
        try:
            author = RevisionAuthor.byName(revision_author)
        except SQLObjectNotFound:
            author = self._createRevisionAuthor(revision_author)

        revision = Revision(revision_id=revision_id,
                            log_body=log_body,
                            revision_date=revision_date,
                            revision_author=author)
        seen_parents = set()
        for sequence, parent_id in enumerate(parent_ids):
            if parent_id in seen_parents:
                continue
            seen_parents.add(parent_id)
            RevisionParent(revision=revision, sequence=sequence,
                           parent_id=parent_id)

        # Create revision properties.
        for name, value in properties.iteritems():
            RevisionProperty(revision=revision, name=name, value=value)

        return revision

    def checkNewVerifiedEmail(self, email):
        """See `IRevisionSet`."""
        for author in RevisionAuthor.selectBy(email=email.email):
            author.person = email.person

    def getTipRevisionsForBranches(self, branches):
        """See `IRevisionSet`."""
        # If there are no branch_ids, then return None.
        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            return None
        return Revision.select("""
            Branch.id in %s AND
            Revision.revision_id = Branch.last_scanned_id
            """ % quote(branch_ids),
            clauseTables=['Branch'], prejoins=['revision_author'])
