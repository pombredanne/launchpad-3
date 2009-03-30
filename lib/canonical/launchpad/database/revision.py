# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'Revision', 'RevisionAuthor', 'RevisionParent', 'RevisionProperty',
    'RevisionSet']

from datetime import datetime, timedelta
import email

import pytz
from storm.expr import And, Asc, Desc, Exists, Join, Not, Select
from storm.locals import Min
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements
from sqlobject import (
    BoolCol, ForeignKey, IntCol, StringCol, SQLObjectNotFound,
    SQLMultipleJoin)

from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import quote, SQLBase, sqlvalues

from canonical.launchpad.interfaces import (
    EmailAddressStatus, IEmailAddressSet, IRevision, IRevisionAuthor,
    IRevisionParent, IRevisionProperty, IRevisionSet)
from canonical.launchpad.interfaces.branch import (
    DEFAULT_BRANCH_STATUS_IN_LISTING)
from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.project import IProject
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
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

    karma_allocated = BoolCol(default=False, notNull=True)

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
        """See `IRevision`."""
        return dict((prop.name, prop.value) for prop in self.properties)

    def allocateKarma(self, branch):
        """See `IRevision`."""
        # If we know who the revision author is, give them karma.
        author = self.revision_author.person
        if (author is not None and branch.product is not None):
            # No karma for junk branches as we need a product to link
            # against.
            karma = author.assignKarma('revisionadded', branch.product)
            # Backdate the karma to the time the revision was created.  If the
            # revision_date on the revision is in future (for whatever weird
            # reason) we will use the date_created from the revision (which
            # will be now) as the karma date created.  Having future karma
            # events is both wrong, as the revision has been created (and it
            # is lying), and a problem with the way the Launchpad code
            # currently does its karma degradation over time.
            if karma is not None:
                karma.datecreated = min(self.revision_date, self.date_created)
                self.karma_allocated = True

    def getBranch(self, allow_private=False, allow_junk=True):
        """See `IRevision`."""
        from canonical.launchpad.database.branch import Branch
        from canonical.launchpad.database.branchrevision import BranchRevision

        store = Store.of(self)

        query = And(
            self.id == BranchRevision.revisionID,
            BranchRevision.branchID == Branch.id)
        if not allow_private:
            query = And(query, Not(Branch.private))
        if not allow_junk:
            # XXX: Tim Penhey 2008-08-20, bug 244768
            # Using Not(column == None) rather than column != None.
            query = And(query, Not(Branch.product == None))
        result_set = store.find(Branch, query)
        if self.revision_author.person is None:
            result_set.order_by(Asc(BranchRevision.sequence))
        else:
            result_set.order_by(
                Branch.ownerID != self.revision_author.personID,
                Asc(BranchRevision.sequence))

        return result_set.first()


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
        # Don't create future revisions.
        if revision.revision_date > revision.date_created:
            revision.revision_date = revision.date_created

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

    def _timestampToDatetime(self, timestamp):
        """Convert the given timestamp to a datetime object.

        This works around a bug in Python that causes datetime.fromtimestamp
        to raise an exception if it is given a negative, fractional timestamp.

        :param timestamp: A timestamp from a bzrlib.revision.Revision
        :type timestamp: float

        :return: A datetime corresponding to the given timestamp.
        """
        # Work around Python bug #1646728.
        # See https://launchpad.net/bugs/81544.
        UTC = pytz.timezone('UTC')
        int_timestamp = int(timestamp)
        revision_date = datetime.fromtimestamp(int_timestamp, tz=UTC)
        revision_date += timedelta(seconds=timestamp - int_timestamp)
        return revision_date

    def newFromBazaarRevision(self, bzr_revision):
        """See `IRevisionSet`."""
        revision_id = bzr_revision.revision_id
        revision_date = self._timestampToDatetime(bzr_revision.timestamp)
        return self.new(
            revision_id=revision_id,
            log_body=bzr_revision.message,
            revision_date=revision_date,
            revision_author=bzr_revision.get_apparent_author(),
            parent_ids=bzr_revision.parent_ids,
            properties=bzr_revision.properties)

    @staticmethod
    def onlyPresent(revids):
        """See `IRevisionSet`."""
        if not revids:
            return set()
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute(
            """
            CREATE TEMPORARY TABLE Revids
            (revision_id text)
            """)
        data = []
        for revid in revids:
            data.append('(%s)' % sqlvalues(revid))
        data = ', '.join(data)
        store.execute(
            "INSERT INTO Revids (revision_id) VALUES %s" % data)
        result = store.execute(
            """
            SELECT Revids.revision_id
            FROM Revids, Revision
            WHERE Revids.revision_id = Revision.revision_id
            """)
        present = set()
        for row in result.get_all():
            present.add(row[0])
        store.execute("DROP TABLE Revids")
        return present

    def checkNewVerifiedEmail(self, email):
        """See `IRevisionSet`."""
        from zope.security.proxy import removeSecurityProxy
        # Bypass zope's security because IEmailAddress.email is not public.
        naked_email = removeSecurityProxy(email)
        for author in RevisionAuthor.selectBy(email=naked_email.email):
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

    @staticmethod
    def getRecentRevisionsForProduct(product, days):
        """See `IRevisionSet`."""
        # Here to stop circular imports.
        from canonical.launchpad.database.branch import Branch
        from canonical.launchpad.database.branchrevision import BranchRevision

        revision_subselect = Select(
            Min(Revision.id), revision_time_limit(days))
        # Only look in active branches.
        result_set = Store.of(product).find(
            (Revision, RevisionAuthor),
            Revision.revision_author == RevisionAuthor.id,
            revision_time_limit(days),
            BranchRevision.revision == Revision.id,
            BranchRevision.branch == Branch.id,
            Branch.product == product,
            Branch.lifecycle_status.is_in(DEFAULT_BRANCH_STATUS_IN_LISTING),
            BranchRevision.revisionID >= revision_subselect)
        result_set.config(distinct=True)
        return result_set.order_by(Desc(Revision.revision_date))

    @staticmethod
    def getRevisionsNeedingKarmaAllocated():
        """See `IRevisionSet`."""
        # Here to stop circular imports.
        from canonical.launchpad.database.branch import Branch
        from canonical.launchpad.database.branchrevision import BranchRevision
        from canonical.launchpad.database.person import ValidPersonCache

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # XXX: Tim Penhey 2008-08-12, bug 244768
        # Using Not(column == None) rather than column != None.
        return store.find(
            Revision,
            Revision.revision_author == RevisionAuthor.id,
            RevisionAuthor.person == ValidPersonCache.id,
            Not(Revision.karma_allocated),
            Exists(
                Select(True,
                       And(BranchRevision.revision == Revision.id,
                           BranchRevision.branch == Branch.id,
                           Not(Branch.product == None)),
                       (Branch, BranchRevision))))

    @staticmethod
    def getPublicRevisionsForPerson(person, day_limit=30):
        """See `IRevisionSet`."""
        # Here to stop circular imports.
        from canonical.launchpad.database.branch import Branch
        from canonical.launchpad.database.branchrevision import BranchRevision
        from canonical.launchpad.database.teammembership import (
            TeamParticipation)

        store = Store.of(person)

        origin = [
            Revision,
            Join(BranchRevision, BranchRevision.revision == Revision.id),
            Join(Branch, BranchRevision.branch == Branch.id),
            Join(RevisionAuthor,
                 Revision.revision_author == RevisionAuthor.id),
            ]

        if person.is_team:
            origin.append(
                Join(TeamParticipation,
                     RevisionAuthor.personID == TeamParticipation.personID))
            person_condition = TeamParticipation.team == person
        else:
            person_condition = RevisionAuthor.person == person

        result_set = store.using(*origin).find(
            Revision,
            And(revision_time_limit(day_limit),
                person_condition,
                Not(Branch.private)))
        result_set.config(distinct=True)
        return result_set.order_by(Desc(Revision.revision_date))

    @staticmethod
    def _getPublicRevisionsHelper(obj, day_limit):
        """Helper method for Products and Projects."""
        # Here to stop circular imports.
        from canonical.launchpad.database.branch import Branch
        from canonical.launchpad.database.product import Product
        from canonical.launchpad.database.branchrevision import BranchRevision

        origin = [
            Revision,
            Join(BranchRevision, BranchRevision.revision == Revision.id),
            Join(Branch, BranchRevision.branch == Branch.id),
            ]

        conditions = And(revision_time_limit(day_limit),
                         Not(Branch.private))

        if IProduct.providedBy(obj):
            conditions = And(conditions, Branch.product == obj)
        elif IProject.providedBy(obj):
            origin.append(Join(Product, Branch.product == Product.id))
            conditions = And(conditions, Product.project == obj)
        else:
            raise AssertionError(
                "obj parameter must be an IProduct or IProject: %r" % obj)

        result_set = Store.of(obj).using(*origin).find(
            Revision, conditions)
        result_set.config(distinct=True)
        return result_set.order_by(Desc(Revision.revision_date))

    @classmethod
    def getPublicRevisionsForProduct(cls, product, day_limit=30):
        """See `IRevisionSet`."""
        return cls._getPublicRevisionsHelper(product, day_limit)

    @classmethod
    def getPublicRevisionsForProject(cls, project, day_limit=30):
        """See `IRevisionSet`."""
        return cls._getPublicRevisionsHelper(project, day_limit)


def revision_time_limit(day_limit):
    """The storm fragment to limit the revision_date field of the Revision."""
    now = datetime.now(pytz.UTC)
    earliest = now - timedelta(days=day_limit)

    return And(
        Revision.revision_date <= now,
        Revision.revision_date > earliest)
