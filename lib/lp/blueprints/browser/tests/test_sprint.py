# Copyright 2011-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Sprint pages and views."""

__metaclass__ = type

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
from testtools.matchers import Equals
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    RequestTimelineCollector,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import (
    BrowsesWithQueryLimit,
    HasQueryCount,
    )


class TestSprintIndex(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_query_count(self):
        sprint = self.factory.makeSprint()
        with person_logged_in(sprint.owner):
            for x in range(30):
                sprint.attend(
                    self.factory.makePerson(),
                    sprint.time_starts, sprint.time_ends, True)
        self.assertThat(sprint, BrowsesWithQueryLimit(21, sprint.owner))

    def test_blueprint_listing_query_count(self):
        """Set a maximum number of queries for sprint blueprint lists."""
        sprint = self.factory.makeSprint()
        for count in range(10):
            blueprint = self.factory.makeSpecification()
            link = blueprint.linkSprint(sprint, blueprint.owner)
            link.acceptBy(sprint.owner)
        with RequestTimelineCollector() as recorder:
            self.getViewBrowser(sprint)
        self.assertThat(recorder, HasQueryCount(Equals(30)))

    def test_proprietary_blueprint_listing_query_count(self):
        """Set a maximum number of queries for sprint blueprint lists."""
        sprint = self.factory.makeSprint()
        for count in range(10):
            blueprint = self.factory.makeSpecification(
                information_type=InformationType.PROPRIETARY)
            owner = removeSecurityProxy(blueprint).owner
            link = removeSecurityProxy(blueprint).linkSprint(sprint, owner)
            link.acceptBy(sprint.owner)
        with RequestTimelineCollector() as recorder:
            self.getViewBrowser(sprint)
        self.assertThat(recorder, HasQueryCount(Equals(22)))


class TestSprintDeleteView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def makePopulatedSprint(self):
        sprint = self.factory.makeSprint()
        with person_logged_in(sprint.owner):
            sprint.attend(
                self.factory.makePerson(),
                sprint.time_starts, sprint.time_ends, True)
        blueprint = self.factory.makeSpecification()
        blueprint.linkSprint(sprint, blueprint.owner).acceptBy(sprint.owner)
        return sprint

    def test_unauthorized(self):
        # A user without edit access cannot delete a sprint.
        self.useFixture(FakeLogger())
        sprint = self.makePopulatedSprint()
        sprint_url = canonical_url(sprint)
        other_person = self.factory.makePerson()
        browser = self.getViewBrowser(sprint, user=other_person)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Delete sprint")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, sprint_url + "/+delete",
            user=other_person)

    def test_delete_sprint_owner(self):
        # A sprint can be deleted by its owner, even if it has attendees and
        # specifications.
        self.useFixture(FakeLogger())
        sprint = self.makePopulatedSprint()
        sprint_url = canonical_url(sprint)
        owner_url = canonical_url(sprint.owner)
        browser = self.getViewBrowser(sprint, user=sprint.owner)
        browser.getLink("Delete sprint").click()
        browser.getControl("Delete sprint").click()
        self.assertEqual(owner_url, browser.url)
        self.assertRaises(NotFound, browser.open, sprint_url)

    def test_delete_sprint_registry(self):
        # A sprint can be deleted by a registry expert, even if it has
        # attendees and specifications.
        self.useFixture(FakeLogger())
        sprint = self.makePopulatedSprint()
        sprint_url = canonical_url(sprint)
        owner_url = canonical_url(sprint.owner)
        browser = self.getViewBrowser(
            sprint, user=self.factory.makeRegistryExpert())
        browser.getLink("Delete sprint").click()
        browser.getControl("Delete sprint").click()
        self.assertEqual(owner_url, browser.url)
        self.assertRaises(NotFound, browser.open, sprint_url)
