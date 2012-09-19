# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Sprint pages and views."""

__metaclass__ = type

from storm.locals import Store

from lp.registry.enums import InformationType
from lp.testing import BrowserTestCase
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import BrowsesWithQueryLimit


class TestSprintIndex(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_query_count(self):
        sprint = self.factory.makeSprint()
        for x in range(30):
            sprint.attend(
                self.factory.makePerson(),
                sprint.time_starts,
                sprint.time_ends,
                True)
        Store.of(sprint).flush()
        Store.of(sprint).invalidate()
        self.assertThat(sprint, BrowsesWithQueryLimit(18, sprint.owner))

    def test_proprietary_blueprint(self):
        sprint = self.factory.makeSprint()
        blueprint = self.factory.makeSpecification(
            information_type=InformationType.PROPRIETARY)
        link = blueprint.linkSprint(sprint, blueprint.owner)
        link.acceptBy(sprint.owner)
        # getViewBrowser should not raise an exception
        self.getViewBrowser(sprint)
