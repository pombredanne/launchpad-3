# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Tests for Revisions."""

__metaclass__ = type

from datetime import datetime, timedelta
import time
from unittest import TestCase, TestLoader

import psycopg2
import pytz
from storm.store import Store

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import cursor
from canonical.launchpad.database.karma import Karma
from canonical.launchpad.database.revision import RevisionSet
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import IRevisionSet
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.branchlookup import IBranchLookup
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory, time_counter)
from canonical.testing import DatabaseFunctionalLayer


class TestRevisionKarma(TestCaseWithFactory):
    """Test the allocation of karma for revisions."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "admin@canonical.com")

    def test_revisionWithUnknownEmail(self):
        # A revision when created does not have karma allocated.
        rev = self.factory.makeRevision()
        self.failIf(rev.karma_allocated)
        # Even if the revision author is someone we know.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        self.failIf(rev.karma_allocated)

    def test_noKarmaForUnknownAuthor(self):
        # If the revision author is unknown, karma isn't allocated.
        rev = self.factory.makeRevision()
        branch = self.factory.makeProductBranch()
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)

    def test_noRevisionsNeedingAllocation(self):
        # There are no outstanding revisions needing karma allocated.
        self.assertEqual(
            [], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

    def test_karmaAllocatedForKnownAuthor(self):
        # If the revision author is known, allocate karma.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email,
            revision_date=datetime.now(pytz.UTC) - timedelta(days=5))
        branch = self.factory.makeProductBranch()
        branch.createBranchRevision(1, rev)
        self.failUnless(rev.karma_allocated)
        # Get the karma event.
        [karma] = list(Store.of(author).find(
            Karma,
            Karma.person == author,
            Karma.product == branch.product))
        self.assertEqual(karma.datecreated, rev.revision_date)
        self.assertEqual(karma.product, branch.product)
        # Since karma has been allocated, the revision isn't in our list.
        self.assertEqual(
            [], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

    def test_karmaNotAllocatedForKnownAuthorWithInactiveAccount(self):
        # If the revision author is known, but the account is not active,
        # don't allocate karma.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        author.account.status = AccountStatus.SUSPENDED
        branch = self.factory.makeProductBranch()
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)
        # Even though the revision author is connected to the person, since
        # the account status is suspended, the person is not "valid", and so
        # the revisions are not returned as needing karma allocated.
        self.assertEqual(
            [], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

    def test_noKarmaForJunk(self):
        # Revisions only associated with junk branches don't get karma.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        branch = self.factory.makePersonalBranch()
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)
        # Nor is this revision identified as needing karma allocated.
        self.assertEqual(
            [], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

    def test_junkBranchMovedToProductNeedsKarma(self):
        # A junk branch that moves to a product needs karma allocated.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        branch = self.factory.makePersonalBranch()
        branch.createBranchRevision(1, rev)
        # Once the branch is connected to the revision, we now specify
        # a product for the branch.
        branch.product = self.factory.makeProduct()
        # The revision is now identified as needing karma allocated.
        self.assertEqual(
            [rev], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

    def test_newRevisionAuthorLinkNeedsKarma(self):
        # If Launchpad knows of revisions by a particular author, and later
        # that authoer registers with launchpad, the revisions need karma
        # allocated.
        email = self.factory.getUniqueEmailAddress()
        rev = self.factory.makeRevision(author=email)
        branch = self.factory.makeProductBranch()
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)
        # Since the revision author is not known, the revisions do not at this
        # stage need karma allocated.
        self.assertEqual(
            [], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))
        # The person registers with Launchpad.
        author = self.factory.makePerson(email=email)
        # Now the kama needs allocating.
        self.assertEqual(
            [rev], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

    def test_karmaDateForFutureRevisions(self):
        # If the revision date is some time in the future, then the karma date
        # is set to be the time that the revision was created.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email,
            revision_date=datetime.now(pytz.UTC) + timedelta(days=5))
        branch = self.factory.makeProductBranch()
        branch.createBranchRevision(1, rev)
        # Get the karma event.
        [karma] = list(Store.of(author).find(
            Karma,
            Karma.person == author,
            Karma.product == branch.product))
        self.assertEqual(karma.datecreated, rev.date_created)


class TestRevisionGetBranch(TestCaseWithFactory):
    """Test the `getBranch` method of the revision."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "admin@canonical.com")
        self.author = self.factory.makePerson()
        self.revision = self.factory.makeRevision(
            author=self.author.preferredemail.email)

    def makeBranchWithRevision(self, sequence, **kwargs):
        branch = self.factory.makeAnyBranch(**kwargs)
        branch.createBranchRevision(sequence, self.revision)
        return branch

    def testPreferAuthorBranch(self):
        # If a revision is on the mainline history of two (or more) different
        # branches, then choose one owned by the revision author.
        self.makeBranchWithRevision(1)
        b = self.makeBranchWithRevision(1, owner=self.author)
        self.assertEqual(b, self.revision.getBranch())

    def testPreferMainlineRevisionBranch(self):
        # Choose a branch where the revision is on the mainline history over a
        # branch where the revision is just in the ancestry.
        self.makeBranchWithRevision(None)
        b = self.makeBranchWithRevision(1)
        self.assertEqual(b, self.revision.getBranch())

    def testOwnerTrunksMainline(self):
        # If the revision is mainline on a branch not owned by the revision
        # owner, but in the ancestry of a branch owned by the revision owner,
        # choose the branch owned by the revision author.
        self.makeBranchWithRevision(1)
        b = self.makeBranchWithRevision(None, owner=self.author)
        self.assertEqual(b, self.revision.getBranch())

    def testPublicBranchTrumpsOwner(self):
        # Only public branches are returned.
        b1 = self.makeBranchWithRevision(1)
        b2 = self.makeBranchWithRevision(1, owner=self.author)
        b2.private = True
        self.assertEqual(b1, self.revision.getBranch())

    def testAllowPrivateReturnsPrivateBranch(self):
        # If the allow_private flag is set, then private branches can be
        # returned if they are the best match.
        b1 = self.makeBranchWithRevision(1)
        b2 = self.makeBranchWithRevision(1, owner=self.author)
        b2.private = True
        self.assertEqual(b2, self.revision.getBranch(allow_private=True))

    def testAllowPrivateCanReturnPublic(self):
        # Allowing private branches does not change the priority ordering of
        # the branches.
        b1 = self.makeBranchWithRevision(1)
        b2 = self.makeBranchWithRevision(1, owner=self.author)
        b1.private = True
        self.assertEqual(b2, self.revision.getBranch(allow_private=True))

    def testGetBranchNotJunk(self):
        # If allow_junk is set to False, then branches without products are
        # not returned.
        b1 = self.factory.makeProductBranch()
        b1.createBranchRevision(1, self.revision)
        b2 = self.factory.makePersonalBranch(owner=self.author)
        b2.createBranchRevision(1, self.revision)
        self.assertEqual(
            b1, self.revision.getBranch(allow_private=True, allow_junk=False))


class GetPublicRevisionsTestCase(TestCaseWithFactory):
    """A base class for the tests for people, products and projects."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "admin@canonical.com")
        # Since the tests order by date, but also limit to the last 30
        # days, we want a time counter that starts 10 days ago.
        self.date_generator = time_counter(
            datetime.now(pytz.UTC) - timedelta(days=10),
            delta=timedelta(days=1))

    def _makeRevision(self, revision_date=None):
        """Make a revision using the date generator."""
        if revision_date is None:
            revision_date = self.date_generator.next()
        return self.factory.makeRevision(
            revision_date=revision_date)

    def _addRevisionsToBranch(self, branch, *revs):
        # Add the revisions to the branch.
        for sequence, rev in enumerate(revs):
            branch.createBranchRevision(sequence, rev)

    def _makeBranch(self, product=None):
        # Make a branch.
        if product is None:
            # If the test defines a product, use that, otherwise
            # have the factory generate one.
            product = getattr(self, 'product', None)
        return self.factory.makeProductBranch(product=product)

    def _makeRevisionInBranch(self, product=None):
        # Make a revision, and associate it with a branch.  The branch is made
        # with the product passed in, which means that if there was no product
        # passed in, the factory makes a new one.
        branch = self.factory.makeProductBranch(product=product)
        rev = self._makeRevision()
        branch.createBranchRevision(1, rev)
        return rev

    def _getRevisions(self, day_limit=30):
        raise NotImplementedError('_getRevisions')


class RevisionTestMixin:
    """Common tests for the different GetPublicRevision test cases."""

    def testNewestRevisionFirst(self):
        # The revisions are ordered with the newest first.
        rev1 = self._makeRevision()
        rev2 = self._makeRevision()
        rev3 = self._makeRevision()
        self._addRevisionsToBranch(self._makeBranch(), rev1, rev2, rev3)
        self.assertEqual([rev3, rev2, rev1], self._getRevisions())

    def testRevisionsOnlyReturnedOnce(self):
        # If the revisions appear in multiple branches, they are only returned
        # once.
        rev1 = self._makeRevision()
        rev2 = self._makeRevision()
        rev3 = self._makeRevision()
        self._addRevisionsToBranch(
            self._makeBranch(), rev1, rev2, rev3)
        self._addRevisionsToBranch(
            self._makeBranch(), rev1, rev2, rev3)
        self.assertEqual([rev3, rev2, rev1], self._getRevisions())

    def testRevisionsMustBeInABranch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        rev1 = self._makeRevision()
        self.assertEqual([], self._getRevisions())
        b = self._makeBranch()
        b.createBranchRevision(1, rev1)
        self.assertEqual([rev1], self._getRevisions())

    def testRevisionsMustBeInAPublicBranch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        rev1 = self._makeRevision()
        b = self._makeBranch()
        b.createBranchRevision(1, rev1)
        b.private = True
        self.assertEqual([], self._getRevisions())

    def testRevisionDateRange(self):
        # Revisions where the revision_date is older than the day_limit, or
        # some time in the future are not returned.
        now = datetime.now(pytz.UTC)
        day_limit = 5
        # Make the first revision earlier than our day limit.
        rev1 = self._makeRevision(
            revision_date=(now - timedelta(days=(day_limit + 2))))
        # The second one is just two days ago.
        rev2 = self._makeRevision(
            revision_date=(now - timedelta(days=2)))
        # The third is in the future
        rev3 = self._makeRevision(
            revision_date=(now + timedelta(days=2)))
        self._addRevisionsToBranch(self._makeBranch(), rev1, rev2, rev3)
        self.assertEqual([rev2],  self._getRevisions(day_limit))


class TestGetPublicRevisionsForPerson(GetPublicRevisionsTestCase,
                                      RevisionTestMixin):
    """Test the `getPublicRevisionsForPerson` method of `RevisionSet`."""

    def setUp(self):
        GetPublicRevisionsTestCase.setUp(self)
        self.author = self.factory.makePerson()
        self.revision = self.factory.makeRevision(
            author=self.author.preferredemail.email)

    def _getRevisions(self, day_limit=30):
        # Returns the revisions for the person.
        return list(RevisionSet.getPublicRevisionsForPerson(
                self.author, day_limit))

    def _makeRevision(self, author=None, revision_date=None):
        """Make a revision owned by `author`.

        `author` defaults to self.author if not set."""
        if revision_date is None:
            revision_date = self.date_generator.next()
        if author is None:
            author = self.author
        return self.factory.makeRevision(
            author=author.preferredemail.email,
            revision_date=revision_date)

    def testTeamRevisions(self):
        # Revisions owned by all members of a team are returned.
        team = self.factory.makeTeam(self.author)
        team_member = self.factory.makePerson()
        team.addMember(team_member, self.author)
        rev1 = self._makeRevision()
        rev2 = self._makeRevision(team_member)
        rev3 = self._makeRevision(self.factory.makePerson())
        branch = self.factory.makeAnyBranch()
        self._addRevisionsToBranch(branch, rev1, rev2, rev3)
        self.assertEqual([rev2, rev1],
                         list(RevisionSet.getPublicRevisionsForPerson(team)))


class TestGetPublicRevisionsForProduct(GetPublicRevisionsTestCase,
                                       RevisionTestMixin):
    """Test the `getPublicRevisionsForProduct` method of `RevisionSet`."""

    def setUp(self):
        GetPublicRevisionsTestCase.setUp(self)
        self.product = self.factory.makeProduct()

    def _getRevisions(self, day_limit=30):
        # Returns the revisions for the person.
        return list(RevisionSet.getPublicRevisionsForProduct(
                self.product, day_limit))

    def testRevisionsMustBeInABranchOfProduct(self):
        # The revision must be in a branch for the product.
        # returned.
        rev1 = self._makeRevisionInBranch(product=self.product)
        rev2 = self._makeRevisionInBranch()
        self.assertEqual([rev1], self._getRevisions())


class TestGetPublicRevisionsForProject(GetPublicRevisionsTestCase,
                                       RevisionTestMixin):
    """Test the `getPublicRevisionsForProject` method of `RevisionSet`."""

    def setUp(self):
        GetPublicRevisionsTestCase.setUp(self)
        self.project = self.factory.makeProject()
        self.product = self.factory.makeProduct(project=self.project)

    def _getRevisions(self, day_limit=30):
        # Returns the revisions for the person.
        return list(RevisionSet.getPublicRevisionsForProject(
                self.project, day_limit))

    def testRevisionsMustBeInABranchOfProduct(self):
        # The revision must be in a branch for the product.
        # returned.
        rev1 = self._makeRevisionInBranch(product=self.product)
        rev2 = self._makeRevisionInBranch()
        self.assertEqual([rev1], self._getRevisions())

    def testProjectRevisions(self):
        # Revisions in all products that are part of the project are returned.
        another_product = self.factory.makeProduct(project=self.project)
        rev1 = self._makeRevisionInBranch(product=self.product)
        rev2 = self._makeRevisionInBranch(product=another_product)
        rev3 = self._makeRevisionInBranch()
        self.assertEqual([rev2, rev1], self._getRevisions())


class TestGetRecentRevisionsForProduct(GetPublicRevisionsTestCase):
    """Test the `getRecentRevisionsForProduct` method of `RevisionSet`."""

    def setUp(self):
        GetPublicRevisionsTestCase.setUp(self)
        self.product = self.factory.makeProduct()

    def _getRecentRevisions(self, day_limit=30):
        # Return a list of the recent revisions and revision authors.
        return list(RevisionSet.getRecentRevisionsForProduct(
                self.product, day_limit))

    def testRevisionAuthorMatchesRevision(self):
        # The revision author returned with the revision is the same as the
        # author for the revision.
        rev1 = self._makeRevisionInBranch(product=self.product)
        results = self._getRecentRevisions()
        self.assertEqual(1, len(results))
        revision, revision_author = results[0]
        self.assertEqual(revision.revision_author, revision_author)

    def testRevisionsMustBeInABranchOfProduct(self):
        # The revisions returned revision must be in a branch for the product.
        rev1 = self._makeRevisionInBranch(product=self.product)
        rev2 = self._makeRevisionInBranch()
        self.assertEqual([(rev1, rev1.revision_author)],
                         self._getRecentRevisions())

    def testRevisionDateRange(self):
        # Revisions where the revision_date is older than the day_limit, or
        # some time in the future are not returned.
        now = datetime.now(pytz.UTC)
        day_limit = 5
        # Make the first revision earlier than our day limit.
        rev1 = self._makeRevision(
            revision_date=(now - timedelta(days=(day_limit + 2))))
        # The second one is just two days ago.
        rev2 = self._makeRevision(revision_date=(now - timedelta(days=2)))
        # The third is in the future
        rev3 = self._makeRevision(revision_date=(now + timedelta(days=2)))
        self._addRevisionsToBranch(self._makeBranch(), rev1, rev2, rev3)
        self.assertEqual([(rev2, rev2.revision_author)],
                         self._getRecentRevisions(day_limit))


class TestTipRevisionsForBranches(TestCase):
    """Test that the tip revisions get returned properly."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('test@canonical.com')

        factory = LaunchpadObjectFactory()
        branches = [factory.makeAnyBranch() for count in range(5)]
        branch_ids = [branch.id for branch in branches]
        for branch in branches:
            factory.makeRevisionsForBranch(branch)
        # Retrieve the updated branches (due to transaction boundaries).
        branch_set = getUtility(IBranchLookup)
        self.branches = [branch_set.get(id) for id in branch_ids]
        self.revision_set = getUtility(IRevisionSet)

    def tearDown(self):
        logout()

    def _breakTransaction(self):
        # make sure the current transaction can not be committed by
        # sending a broken SQL statement to the database
        try:
            cursor().execute('break this transaction')
        except psycopg2.DatabaseError:
            pass

    def testNoBranches(self):
        """Assert that when given an empty list, an empty list is returned."""
        bs = self.revision_set
        revisions = bs.getTipRevisionsForBranches([])
        self.assertTrue(revisions is None)

    def testOneBranches(self):
        """When given one branch, one branch revision is returned."""
        revisions = list(
            self.revision_set.getTipRevisionsForBranches(
                self.branches[:1]))
        # XXX jamesh 2008-06-02: ensure that branch[0] is loaded
        last_scanned_id = self.branches[0].last_scanned_id
        self._breakTransaction()
        self.assertEqual(1, len(revisions))
        revision = revisions[0]
        self.assertEqual(self.branches[0].last_scanned_id,
                         revision.revision_id)
        # By accessing to the revision_author we can confirm that the
        # revision author has in fact been retrieved already.
        revision_author = revision.revision_author
        self.assertTrue(revision_author is not None)

    def testManyBranches(self):
        """Assert multiple branch revisions are returned correctly."""
        revisions = list(
            self.revision_set.getTipRevisionsForBranches(
                self.branches))
        self._breakTransaction()
        self.assertEqual(5, len(revisions))
        for revision in revisions:
            # By accessing to the revision_author we can confirm that the
            # revision author has in fact been retrieved already.
            revision_author = revision.revision_author
            self.assertTrue(revision_author is not None)

    def test_timestampToDatetime_with_negative_fractional(self):
        # timestampToDatetime should convert a negative, fractional timestamp
        # into a valid, sane datetime object.
        revision_set = removeSecurityProxy(getUtility(IRevisionSet))
        UTC = pytz.timezone('UTC')
        timestamp = -0.5
        date = revision_set._timestampToDatetime(timestamp)
        self.assertEqual(
            date, datetime(1969, 12, 31, 23, 59, 59, 500000, UTC))

    def test_timestampToDatetime(self):
        # timestampTODatetime should convert a regular timestamp into a valid,
        # sane datetime object.
        revision_set = removeSecurityProxy(getUtility(IRevisionSet))
        UTC = pytz.timezone('UTC')
        timestamp = time.time()
        date = datetime.fromtimestamp(timestamp, tz=UTC)
        self.assertEqual(date, revision_set._timestampToDatetime(timestamp))


class TestOnlyPresent(TestCaseWithFactory):
    """Tests for `RevisionSet.onlyPresent`.

    Note that although onlyPresent returns a set, it is a security proxied
    set, so we have to convert it to a real set before doing any comparisons.
    """

    layer = DatabaseFunctionalLayer

    def test_empty(self):
        # onlyPresent returns no results when passed no revids.
        self.assertEqual(
            set(),
            set(getUtility(IRevisionSet).onlyPresent([])))

    def test_none_present(self):
        # onlyPresent returns no results when passed a revid not present in
        # the database.
        not_present = self.factory.getUniqueString()
        self.assertEqual(
            set(),
            set(getUtility(IRevisionSet).onlyPresent([not_present])))

    def test_one_present(self):
        # onlyPresent returns a revid that is present in the database.
        present = self.factory.makeRevision().revision_id
        self.assertEqual(
            set([present]),
            set(getUtility(IRevisionSet).onlyPresent([present])))

    def test_some_present(self):
        # onlyPresent returns only the revid that is present in the database.
        not_present = self.factory.getUniqueString()
        present = self.factory.makeRevision().revision_id
        self.assertEqual(
            set([present]),
            set(getUtility(IRevisionSet).onlyPresent([present, not_present])))

    def test_call_twice_in_one_transaction(self):
        # onlyPresent creates temporary tables, but cleans after itself so
        # that it can safely be called twice in one transaction.
        not_present = self.factory.getUniqueString()
        getUtility(IRevisionSet).onlyPresent([not_present])
        # This is just "assertNotRaises"
        getUtility(IRevisionSet).onlyPresent([not_present])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
