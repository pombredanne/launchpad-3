# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package listings."""

__metaclass__ = type

import soupmatchers
from testtools.matchers import Not

from lp.code.tests.helpers import GitHostingFixture
from lp.services.database.constants import (
    ONE_DAY_AGO,
    SEVEN_DAYS_AGO,
    UTC_NOW,
    )
from lp.services.webapp import canonical_url
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    person_logged_in,
    record_two_runs,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestSnapListing(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def assertSnapsLink(self, context, link_text, link_has_context=False,
                        **kwargs):
        if link_has_context:
            expected_href = canonical_url(context, view_name="+snaps")
        else:
            expected_href = "+snaps"
        matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "View snap packages link", "a", text=link_text,
                attrs={"href": expected_href}))
        self.assertThat(self.getViewBrowser(context).contents, Not(matcher))
        login(ANONYMOUS)
        self.factory.makeSnap(**kwargs)
        self.factory.makeSnap(**kwargs)
        self.assertThat(self.getViewBrowser(context).contents, matcher)

    def test_branch_links_to_snaps(self):
        branch = self.factory.makeAnyBranch()
        self.assertSnapsLink(branch, "2 snap packages", branch=branch)

    def test_git_repository_links_to_snaps(self):
        repository = self.factory.makeGitRepository()
        [ref] = self.factory.makeGitRefs(repository=repository)
        self.assertSnapsLink(repository, "2 snap packages", git_ref=ref)

    def test_git_ref_links_to_snaps(self):
        self.useFixture(GitHostingFixture())
        [ref] = self.factory.makeGitRefs()
        self.assertSnapsLink(ref, "2 snap packages", git_ref=ref)

    def test_person_links_to_snaps(self):
        person = self.factory.makePerson()
        self.assertSnapsLink(
            person, "View snap packages", link_has_context=True,
            registrant=person, owner=person)

    def test_project_links_to_snaps(self):
        project = self.factory.makeProduct()
        [ref] = self.factory.makeGitRefs(target=project)
        self.assertSnapsLink(
            project, "View snap packages", link_has_context=True, git_ref=ref)

    def test_branch_snap_listing(self):
        # We can see snap packages for a Bazaar branch.
        branch = self.factory.makeAnyBranch()
        self.factory.makeSnap(branch=branch)
        text = self.getMainText(branch, "+snaps")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Snap packages for lp:.*
            Name            Owner           Registered
            snap-name.*     Team Name.*     .*""", text)

    def test_git_repository_snap_listing(self):
        # We can see snap packages for a Git repository.
        repository = self.factory.makeGitRepository()
        [ref] = self.factory.makeGitRefs(repository=repository)
        self.factory.makeSnap(git_ref=ref)
        text = self.getMainText(repository, "+snaps")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Snap packages for lp:~.*
            Name            Owner           Registered
            snap-name.*     Team Name.*     .*""", text)

    def test_git_ref_snap_listing(self):
        # We can see snap packages for a Git reference.
        [ref] = self.factory.makeGitRefs()
        self.factory.makeSnap(git_ref=ref)
        text = self.getMainText(ref, "+snaps")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Snap packages for ~.*:.*
            Name            Owner           Registered
            snap-name.*     Team Name.*     .*""", text)

    def test_person_snap_listing(self):
        # We can see snap packages for a person.
        owner = self.factory.makePerson(displayname="Snap Owner")
        self.factory.makeSnap(
            registrant=owner, owner=owner, branch=self.factory.makeAnyBranch(),
            date_created=SEVEN_DAYS_AGO)
        [ref] = self.factory.makeGitRefs()
        self.factory.makeSnap(
            registrant=owner, owner=owner, git_ref=ref,
            date_created=ONE_DAY_AGO)
        remote_ref = self.factory.makeGitRefRemote()
        self.factory.makeSnap(
            registrant=owner, owner=owner, git_ref=remote_ref,
            date_created=UTC_NOW)
        text = self.getMainText(owner, "+snaps")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Snap packages for Snap Owner
            Name            Source                  Registered
            snap-name.*     http://.* path-.*       .*
            snap-name.*     ~.*:.*                  .*
            snap-name.*     lp:.*                   .*""", text)

    def test_project_snap_listing(self):
        # We can see snap packages for a project.
        project = self.factory.makeProduct(displayname="Snappable")
        self.factory.makeSnap(
            branch=self.factory.makeProductBranch(product=project),
            date_created=ONE_DAY_AGO)
        [ref] = self.factory.makeGitRefs(target=project)
        self.factory.makeSnap(git_ref=ref, date_created=UTC_NOW)
        text = self.getMainText(project, "+snaps")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Snap packages for Snappable
            Name            Owner           Source          Registered
            snap-name.*     Team Name.*     ~.*:.*          .*
            snap-name.*     Team Name.*     lp:.*           .*""", text)

    def assertSnapsQueryCount(self, context, item_creator):
        recorder1, recorder2 = record_two_runs(
            lambda: self.getMainText(context, "+snaps"), item_creator, 5)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_branch_query_count(self):
        # The number of queries required to render the list of all snap
        # packages for a Bazaar branch is constant in the number of owners
        # and snap packages.
        person = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(owner=person)

        def create_snap():
            with person_logged_in(person):
                self.factory.makeSnap(branch=branch)

        self.assertSnapsQueryCount(branch, create_snap)

    def test_git_repository_query_count(self):
        # The number of queries required to render the list of all snap
        # packages for a Git repository is constant in the number of owners
        # and snap packages.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)

        def create_snap():
            with person_logged_in(person):
                [ref] = self.factory.makeGitRefs(repository=repository)
                self.factory.makeSnap(git_ref=ref)

        self.assertSnapsQueryCount(repository, create_snap)

    def test_git_ref_query_count(self):
        # The number of queries required to render the list of all snap
        # packages for a Git reference is constant in the number of owners
        # and snap packages.
        person = self.factory.makePerson()
        [ref] = self.factory.makeGitRefs(owner=person)

        def create_snap():
            with person_logged_in(person):
                self.factory.makeSnap(git_ref=ref)

        self.assertSnapsQueryCount(ref, create_snap)

    def test_person_query_count(self):
        # The number of queries required to render the list of all snap
        # packages for a person is constant in the number of projects,
        # sources, and snap packages.
        person = self.factory.makePerson()
        i = 0

        def create_snap():
            with person_logged_in(person):
                project = self.factory.makeProduct()
                if (i % 2) == 0:
                    branch = self.factory.makeProductBranch(
                        owner=person, product=project)
                    self.factory.makeSnap(branch=branch)
                else:
                    [ref] = self.factory.makeGitRefs(
                        owner=person, target=project)
                    self.factory.makeSnap(git_ref=ref)

        self.assertSnapsQueryCount(person, create_snap)

    def test_project_query_count(self):
        # The number of queries required to render the list of all snap
        # packages for a person is constant in the number of owners,
        # sources, and snap packages.
        person = self.factory.makePerson()
        project = self.factory.makeProduct(owner=person)
        i = 0

        def create_snap():
            with person_logged_in(person):
                if (i % 2) == 0:
                    branch = self.factory.makeProductBranch(product=project)
                    self.factory.makeSnap(branch=branch)
                else:
                    [ref] = self.factory.makeGitRefs(target=project)
                    self.factory.makeSnap(git_ref=ref)

        self.assertSnapsQueryCount(project, create_snap)
