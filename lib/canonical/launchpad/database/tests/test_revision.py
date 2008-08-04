# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for Revisions."""

__metaclass__ = type

from datetime import datetime, timedelta
from unittest import TestCase, TestLoader

import psycopg2
import pytz
import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.launchpad.database.revision import RevisionSet
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import (
    IBranchSet, IRevisionSet)
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory, time_counter)
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer


class TestRevisionKarma(TestCaseWithFactory):
    """Test the `getBranch` method of the revision."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "foo.bar@canonical.com")

    def test_revisionWithUnknownEmail(self):
        # A revision when created does not have karma allocated.
        rev = self.factory.makeRevision()
        self.assertEqual(False, rev.karma_allocated)
        # Even if the revision author is someone we know.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        self.assertEqual(False, rev.karma_allocated)

    def test_noKarmaForUnknownAuthor(self):
        # If the revision author is unknown, karam isn't allocated.
        rev = self.factory.makeRevision()
        branch = self.factory.makeBranch()
        branch.createBranchRevision(1, rev)
        self.assertEqual(False, rev.karma_allocated)

    def test_karmaAllocatedForKnownAuthor(self):
        # If the revision author is known, allocate karma.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        branch = self.factory.makeBranch()
        branch.createBranchRevision(1, rev)
        self.assertEqual(True, rev.karma_allocated)
        [karma] = list(author.latestKarma(1))
        self.assertEqual(karma.datecreated, rev.revision_date)
        self.assertEqual(karma.product, branch.product)

    def test_checkNewVerifiedEmailClaimsRevisionKarma(self):
        # Revisions that exist already, but without allocated karma will get
        # karma events created when we work out who the Launchpad person is.
        email = self.factory.getUniqueEmailAddress()
        rev = self.factory.makeRevision(author=email)
        branch = self.factory.makeBranch()
        branch.createBranchRevision(1, rev)
        self.assertEqual(False, rev.karma_allocated)
        author = self.factory.makePerson(email=email)

        RevisionSet().checkNewVerifiedEmail(author.preferredemail)

        self.assertEqual(True, rev.karma_allocated)
        [karma] = list(author.latestKarma(1))
        self.assertEqual(karma.datecreated, rev.revision_date)
        self.assertEqual(karma.product, branch.product)


class TestRevisionGetBranch(TestCaseWithFactory):
    """Test the `getBranch` method of the revision."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "foo.bar@canonical.com")
        self.author = self.factory.makePerson()
        self.revision = self.factory.makeRevision(
            author=self.author.preferredemail.email)

    def testPreferAuthorBranch(self):
        # If a revision is on the mainline history of two (or more) different
        # branches, then choose one owned by the revision author.
        b1 = self.factory.makeBranch()
        b1.createBranchRevision(1, self.revision)
        b2 = self.factory.makeBranch(owner=self.author)
        b2.createBranchRevision(1, self.revision)
        self.assertEqual(b2, self.revision.getBranch())

    def testPreferMainlineRevisionBranch(self):
        # Choose a branch where the revision is on the mainline history over a
        # branch where the revision is just in the ancestry.
        b1 = self.factory.makeBranch()
        b1.createBranchRevision(None, self.revision)
        b2 = self.factory.makeBranch()
        b2.createBranchRevision(1, self.revision)
        self.assertEqual(b2, self.revision.getBranch())

    def testOwnerTrunksMainline(self):
        # If the revision is mainline on a branch not owned by the revision
        # owner, but in the ancestry of a branch owned by the revision owner,
        # choose the branch owned by the revision author.
        b1 = self.factory.makeBranch()
        b1.createBranchRevision(1, self.revision)
        b2 = self.factory.makeBranch(owner=self.author)
        b2.createBranchRevision(None, self.revision)
        self.assertEqual(b2, self.revision.getBranch())

    def testPublicBranchTrumpsOwner(self):
        # Only public branches are returned.
        b1 = self.factory.makeBranch()
        b1.createBranchRevision(1, self.revision)
        b2 = self.factory.makeBranch(owner=self.author)
        b2.createBranchRevision(1, self.revision)
        b2.private = True
        self.assertEqual(b1, self.revision.getBranch())
        # Private branches can be returned if explicitly asked for.
        self.assertEqual(b2, self.revision.getBranch(allow_private=True))

    def testEarlierHistoryFirst(self):
        # If all else is equal, choose the branch that has the revision
        # earlier in the mainline history.
        b1 = self.factory.makeBranch()
        b1.createBranchRevision(2, self.revision)
        b2 = self.factory.makeBranch()
        b2.createBranchRevision(1, self.revision)
        self.assertEqual(b2, self.revision.getBranch())


class TestGetPublicRevisonsForPerson(TestCaseWithFactory):
    """Test the `getPublicRevisionsForPerson` method of `RevisionSet`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "foo.bar@canonical.com")
        self.author = self.factory.makePerson()
        self.revision = self.factory.makeRevision(
            author=self.author.preferredemail.email)
        self.date_generator = time_counter(
            datetime(2007, 1, 1, tzinfo=pytz.UTC),
            delta=timedelta(days=1))

    def _makeRevision(self, author=None):
        """Make a revision owned by self.author."""
        if author is None:
            author = self.author
        return self.factory.makeRevision(
            author=author.preferredemail.email,
            revision_date=self.date_generator.next())

    def _addRevisionsToBranch(self, branch, *revs):
        # Add the revisions to the the branch.
        for sequence, rev in enumerate(revs):
            branch.createBranchRevision(sequence, rev)

    def testRevisionsMustBeInABranch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        rev1 = self._makeRevision()
        self.assertEqual(self.author, rev1.revision_author.person)
        self.assertEqual(
            [],
            list(RevisionSet.getPublicRevisionsForPerson(self.author)))
        b = self.factory.makeBranch()
        b.createBranchRevision(1, rev1)
        self.assertEqual(
            [rev1],
            list(RevisionSet.getPublicRevisionsForPerson(self.author)))

    def testRevisionsMustBeInAPublicBranch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        rev1 = self._makeRevision()
        self.assertEqual(self.author, rev1.revision_author.person)
        self.assertEqual(
            [],
            list(RevisionSet.getPublicRevisionsForPerson(self.author)))
        b = self.factory.makeBranch()
        b.createBranchRevision(1, rev1)
        b.private = True
        self.assertEqual(
            [],
            list(RevisionSet.getPublicRevisionsForPerson(self.author)))

    def testNewestRevisionFirst(self):
        # The revisions are ordered with the newest first.
        rev1 = self._makeRevision()
        rev2 = self._makeRevision()
        rev3 = self._makeRevision()
        branch = self.factory.makeBranch()
        self._addRevisionsToBranch(branch, rev1, rev2, rev3)
        self.assertEqual(
            [rev3, rev2, rev1],
            list(RevisionSet.getPublicRevisionsForPerson(self.author)))

    def testTeamRevisions(self):
        # Revisions owned by all members of a team are returnded.
        team = self.factory.makeTeam(self.author)
        team_member = self.factory.makePerson()
        team.addMember(team_member, self.author)
        rev1 = self._makeRevision()
        rev2 = self._makeRevision(team_member)
        rev3 = self._makeRevision(self.factory.makePerson())
        branch = self.factory.makeBranch()
        self._addRevisionsToBranch(branch, rev1, rev2, rev3)
        self.assertEqual(
            [rev2, rev1],
            list(RevisionSet.getPublicRevisionsForPerson(team)))


class TestTipRevisionsForBranches(TestCase):
    """Test that the tip revisions get returned properly."""

    # The LaunchpadZopelessLayer is used as the setUp needs to
    # switch database users in order to create revisions for the
    # test branches.
    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('test@canonical.com')

        factory = LaunchpadObjectFactory()
        branches = [factory.makeBranch() for count in range(5)]
        branch_ids = [branch.id for branch in branches]
        transaction.commit()
        launchpad_dbuser = config.launchpad.dbuser
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        for branch in branches:
            factory.makeRevisionsForBranch(branch)
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(launchpad_dbuser)
        # Retrieve the updated branches (due to transaction boundaries).
        branch_set = getUtility(IBranchSet)
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
        self.branches[0].last_scanned_id
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


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
