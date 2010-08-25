# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import timedelta
from doctest import DocTestSuite
import unittest

from lazr.lifecycle.snapshot import Snapshot
from zope.component import getUtility
from zope.interface import providedBy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.searchbuilder import (
    all,
    any,
    )
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.bugs.interfaces.bugtarget import IBugTarget
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.bugs.model.bugtask import build_tag_search_clause
from lp.hardwaredb.interfaces.hwdb import (
    HWBus,
    IHWDeviceSet,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPerson, IPersonSet
from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    logout,
    normalize_whitespace,
    TestCase,
    TestCaseWithFactory,
    )


class TestBugTaskDelta(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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


class TestBugTaskPermissionsToSetAssigneeMixin:

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create the test setup.

        We need
        - bug task targets (a product and a product series, or
          a distribution and distoseries, see classes derived from
          this one)
        - persons and team with special roles: product and distribution,
          owners, bug supervisors, drivers
        - bug tasks for the targets
        """
        super(TestBugTaskPermissionsToSetAssigneeMixin, self).setUp()
        self.target_owner_member = self.factory.makePerson()
        self.target_owner_team = self.factory.makeTeam(
            owner=self.target_owner_member)
        self.regular_user = self.factory.makePerson()

        login_person(self.target_owner_member)
        # Target and bug supervisor creation are deferred to sub-classes.
        self.makeTarget()
        self.setBugSupervisor()

        self.driver_team = self.factory.makeTeam(
            owner=self.target_owner_member)
        self.driver_member = self.factory.makePerson()
        self.driver_team.addMember(
            self.driver_member, self.target_owner_member)
        self.target.driver = self.driver_team

        self.series_driver_team = self.factory.makeTeam(
            owner=self.target_owner_member)
        self.series_driver_member = self.factory.makePerson()
        self.series_driver_team.addMember(
            self.series_driver_member, self.target_owner_member)
        self.series.driver = self.series_driver_team

        self.series_bugtask = self.factory.makeBugTask(target=self.series)
        self.series_bugtask.transitionToAssignee(self.regular_user)
        bug = self.series_bugtask.bug
        # If factory.makeBugTask() is called with a series target, it
        # creates automatically another bug task for the main target.
        self.target_bugtask = bug.getBugTask(self.target)
        self.target_bugtask.transitionToAssignee(self.regular_user)
        logout()

    def makeTarget(self):
        """Create a target and a series.

        The target and series must be assigned as attributes of self:
        'self.target' and 'self.series'.
        """
        raise NotImplementedError(self.makeTarget)

    def setBugSupervisor(self):
        """Set bug supervisor variables.

        This is the standard interface for sub-classes, but this
        method should return _setBugSupervisorData or
        _setBugSupervisorDataNone depending on what is required.
        """
        raise NotImplementedError(self.setBugSupervisor)

    def _setBugSupervisorData(self):
        """Helper function used by sub-classes to setup bug supervisors."""
        self.supervisor_team = self.factory.makeTeam(
            owner=self.target_owner_member)
        self.supervisor_member = self.factory.makePerson()
        self.supervisor_team.addMember(
            self.supervisor_member, self.target_owner_member)
        self.target.setBugSupervisor(
            self.supervisor_team, self.target_owner_member)

    def _setBugSupervisorDataNone(self):
        """Helper for sub-classes to work around setting a bug supervisor."""
        self.supervisor_member = None

    def test_userCanSetAnyAssignee_anonymous_user(self):
        # Anonymous users cannot set anybody as an assignee.
        login(ANONYMOUS)
        self.assertFalse(self.target_bugtask.userCanSetAnyAssignee(None))
        self.assertFalse(self.series_bugtask.userCanSetAnyAssignee(None))

    def test_userCanUnassign_anonymous_user(self):
        # Anonymous users cannot unassign anyone.
        login(ANONYMOUS)
        self.assertFalse(self.target_bugtask.userCanUnassign(None))
        self.assertFalse(self.series_bugtask.userCanUnassign(None))

    def test_userCanSetAnyAssignee_regular_user(self):
        # If we have a bug supervisor, check that regular user cannot
        # assign to someone else.  Otherwise, the regular user should
        # be able to assign to anyone.
        login_person(self.regular_user)
        if self.supervisor_member is not None:
            self.assertFalse(
                self.target_bugtask.userCanSetAnyAssignee(self.regular_user))
            self.assertFalse(
                self.series_bugtask.userCanSetAnyAssignee(self.regular_user))
        else:
            self.assertTrue(
                self.target_bugtask.userCanSetAnyAssignee(self.regular_user))
            self.assertTrue(
                self.series_bugtask.userCanSetAnyAssignee(self.regular_user))

    def test_userCanUnassign_regular_user(self):
        # Ordinary users can unassign themselves...
        login_person(self.regular_user)
        self.assertEqual(self.target_bugtask.assignee, self.regular_user)
        self.assertEqual(self.series_bugtask.assignee, self.regular_user)
        self.assertTrue(
            self.target_bugtask.userCanUnassign(self.regular_user))
        self.assertTrue(
            self.series_bugtask.userCanUnassign(self.regular_user))
        # ...but not other assignees.
        login_person(self.target_owner_member)
        other_user = self.factory.makePerson()
        self.series_bugtask.transitionToAssignee(other_user)
        self.target_bugtask.transitionToAssignee(other_user)
        login_person(self.regular_user)
        self.assertFalse(
            self.target_bugtask.userCanUnassign(self.regular_user))
        self.assertFalse(
            self.series_bugtask.userCanUnassign(self.regular_user))

    def test_userCanSetAnyAssignee_target_owner(self):
        # The bug task target owner can assign anybody.
        login_person(self.target_owner_member)
        self.assertTrue(
            self.target_bugtask.userCanSetAnyAssignee(self.target.owner))
        self.assertTrue(
            self.series_bugtask.userCanSetAnyAssignee(self.target.owner))

    def test_userCanUnassign_target_owner(self):
        # The target owner can unassign anybody.
        login_person(self.target_owner_member)
        self.assertTrue(
            self.target_bugtask.userCanUnassign(self.target_owner_member))
        self.assertTrue(
            self.series_bugtask.userCanUnassign(self.target_owner_member))

    def test_userCanSetAnyAssignee_bug_supervisor(self):
        # A bug supervisor can assign anybody.
        if self.supervisor_member is not None:
            login_person(self.supervisor_member)
            self.assertTrue(
                self.target_bugtask.userCanSetAnyAssignee(
                    self.supervisor_member))
            self.assertTrue(
                self.series_bugtask.userCanSetAnyAssignee(
                    self.supervisor_member))

    def test_userCanUnassign_bug_supervisor(self):
        # A bug supervisor can unassign anybody.
        if self.supervisor_member is not None:
            login_person(self.supervisor_member)
            self.assertTrue(
                self.target_bugtask.userCanUnassign(self.supervisor_member))
            self.assertTrue(
                self.series_bugtask.userCanUnassign(self.supervisor_member))

    def test_userCanSetAnyAssignee_driver(self):
        # A project driver can assign anybody.
        login_person(self.driver_member)
        self.assertTrue(
            self.target_bugtask.userCanSetAnyAssignee(self.driver_member))
        self.assertTrue(
            self.series_bugtask.userCanSetAnyAssignee(self.driver_member))

    def test_userCanUnassign_driver(self):
        # A project driver can unassign anybody.
        login_person(self.driver_member)
        self.assertTrue(
            self.target_bugtask.userCanUnassign(self.driver_member))
        self.assertTrue(
            self.series_bugtask.userCanUnassign(self.driver_member))

    def test_userCanSetAnyAssignee_series_driver(self):
        # A series driver can assign anybody to series bug tasks.
        login_person(self.driver_member)
        self.assertTrue(
            self.series_bugtask.userCanSetAnyAssignee(
                self.series_driver_member))
        # But he cannot assign anybody to bug tasks of the main target.
        self.assertFalse(
            self.target_bugtask.userCanSetAnyAssignee(
                self.series_driver_member))

    def test_userCanUnassign_series_driver(self):
        # The target owner can unassign anybody from series bug tasks...
        login_person(self.series_driver_member)
        self.assertTrue(
            self.series_bugtask.userCanUnassign(self.series_driver_member))
        # ...but not from tasks of the main product/distribution.
        self.assertFalse(
            self.target_bugtask.userCanUnassign(self.series_driver_member))

    def test_userCanSetAnyAssignee_launchpad_admins(self):
        # Launchpad admins can assign anybody.
        login_person(self.target_owner_member)
        foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        login_person(foo_bar)
        self.assertTrue(self.target_bugtask.userCanSetAnyAssignee(foo_bar))
        self.assertTrue(self.series_bugtask.userCanSetAnyAssignee(foo_bar))

    def test_userCanUnassign_launchpad_admins(self):
        # Launchpad admins can unassign anybody.
        login_person(self.target_owner_member)
        foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        login_person(foo_bar)
        self.assertTrue(self.target_bugtask.userCanUnassign(foo_bar))
        self.assertTrue(self.series_bugtask.userCanUnassign(foo_bar))

    def test_userCanSetAnyAssignee_bug_importer(self):
        # The bug importer celebrity can assign anybody.
        login_person(self.target_owner_member)
        bug_importer = getUtility(ILaunchpadCelebrities).bug_importer
        login_person(bug_importer)
        self.assertTrue(
            self.target_bugtask.userCanSetAnyAssignee(bug_importer))
        self.assertTrue(
            self.series_bugtask.userCanSetAnyAssignee(bug_importer))

    def test_userCanUnassign_launchpad_bug_importer(self):
        # The bug importer celebrity can unassign anybody.
        login_person(self.target_owner_member)
        bug_importer = getUtility(ILaunchpadCelebrities).bug_importer
        login_person(bug_importer)
        self.assertTrue(self.target_bugtask.userCanUnassign(bug_importer))
        self.assertTrue(self.series_bugtask.userCanUnassign(bug_importer))


class TestProductBugTaskPermissionsToSetAssignee(
    TestBugTaskPermissionsToSetAssigneeMixin, TestCaseWithFactory):

    def makeTarget(self):
        """Create a product and a product series."""
        self.target = self.factory.makeProduct(owner=self.target_owner_team)
        self.series = self.factory.makeProductSeries(self.target)

    def setBugSupervisor(self):
        """Establish a bug supervisor for this target."""
        self._setBugSupervisorData()


class TestProductNoBugSupervisorBugTaskPermissionsToSetAssignee(
    TestBugTaskPermissionsToSetAssigneeMixin, TestCaseWithFactory):

    def makeTarget(self):
        """Create a product and a product series without a bug supervisor."""
        self.target = self.factory.makeProduct(owner=self.target_owner_team)
        self.series = self.factory.makeProductSeries(self.target)

    def setBugSupervisor(self):
        """Set bug supervisor to None."""
        self._setBugSupervisorDataNone()


class TestDistributionBugTaskPermissionsToSetAssignee(
    TestBugTaskPermissionsToSetAssigneeMixin, TestCaseWithFactory):

    def makeTarget(self):
        """Create a distribution and a distroseries."""
        self.target = self.factory.makeDistribution(
            owner=self.target_owner_team)
        self.series = self.factory.makeDistroSeries(self.target)

    def setBugSupervisor(self):
        """Set bug supervisor to None."""
        self._setBugSupervisorData()


class TestDistributionNoBugSupervisorBugTaskPermissionsToSetAssignee(
    TestBugTaskPermissionsToSetAssigneeMixin, TestCaseWithFactory):

    def makeTarget(self):
        """Create a distribution and a distroseries."""
        self.target = self.factory.makeDistribution(
            owner=self.target_owner_team)
        self.series = self.factory.makeDistroSeries(self.target)

    def setBugSupervisor(self):
        """Establish a bug supervisor for this target."""
        self._setBugSupervisorDataNone()


class TestBugTaskSearch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def login(self):
        # Log in as an arbitrary person.
        person = self.factory.makePerson()
        login_person(person)
        self.addCleanup(logout)
        return person

    def makeBugTarget(self):
        """Make an arbitrary bug target with no tasks on it."""
        return IBugTarget(self.factory.makeProduct())

    def test_no_tasks(self):
        # A brand new bug target has no tasks.
        target = self.makeBugTarget()
        self.assertEqual([], list(target.searchTasks(None)))

    def test_new_task_shows_up(self):
        # When we create a new bugtask on the target, it shows up in
        # searchTasks.
        target = self.makeBugTarget()
        self.login()
        task = self.factory.makeBugTask(target=target)
        self.assertEqual([task], list(target.searchTasks(None)))

    def test_modified_since_excludes_earlier_bugtasks(self):
        # When we search for bug tasks that have been modified since a certain
        # time, tasks for bugs that have not been modified since then are
        # excluded.
        target = self.makeBugTarget()
        self.login()
        task = self.factory.makeBugTask(target=target)
        date = task.bug.date_last_updated + timedelta(days=1)
        result = target.searchTasks(None, modified_since=date)
        self.assertEqual([], list(result))

    def test_modified_since_includes_later_bugtasks(self):
        # When we search for bug tasks that have been modified since a certain
        # time, tasks for bugs that have been modified since then are
        # included.
        target = self.makeBugTarget()
        self.login()
        task = self.factory.makeBugTask(target=target)
        date = task.bug.date_last_updated - timedelta(days=1)
        result = target.searchTasks(None, modified_since=date)
        self.assertEqual([task], list(result))

    def test_modified_since_includes_later_bugtasks_excludes_earlier(self):
        # When we search for bugs that have been modified since a certain
        # time, tasks for bugs that have been modified since then are
        # included, tasks that have not are excluded.
        target = self.makeBugTarget()
        self.login()
        task1 = self.factory.makeBugTask(target=target)
        date = task1.bug.date_last_updated
        task1.bug.date_last_updated -= timedelta(days=1)
        task2 = self.factory.makeBugTask(target=target)
        task2.bug.date_last_updated += timedelta(days=1)
        result = target.searchTasks(None, modified_since=date)
        self.assertEqual([task2], list(result))

    def test_private_bug_view_permissions_cached(self):
        """Private bugs from a search know the user can see the bugs."""
        target = self.makeBugTarget()
        person = self.login()
        self.factory.makeBug(product=target, private=True, owner=person)
        self.factory.makeBug(product=target, private=True, owner=person)
        # Search style and parameters taken from the milestone index view where
        # the issue was discovered.
        login_person(person)
        tasks = target.searchTasks(BugTaskSearchParams(person, omit_dupes=True,
            orderby=['status', '-importance', 'id']))
        # We must be finding the bugs.
        self.assertEqual(2, tasks.count())
        # Cache in the storm cache the account->person lookup so its not
        # distorting what we're testing.
        _ = IPerson(person.account, None)
        # One query and only one should be issued to get the tasks, bugs and
        # allow access to getConjoinedMaster attribute - an attribute that
        # triggers a permission check (nb: id does not trigger such a check)
        self.assertStatementCount(1,
            lambda:[task.getConjoinedMaster for task in tasks])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(DocTestSuite('lp.bugs.model.bugtask'))
    return suite
