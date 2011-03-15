# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTasks."""

__metaclass__ = type

from testtools.matchers import Equals

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import filter_bugtasks_by_context
from lp.testing import TestCaseWithFactory


class TestFilterBugTasksByContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_simple_case(self):
        bug = self.factory.makeBug()
        tasks = list(bug.bugtasks)
        self.assertEqual(
            filter_bugtasks_by_context(None, tasks),
            Equals(tasks))
