# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.bugs.interfaces.bugtaskfilter."""

__metaclass__ = type

from storm.locals import Store
from testtools.matchers import Equals

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtaskfilter import filter_bugtasks_by_context
from lp.testing import TestCaseWithFactory


class TestFilterBugTasksByContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_simple_case(self):
        bug = self.factory.makeBug()
        tasks = list(bug.bugtasks)
        self.assertThat(
            filter_bugtasks_by_context(None, tasks),
            Equals(tasks))

    def test_two_product_tasks_case_no_context(self):
        widget = self.factory.makeProduct()
        bug = self.factory.makeBug(product=widget)
        # Make sure the bug and the first task is flushed first.
        Store.of(bug).flush()
        cogs = self.factory.makeProduct()
        self.factory.makeBugTask(bug=bug, target=cogs)
        tasks = list(bug.bugtasks)
        self.assertThat(
            filter_bugtasks_by_context(None, tasks),
            Equals([bug.getBugTask(widget)]))

    def test_two_product_tasks_case(self):
        widget = self.factory.makeProduct()
        bug = self.factory.makeBug(product=widget)
        # Make sure the bug and the first task is flushed first.
        Store.of(bug).flush()
        cogs = self.factory.makeProduct()
        task = self.factory.makeBugTask(bug=bug, target=cogs)
        tasks = list(bug.bugtasks)
        self.assertThat(
            filter_bugtasks_by_context(cogs, tasks),
            Equals([task]))
