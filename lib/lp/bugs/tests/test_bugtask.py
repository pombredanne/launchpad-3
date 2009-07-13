# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.interface import providedBy
from zope.testing.doctestunit import DocTestSuite

from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.hwdb import HWBus, IHWDeviceSet
from canonical.launchpad.searchbuilder import all, any
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer

from lp.bugs.interfaces.bugtask import (
    BugTaskImportance, BugTaskSearchParams, BugTaskStatus)
from lp.bugs.model.bugtask import build_tag_search_clause
from lp.registry.interfaces.distribution import IDistributionSet
from lp.testing import TestCase, normalize_whitespace, TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory


class TestBugTaskDelta(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTaskDelta, self).setUp()
        login('foo.bar@canonical.com')

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

    def check_delta(self, bug_task_before, bug_task_after, **expected_delta):
        # Get a delta between one bug task and another, then compare
        # the contents of the delta with expected_delta (a dict, or
        # something that can be dictified). Anything not mentioned in
        # expected_delta is assumed to be None in the delta.
        delta = bug_task_after.getDelta(bug_task_before)
        expected_delta.setdefault('bugtask', bug_task_after)
        names = set(
            name for interface in providedBy(delta) for name in interface)
        for name in names:
            self.assertEquals(
                getattr(delta, name), expected_delta.get(name))

    def test_get_bugwatch_delta(self):
        # Exercise getDelta() with a change to bugwatch.
        user = self.factory.makePerson()
        bug_task = self.factory.makeBugTask()
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))

        bug_watch = self.factory.makeBugWatch(bug=bug_task.bug)
        bug_task.bugwatch = bug_watch

        self.check_delta(
            bug_task_before_modification, bug_task,
            bugwatch=dict(old=None, new=bug_watch))

    def test_get_target_delta(self):
        # Exercise getDelta() with a change to target.
        user = self.factory.makePerson()
        product = self.factory.makeProduct(owner=user)
        bug_task = self.factory.makeBugTask(target=product)
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))

        new_product = self.factory.makeProduct(owner=user)
        bug_task.transitionToTarget(new_product)

        self.check_delta(
            bug_task_before_modification, bug_task,
            target=dict(old=product, new=new_product))

    def test_get_milestone_delta(self):
        # Exercise getDelta() with a change to milestone.
        user = self.factory.makePerson()
        product = self.factory.makeProduct(owner=user)
        bug_task = self.factory.makeBugTask(target=product)
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))

        milestone = self.factory.makeMilestone(product=product)
        bug_task.milestone = milestone

        self.check_delta(
            bug_task_before_modification, bug_task,
            milestone=dict(old=None, new=milestone))

    def test_get_assignee_delta(self):
        # Exercise getDelta() with a change to assignee.
        user = self.factory.makePerson()
        product = self.factory.makeProduct(owner=user)
        bug_task = self.factory.makeBugTask(target=product)
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))

        bug_task.transitionToAssignee(user)

        self.check_delta(
            bug_task_before_modification, bug_task,
            assignee=dict(old=None, new=user))

    def test_get_status_delta(self):
        # Exercise getDelta() with a change to status.
        user = self.factory.makePerson()
        product = self.factory.makeProduct(owner=user)
        bug_task = self.factory.makeBugTask(target=product)
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))

        bug_task.transitionToStatus(BugTaskStatus.FIXRELEASED, user)

        self.check_delta(
            bug_task_before_modification, bug_task,
            status=dict(old=bug_task_before_modification.status,
                        new=bug_task.status))

    def test_get_importance_delta(self):
        # Exercise getDelta() with a change to importance.
        user = self.factory.makePerson()
        product = self.factory.makeProduct(owner=user)
        bug_task = self.factory.makeBugTask(target=product)
        bug_task_before_modification = Snapshot(
            bug_task, providing=providedBy(bug_task))

        bug_task.transitionToImportance(BugTaskImportance.HIGH, user)

        self.check_delta(
            bug_task_before_modification, bug_task,
            importance=dict(old=bug_task_before_modification.importance,
                            new=bug_task.importance))


class TestBugTaskTagSearchClauses(TestCase):

    def searchClause(self, tag_spec):
        return build_tag_search_clause(tag_spec)

    def assertEqualIgnoringWhitespace(self, expected, observed):
        return self.assertEqual(
            normalize_whitespace(expected),
            normalize_whitespace(observed))

    def test_empty(self):
        # Specifying no tags is valid.
        self.assertEqual(self.searchClause(any()), None)
        self.assertEqual(self.searchClause(all()), None)

    def test_single_tag_presence(self):
        # The WHERE clause to test for the presence of a single
        # tag. Should be the same for an `any` query or an `all`
        # query.
        expected_query = (
            """BugTask.bug IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred')),
            expected_query)
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred')),
            expected_query)

    def test_single_tag_absence(self):
        # The WHERE clause to test for the absence of a single
        # tag. Should be the same for an `any` query or an `all`
        # query.
        expected_query = (
            """BugTask.bug NOT IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'-fred')),
            expected_query)
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'-fred')),
            expected_query)

    def test_tag_presence(self):
        # The WHERE clause to test for the presence of tags. Should be
        # the same for an `any` query or an `all` query.
        expected_query = (
            """BugTask.bug IN
                 (SELECT bug FROM BugTag)""")
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'*')),
            expected_query)
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'*')),
            expected_query)

    def test_tag_absence(self):
        # The WHERE clause to test for the absence of tags. Should be
        # the same for an `any` query or an `all` query.
        expected_query = (
            """BugTask.bug NOT IN
                 (SELECT bug FROM BugTag)""")
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'-*')),
            expected_query)
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'-*')),
            expected_query)

    def test_multiple_tag_presence_any(self):
        # The WHERE clause to test for the presence of *any* of
        # several tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'bob')),
            """BugTask.bug IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'bob'
                  UNION
                  SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")
        # In an `any` query, a positive wildcard is dominant over
        # other positive tags because "bugs with one or more tags" is
        # a superset of "bugs with a specific tag".
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'*')),
            """BugTask.bug IN
                 (SELECT bug FROM BugTag)""")

    def test_multiple_tag_absence_any(self):
        # The WHERE clause to test for the absence of *any* of several
        # tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'-fred', u'-bob')),
            """BugTask.bug NOT IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'bob'
                  INTERSECT
                  SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")
        # In an `any` query, a negative wildcard is superfluous in the
        # presence of other negative tags because "bugs without a
        # specific tag" is a superset of "bugs without any tags".
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'-fred', u'-*')),
            """BugTask.bug NOT IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")

    def test_multiple_tag_presence_all(self):
        # The WHERE clause to test for the presence of *all* specified
        # tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'bob')),
            """BugTask.bug IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'bob'
                  INTERSECT
                  SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")
        # In an `all` query, a positive wildcard is superfluous in the
        # presence of other positive tags because "bugs with a
        # specific tag" is a subset of (i.e. more specific than) "bugs
        # with one or more tags".
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'*')),
            """BugTask.bug IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")

    def test_multiple_tag_absence_all(self):
        # The WHERE clause to test for the absence of all specified
        # tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'-fred', u'-bob')),
            """BugTask.bug NOT IN
                 (SELECT bug FROM BugTag
                   WHERE tag = 'bob'
                  UNION
                  SELECT bug FROM BugTag
                   WHERE tag = 'fred')""")
        # In an `all` query, a negative wildcard is dominant over
        # other negative tags because "bugs without any tags" is a
        # subset of (i.e. more specific than) "bugs without a specific
        # tag".
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'-fred', u'-*')),
            """BugTask.bug NOT IN
                 (SELECT bug FROM BugTag)""")

    def test_mixed_tags_any(self):
        # The WHERE clause to test for the presence of one or more
        # specific tags or the absence of one or more other specific
        # tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'-bob')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'))""")
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'-bob', u'eric', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'eric'
                   UNION
                   SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'
                   INTERSECT
                   SELECT bug FROM BugTag
                    WHERE tag = 'harry'))""")
        # The positive wildcard is dominant over other positive tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'-bob', u'*', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag)
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'
                   INTERSECT
                   SELECT bug FROM BugTag
                    WHERE tag = 'harry'))""")
        # The negative wildcard is superfluous in the presence of
        # other negative tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'-bob', u'eric', u'-*')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'eric'
                   UNION
                   SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'))""")
        # The negative wildcard is not superfluous in the absence of
        # other negative tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'-*', u'eric')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'eric'
                   UNION
                   SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag))""")
        # The positive wildcard is dominant over other positive tags,
        # and the negative wildcard is superfluous in the presence of
        # other negative tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'fred', u'-*', u'*', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag)
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'harry'))""")

    def test_mixed_tags_all(self):
        # The WHERE clause to test for the presence of one or more
        # specific tags and the absence of one or more other specific
        # tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'-bob')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                     WHERE tag = 'fred')
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'))""")
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'-bob', u'eric', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'eric'
                   INTERSECT
                   SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'
                   UNION
                   SELECT bug FROM BugTag
                    WHERE tag = 'harry'))""")
        # The positive wildcard is superfluous in the presence of
        # other positive tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'-bob', u'*', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'
                   UNION
                   SELECT bug FROM BugTag
                    WHERE tag = 'harry'))""")
        # The positive wildcard is not superfluous in the absence of
        # other positive tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'-bob', u'*', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag)
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'bob'
                   UNION
                   SELECT bug FROM BugTag
                    WHERE tag = 'harry'))""")
        # The negative wildcard is dominant over other negative tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'-bob', u'eric', u'-*')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'eric'
                   INTERSECT
                   SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag))""")
        # The positive wildcard is superfluous in the presence of
        # other positive tags, and the negative wildcard is dominant
        # over other negative tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'fred', u'-*', u'*', u'-harry')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag
                    WHERE tag = 'fred')
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag))""")

    def test_mixed_wildcards(self):
        # The WHERE clause to test for the presence of tags or the
        # absence of tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(any(u'*', u'-*')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag)
                OR BugTask.bug NOT IN
                  (SELECT bug FROM BugTag))""")
        # The WHERE clause to test for the presence of tags and the
        # absence of tags.
        self.assertEqualIgnoringWhitespace(
            self.searchClause(all(u'*', u'-*')),
            """(BugTask.bug IN
                  (SELECT bug FROM BugTag)
                AND BugTask.bug NOT IN
                  (SELECT bug FROM BugTag))""")


class TestBugTaskHardwareSearch(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBugTaskHardwareSearch, self).setUp()
        self.layer.switchDbUser('launchpad')

    def test_search_results_without_duplicates(self):
        # Searching for hardware related bugtasks returns each
        # matching task exactly once, even if devices from more than
        # one HWDB submission match the given criteria.
        new_submission = self.factory.makeHWSubmission(
            emailaddress=u'test@canonical.com')
        self.layer.txn.commit()
        device = getUtility(IHWDeviceSet).getByDeviceID(
            HWBus.PCI, '0x10de', '0x0455')
        self.layer.switchDbUser('hwdb-submission-processor')
        self.factory.makeHWSubmissionDevice(
            new_submission, device, None, None, 1)
        self.layer.txn.commit()
        self.layer.switchDbUser('launchpad')
        search_params = BugTaskSearchParams(
            user=None, hardware_bus=HWBus.PCI, hardware_vendor_id='0x10de',
            hardware_product_id='0x0455', hardware_owner_is_bug_reporter=True)
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        bugtasks = ubuntu.searchTasks(search_params)
        self.assertEqual(
            [1, 2],
            [bugtask.bug.id for bugtask in bugtasks])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBugTaskDelta))
    suite.addTest(unittest.makeSuite(TestBugTaskTagSearchClauses))
    suite.addTest(unittest.makeSuite(TestBugTaskHardwareSearch))
    suite.addTest(DocTestSuite('lp.bugs.model.bugtask'))
    return suite
