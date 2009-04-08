# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the cron script that updates revision karma."""

__metaclass__ = type

from storm.store import Store
import transaction
from unittest import TestLoader

from canonical.config import config
from lp.registry.model.karma import Karma
from canonical.launchpad.database.revision import RevisionSet
from canonical.launchpad.database.emailaddress import EmailAddressSet
from lp.code.scripts.revisionkarma import RevisionKarmaAllocator
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer


class TestRevisionKarma(TestCaseWithFactory):
    """Test the `getBranch` method of the revision."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Use an administrator for the factory
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')

    def assertOneKarmaEvent(self, person, product):
        # Make sure there is one and only one karma event for the person and
        # product.
        result = Store.of(person).find(
            Karma,
            Karma.person == person,
            Karma.product == product)
        self.assertEqual(1, result.count())

    def test_junkBranchMoved(self):
        # When a junk branch is moved to a product, the revision author will
        # get karma on the product.
        author = self.factory.makePerson()
        rev = self.factory.makeRevision(
            author=author.preferredemail.email)
        branch = self.factory.makePersonalBranch()
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
        self.assertOneKarmaEvent(author, branch.product)

    def test_newRevisionAuthor(self):
        # When a user validates an email address that is part of a revision
        # author, and that author has revisions associated with a product, we
        # give the karma to the user.
        email = self.factory.getUniqueEmailAddress()
        rev = self.factory.makeRevision(author=email)
        branch = self.factory.makeAnyBranch()
        branch.createBranchRevision(1, rev)
        transaction.commit()
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
        self.assertOneKarmaEvent(author, branch.product)

    def test_ownerJunkBranchWithAnotherProductBranch(self):
        # If the revision author has the revision in a junk branch but someone
        # else has the revision in the ancestry of a branch associated with a
        # product, then we use the branch with the product rather than the
        # junk branch owned by the revision author.
        author = self.factory.makePerson()
        email = self.factory.getUniqueEmailAddress()
        rev = self.factory.makeRevision(author=email)
        branch = self.factory.makePersonalBranch(owner=author)
        branch.createBranchRevision(1, rev)
        self.failIf(rev.karma_allocated)
        # Now we have a junk branch which has a revision with an email address
        # that is not yet claimed by the author.

        # Now create a non junk branch owned by someone else that has the
        # revision.
        b2 = self.factory.makeProductBranch()
        # Put the author's revision in the ancestry.
        b2.createBranchRevision(None, rev)

        # Now link the revision author to the author.
        author.validateAndEnsurePreferredEmail(
            EmailAddressSet().new(email, author, account=author.account))
        transaction.commit()
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
        self.assertOneKarmaEvent(author, b2.product)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
