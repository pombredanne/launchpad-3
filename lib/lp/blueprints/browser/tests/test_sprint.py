# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Sprint pages and views."""

__metaclass__ = type

from storm.locals import Store
from testtools.matchers import LessThan

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.views import create_initialized_view


class TestSprintIndex(TestCaseWithFactory):

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
        view = create_initialized_view(sprint, '+index')
        with StormStatementRecorder() as recorder:
            view.render()
        self.assertThat(recorder, HasQueryCount(LessThan(10)))
