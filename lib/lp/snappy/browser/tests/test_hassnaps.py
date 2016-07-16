# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views for objects that have snap packages."""

__metaclass__ = type

from lp.services.webapp import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class TestRelatedSnapsMixin:

    layer = DatabaseFunctionalLayer

    def test_snaps_link_no_snaps(self):
        # An object with no snap packages does not show a snap packages link.
        context = self.makeContext()
        view = create_initialized_view(context, "+index")
        self.assertEqual(
            "No snap packages using this %s." % self.context_type,
            view.snaps_link)

    def test_snaps_link_one_snap(self):
        # An object with one snap package shows a link to that snap package.
        context = self.makeContext()
        snap = self.makeSnap(context)
        view = create_initialized_view(context, "+index")
        expected_link = (
            '<a href="%s">1 snap package</a> using this %s.' %
            (canonical_url(snap), self.context_type))
        self.assertEqual(expected_link, view.snaps_link)

    def test_snaps_link_more_snaps(self):
        # An object with more than one snap package shows a link to a listing.
        context = self.makeContext()
        self.makeSnap(context)
        self.makeSnap(context)
        view = create_initialized_view(context, "+index")
        expected_link = (
            '<a href="+snaps">2 snap packages</a> using this %s.' %
            self.context_type)
        self.assertEqual(expected_link, view.snaps_link)


class TestRelatedSnapsBranch(TestRelatedSnapsMixin, TestCaseWithFactory):

    context_type = "branch"

    def makeContext(self):
        return self.factory.makeAnyBranch()

    def makeSnap(self, context):
        return self.factory.makeSnap(branch=context)


class TestRelatedSnapsGitRepository(
    TestRelatedSnapsMixin, TestCaseWithFactory):

    context_type = "repository"

    def makeContext(self):
        return self.factory.makeGitRepository()

    def makeSnap(self, context):
        [ref] = self.factory.makeGitRefs(repository=context)
        return self.factory.makeSnap(git_ref=ref)


class TestRelatedSnapsGitRef(TestRelatedSnapsMixin, TestCaseWithFactory):

    context_type = "branch"

    def makeContext(self):
        return self.factory.makeGitRefs()[0]

    def makeSnap(self, context):
        return self.factory.makeSnap(git_ref=context)
