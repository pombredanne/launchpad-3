# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the cron script that updates revision karma."""

__metaclass__ = type

from storm.store import Store
import transaction

from canonical.config import config
from canonical.launchpad.database.emailaddress import EmailAddressSet
from lp.scripts.garbo import RevisionAuthorEmailLinker
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.code.model.revision import RevisionSet
from lp.code.scripts.revisionkarma import RevisionKarmaAllocator
from lp.registry.model.karma import Karma
from lp.services.log.logger import DevNullLogger
from lp.testing import TestCaseWithFactory


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
        project = self.factory.makeProduct()
        branch.setTarget(user=branch.owner, project=project)
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
        # Run the RevisionAuthorEmailLinker garbo job.
        RevisionAuthorEmailLinker(log=DevNullLogger()).run()
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
        # Run the RevisionAuthorEmailLinker garbo job.
        RevisionAuthorEmailLinker(log=DevNullLogger()).run()

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
