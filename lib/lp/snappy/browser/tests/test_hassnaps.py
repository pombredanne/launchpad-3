# Copyright 2015-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views for objects that have snap packages."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import soupmatchers
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )

from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.tests.helpers import GitHostingFixture
from lp.services.webapp import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


def make_branch(test_case):
    return test_case.factory.makeAnyBranch()


def make_git_repository(test_case):
    return test_case.factory.makeGitRepository()


def make_git_ref(test_case):
    return test_case.factory.makeGitRefs()[0]


class TestHasSnapsView(WithScenarios, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ("Branch", {
            "context_type": "branch",
            "context_factory": make_branch,
            }),
        ("GitRepository", {
            "context_type": "repository",
            "context_factory": make_git_repository,
            }),
        ("GitRef", {
            "context_type": "branch",
            "context_factory": make_git_ref,
            }),
        ]

    def makeSnap(self, context):
        if IBranch.providedBy(context):
            return self.factory.makeSnap(branch=context)
        else:
            if IGitRepository.providedBy(context):
                [context] = self.factory.makeGitRefs(repository=context)
            return self.factory.makeSnap(git_ref=context)

    def test_snaps_link_no_snaps(self):
        # An object with no snap packages does not show a snap packages link.
        context = self.context_factory(self)
        view = create_initialized_view(context, "+index")
        self.assertEqual(
            "No snap packages using this %s." % self.context_type,
            view.snaps_link)

    def test_snaps_link_one_snap(self):
        # An object with one snap package shows a link to that snap package.
        context = self.context_factory(self)
        snap = self.makeSnap(context)
        view = create_initialized_view(context, "+index")
        expected_link = (
            '<a href="%s">1 snap package</a> using this %s.' %
            (canonical_url(snap), self.context_type))
        self.assertEqual(expected_link, view.snaps_link)

    def test_snaps_link_more_snaps(self):
        # An object with more than one snap package shows a link to a listing.
        context = self.context_factory(self)
        self.makeSnap(context)
        self.makeSnap(context)
        view = create_initialized_view(context, "+index")
        expected_link = (
            '<a href="+snaps">2 snap packages</a> using this %s.' %
            self.context_type)
        self.assertEqual(expected_link, view.snaps_link)


class TestHasSnapsMenu(WithScenarios, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    needs_git_hosting_fixture = False

    scenarios = [
        ("Branch", {
            "context_factory": make_branch,
            }),
        ("GitRef", {
            "context_factory": make_git_ref,
            "needs_git_hosting_fixture": True,
            }),
        ]

    def setUp(self):
        super(TestHasSnapsMenu, self).setUp()
        if self.needs_git_hosting_fixture:
            self.useFixture(GitHostingFixture())

    def makeSnap(self, context):
        if IBranch.providedBy(context):
            return self.factory.makeSnap(branch=context)
        else:
            return self.factory.makeSnap(git_ref=context)

    def test_creation_link_no_snaps(self):
        # An object with no snap packages shows a creation link.
        context = self.context_factory(self)
        view = create_initialized_view(context, "+index")
        new_snap_url = canonical_url(context, view_name="+new-snap")
        self.assertThat(view(), soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "creation link", "a", attrs={"href": new_snap_url},
                text="Create snap package")))

    def test_creation_link_snaps(self):
        # An object with snap packages shows a creation link.
        context = self.context_factory(self)
        self.makeSnap(context)
        view = create_initialized_view(context, "+index")
        new_snap_url = canonical_url(context, view_name="+new-snap")
        self.assertThat(view(), soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "creation link", "a", attrs={"href": new_snap_url},
                text="Create snap package")))


load_tests = load_tests_apply_scenarios
