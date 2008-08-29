# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the cron script that updates revision karma."""

__metaclass__ = type

from storm.store import Store
import transaction
from unittest import TestLoader

from canonical.config import config
from canonical.launchpad.database.karma import Karma
from canonical.launchpad.database.revision import RevisionSet
from canonical.launchpad.database.emailaddress import EmailAddressSet
from canonical.launchpad.scripts.revisionkarma import RevisionKarmaAllocator
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer


class TestRevisionKarma(TestCaseWithFactory):
    """Test the `getBranch` method of the revision."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Use an administrator for the factory
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')

    def test_junkBranchMoved(self):
        # When a junk branch is moved to a product, the revision author will
        # get karma on the product.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        branch = self.factory.makeBranch(explicit_junk=True)
        branch.createBranchRevision(1, rev)
        # Once the branch is connected to the revision, we now specify
        # a product for the branch.
        branch.product = self.factory.makeProduct()
        # Commit and switch to the script db user.
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.revisionkarma.dbuser)
        script = RevisionKarmaAllocator(
            'test', config.revisionkarma.dbuser, ['-q'])
        script.main()
        # Get the karma event.
        [karma] = list(Store.of(author).find(
            Karma,
            Karma.person == author,
            Karma.product == branch.product))
        self.assertEqual(karma.datecreated, rev.revision_date)
        self.assertEqual(karma.product, branch.product)

    def test_newRevisionAuthor(self):
        # When a user validates an email address that is part of a revision
        # author, and that author has revisions associated with a product, we
        # give the karma to the user.
        email = self.factory.getUniqueEmailAddress()
        rev = self.factory.makeRevision(author=email)
        branch = self.factory.makeBranch()
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)
        # Since the revision author is not known, the revisions do not at this
        # stage need karma allocated.
        self.assertEqual(
            [], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))
        # The person registers with Launchpad.
        author = self.factory.makePerson(email=email)
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.revisionkarma.dbuser)
        script = RevisionKarmaAllocator(
            'test', config.revisionkarma.dbuser, ['-q'])
        script.main()
        # Get the karma event.
        [karma] = list(Store.of(author).find(
            Karma,
            Karma.person == author,
            Karma.product == branch.product))
        self.assertEqual(karma.datecreated, rev.revision_date)
        self.assertEqual(karma.product, branch.product)

    def test_ownerJunkBranchWithAnotherProductBranch(self):
        # If the revision author has the revision in a junk branch but someone
        # else has the revision in the ancestry of a branch associated with a
        # product, then we use the branch with the product rather than the
        # junk branch owned by the revision author.
        author = self.factory.makePerson()
        email = self.factory.getUniqueEmailAddress()
        rev = self.factory.makeRevision(author=email)
        branch = self.factory.makeBranch(explicit_junk=True, owner=author)
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)
        # Now we have a junk branch which has a revision with an email address
        # that is not yet claimed by the author.

        # Now create a non junk branch owned by someone else that has the
        # revision.
        b2 = self.factory.makeBranch()
        # Put the author's revision in the ancestry.
        b2.createBranchRevision(None, rev)

        # Now link the revision author to the author.
        author.validateAndEnsurePreferredEmail(
            EmailAddressSet().new(email, author))
        # Now that the revision author is linked to the person, the revision
        # needs karma allocated.
        self.assertEqual(
            [rev], list(RevisionSet.getRevisionsNeedingKarmaAllocated()))

        # Commit and switch to the script db user.
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.revisionkarma.dbuser)
        script = RevisionKarmaAllocator(
            'test', config.revisionkarma.dbuser, ['-q'])
        script.main()
        # Get the karma event.
        [karma] = list(Store.of(author).find(
            Karma,
            Karma.person == author,
            Karma.product == b2.product))
        self.assertEqual(karma.datecreated, rev.revision_date)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
