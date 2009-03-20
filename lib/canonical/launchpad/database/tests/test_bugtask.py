# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from storm.store import Store

from zope.interface import providedBy
from zope.testing.doctestunit import DocTestSuite

from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.database.bugtask import BugTaskDelta
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.bugtask import (
    BugTaskImportance, BugTaskStatus, IBugTaskDelta)
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestBugTaskDelta(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def test_get_empty_delta(self):
        # getDelta() should return None when no change has been made.
        bug_task = self.factory.makeBugTask()
        self.assertEqual(bug_task.getDelta(bug_task), None)

    def test_get_mismatched_delta(self):
        # getDelta() should raise TypeError when different types of
        # bug tasks are passed in.
        product = self.factory.makeProduct()
        product_bug_task = self.factory.makeBugTask(target=product)
        distro_source_package = self.factory.makeDistributionSourcePackage()
        distro_source_package_bug_task = self.factory.makeBugTask(
            target=distro_source_package)
        self.assertRaises(
            TypeError, product_bug_task.getDelta,
            distro_source_package_bug_task)

    def test_get_delta(self):
        # Exercise getDelta() with a full set of changes.
        user = self.factory.makePerson()
        product = self.factory.makeProduct(owner=user)
        bug_task = self.factory.makeBugTask(target=product)
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))
        store = Store.of(bug_task)
        store.flush()

        # bugwatch
        bug_watch = self.factory.makeBugWatch(bug=bug_task.bug, owner=user)
        store.flush()
        bug_task.bugwatch = bug_watch

        # target
        new_product = self.factory.makeProduct(owner=user)
        store.flush()
        bug_task.transitionToTarget(new_product)

        # milestone
        milestone = self.factory.makeMilestone(product=new_product)
        store.flush()
        bug_task.milestone = milestone

        # assignee
        new_user = self.factory.makePerson()
        store.flush()
        bug_task.transitionToAssignee(new_user)

        # status and importance
        bug_task.transitionToStatus(BugTaskStatus.FIXRELEASED, user)
        bug_task.transitionToImportance(BugTaskImportance.HIGH, user)
        store.flush()

        delta = bug_task.getDelta(bug_task_before_modification)
        expected_delta = {
            'bugtask': bug_task,
            'target': dict(old=product, new=new_product),
            'assignee': dict(old=None, new=new_user),
            'bugwatch': dict(old=None, new=bug_watch),
            'milestone': dict(old=None, new=milestone),
            'status':
                dict(old=bug_task_before_modification.status,
                     new=bug_task.status),
            'importance':
                dict(old=bug_task_before_modification.importance,
                     new=bug_task.importance),
            }

        for name in IBugTaskDelta:
            self.assertEquals(
                getattr(delta, name), expected_delta.get(name))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBugTaskDelta))
    suite.addTest(DocTestSuite('canonical.launchpad.database.bugtask'))
    return suite
