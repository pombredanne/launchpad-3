# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from lp.bugs.interfaces.bugtask import IBugTaskSet
from lp.bugs.model.bugsummary import BugSummary
from lp.bugs.scripts.bugsummaryrebuild import (
    get_bugsummary_targets,
    get_bugtask_targets,
    )
from lp.services.database.lpstorm import IStore
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer


def rollup_journal():
    IStore(BugSummary).execute('SELECT bugsummary_rollup_journal()')


def create_tasks(factory):
    ps = factory.makeProductSeries()
    product = ps.product
    sp = factory.makeSourcePackage(publish=True)

    bug = factory.makeBug(product=product)
    getUtility(IBugTaskSet).createManyTasks(
        bug, bug.owner, [sp, sp.distribution_sourcepackage, ps])

    # There'll be a target for each task, plus a packageless one for
    # each package task.
    expected_targets = [
        (ps.product.id, None, None, None, None),
        (None, ps.id, None, None, None),
        (None, None, sp.distribution.id, None, None),
        (None, None, sp.distribution.id, None, sp.sourcepackagename.id),
        (None, None, None, sp.distroseries.id, None),
        (None, None, None, sp.distroseries.id, sp.sourcepackagename.id)
        ]
    return expected_targets


class TestBugSummaryRebuild(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_get_bugsummary_targets(self):
        # get_bugsummary_targets returns the set of target tuples that are
        # currently represented in BugSummary.
        orig_targets = get_bugsummary_targets()
        expected_targets = create_tasks(self.factory)
        rollup_journal()
        new_targets = get_bugsummary_targets()
        self.assertContentEqual(expected_targets, new_targets - orig_targets)

    def test_get_bugtask_targets(self):
        # get_bugtask_targets returns the set of target tuples that are
        # currently represented in BugTask.
        orig_targets = get_bugtask_targets()
        expected_targets = create_tasks(self.factory)
        new_targets = get_bugtask_targets()
        self.assertContentEqual(expected_targets, new_targets - orig_targets)
