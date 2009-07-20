# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the revision feeds."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.feed.branch import RevisionListingFeed
from lp.code.interfaces.revision import IRevisionSet
from lp.testing import login_person, TestCaseWithFactory


class TestRevisionFeed(TestCaseWithFactory):
    """Tests for the methods of the RevisionListingFeed base class."""

    layer = DatabaseFunctionalLayer

    def _createBranchWithRevision(self):
        """Create a branch with a linked, cached revision.

        :return: a tuple of (branch, revision)
        """
        revision = self.factory.makeRevision()
        branch = self.factory.makeBranch()
        branch.createBranchRevision(1, revision)
        getUtility(IRevisionSet).updateRevisionCacheForBranch(branch)
        return branch, revision

    def _createFeed(self):
        """Create and return a RevisionListingFeed instance."""
        # The FeedBase class determins the feed type by the end of the
        # requested URL, so forcing .atom here.
        return RevisionListingFeed(
            None, LaunchpadTestRequest(
                SERVER_URL="http://example.com/fake.atom"))

    def test_createView(self):
        # Revisions that are linked to branches are shown in the feed.

        # Since we are calling into a base class that would normally take a
        # context and a request, we need to give it something - None should be
        # fine.
        branch, revision = self._createBranchWithRevision()
        revision_feed = self._createFeed()
        view = revision_feed._createView(revision)
        self.assertEqual(revision, view.context)
        self.assertEqual(branch, view.branch)

    def test_createView_revision_not_in_branch(self):
        # If a revision is in the RevisionCache table, but no longer
        # associated with a public branch, then the createView call will
        # return None to indicate not do show this revision.
        branch, revision = self._createBranchWithRevision()
        # Now delete the branch.
        login_person(branch.owner)
        branch.destroySelf()
        revision_feed = self._createFeed()
        view = revision_feed._createView(revision)
        self.assertIs(None, view)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
