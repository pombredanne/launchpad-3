# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )
from doctest import DocTestSuite
from itertools import count
import unittest

from pytz import UTC
from storm.store import Store
from testtools.matchers import LessThan
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    login_person,
    )
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.browser import bugtask
from lp.bugs.browser.bugcomment import group_comments_with_activity
from lp.bugs.browser.bugtask import (
    BugTaskEditView,
    BugTasksAndNominationsView,
    )
from lp.bugs.interfaces.bugactivity import IBugActivitySet
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.services.propertycache import get_property_cache
from lp.testing import (
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import (
    ADMIN_EMAIL,
    NO_PRIVILEGE_EMAIL,
    USER_EMAIL,
    )
from lp.testing.views import create_initialized_view


class TestBugTaskView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def invalidate_caches(self, obj):
        store = Store.of(obj)
        # Make sure everything is in the database.
        store.flush()
        # And invalidate the cache (not a reset, because that stops us using
        # the domain objects)
        store.invalidate()

    def test_rendered_query_counts_constant_with_team_memberships(self):
        login(ADMIN_EMAIL)
        task = self.factory.makeBugTask()
        person_no_teams = self.factory.makePerson(password='test')
        person_with_teams = self.factory.makePerson(password='test')
        for _ in range(10):
            self.factory.makeTeam(members=[person_with_teams])
        # count with no teams
        url = canonical_url(task)
        recorder = QueryCollector()
        recorder.register()
        self.addCleanup(recorder.unregister)
        self.invalidate_caches(task)
        self.getUserBrowser(url, person_no_teams)
        # This may seem large: it is; there is easily another 30% fat in
        # there.
        self.assertThat(recorder, HasQueryCount(LessThan(62)))
        count_with_no_teams = recorder.count
        # count with many teams
        self.invalidate_caches(task)
        self.getUserBrowser(url, person_with_teams)
        # Allow an increase of one because storm bug 619017 causes additional
        # queries, revalidating things unnecessarily. An increase which is
        # less than the number of new teams shows it is definitely not
        # growing per-team.
        self.assertThat(recorder, HasQueryCount(
            LessThan(count_with_no_teams + 3),
            ))

    def test_interesting_activity(self):
        # The interesting_activity property returns a tuple of interesting
        # `BugActivityItem`s.
        bug = self.factory.makeBug()
        view = create_initialized_view(
            bug.default_bugtask, name=u'+index', rootsite='bugs')

        def add_activity(what, old=None, new=None, message=None):
            getUtility(IBugActivitySet).new(
                bug, datetime.now(UTC), bug.owner, whatchanged=what,
                oldvalue=old, newvalue=new, message=message)
            del get_property_cache(view).interesting_activity

        # A fresh bug has no interesting activity.
        self.assertEqual((), view.interesting_activity)

        # Some activity is not considered interesting.
        add_activity("boring")
        self.assertEqual((), view.interesting_activity)

        # A description change is interesting.
        add_activity("description")
        self.assertEqual(1, len(view.interesting_activity))
        [activity] = view.interesting_activity
        self.assertEqual("description", activity.whatchanged)


class BugActivityStub:

    def __init__(self, datechanged, person=None):
        self.datechanged = datechanged
        if person is None:
            person = PersonStub()
        self.person = person

    def __repr__(self):
        return "BugActivityStub(%r, %r)" % (
            self.datechanged.strftime('%Y-%m-%d--%H%M'), self.person)


class BugCommentStub:

    def __init__(self, datecreated, owner=None):
        self.datecreated = datecreated
        if owner is None:
            owner = PersonStub()
        self.owner = owner
        self.activity = []

    def __repr__(self):
        return "BugCommentStub(%r, %r)" % (
            self.datecreated.strftime('%Y-%m-%d--%H%M'), self.owner)


class PersonStub:

    ids = count(1)

    def __init__(self):
        self.id = next(self.ids)

    def __repr__(self):
        return "PersonStub#%d" % self.id


class TestGroupCommentsWithActivities(TestCase):
    """Tests for `group_comments_with_activities`."""

    def setUp(self):
        super(TestGroupCommentsWithActivities, self).setUp()
        self.now = datetime.now(UTC)
        self.timestamps = (
            self.now + timedelta(minutes=counter)
            for counter in count(1))

    def group(self, comments, activities):
        return list(
            group_comments_with_activity(
                comments=comments, activities=activities))

    def test_empty(self):
        # Given no comments or activities the result is also empty.
        self.assertEqual(
            [], self.group(comments=[], activities=[]))

    def test_activity_empty_no_common_actor(self):
        # When no activities is passed in, and the comments passed in don't
        # have any common actors, no grouping is possible.
        comments = [
            BugCommentStub(next(self.timestamps))
            for number in xrange(5)]
        self.assertEqual(
            comments, self.group(comments=comments, activities=[]))

    def test_comments_empty_no_common_actor(self):
        # When no comments are passed in, and the activities passed in don't
        # have any common actors, no grouping is possible.
        activities = [
            BugActivityStub(next(self.timestamps))
            for number in xrange(5)]
        self.assertEqual(
            [[activity] for activity in activities], self.group(
                comments=[], activities=activities))

    def test_no_common_actor(self):
        # When each activities and comment given has a different actor then no
        # grouping is possible.
        activity1 = BugActivityStub(next(self.timestamps))
        comment1 = BugCommentStub(next(self.timestamps))
        activity2 = BugActivityStub(next(self.timestamps))
        comment2 = BugCommentStub(next(self.timestamps))

        activities = set([activity1, activity2])
        comments = set([comment1, comment2])

        self.assertEqual(
            [[activity1], comment1, [activity2], comment2],
            self.group(comments=comments, activities=activities))

    def test_comment_then_activity_close_by_common_actor(self):
        # An activity shortly after a comment by the same person is grouped
        # into the comment.
        actor = PersonStub()
        comment = BugCommentStub(next(self.timestamps), actor)
        activity = BugActivityStub(next(self.timestamps), actor)
        grouped = self.group(comments=[comment], activities=[activity])
        self.assertEqual([comment], grouped)
        self.assertEqual([activity], comment.activity)

    def test_activity_then_comment_close_by_common_actor(self):
        # An activity shortly before a comment by the same person is grouped
        # into the comment.
        actor = PersonStub()
        activity = BugActivityStub(next(self.timestamps), actor)
        comment = BugCommentStub(next(self.timestamps), actor)
        grouped = self.group(comments=[comment], activities=[activity])
        self.assertEqual([comment], grouped)
        self.assertEqual([activity], comment.activity)

    def test_interleaved_activity_with_comments_by_common_actor(self):
        # Activities shortly before and after a comment are grouped into the
        # comment's activity.
        actor = PersonStub()
        activity1 = BugActivityStub(next(self.timestamps), actor)
        comment = BugCommentStub(next(self.timestamps), actor)
        activity2 = BugActivityStub(next(self.timestamps), actor)
        grouped = self.group(
            comments=[comment], activities=[activity1, activity2])
        self.assertEqual([comment], grouped)
        self.assertEqual([activity1, activity2], comment.activity)

    def test_common_actor_over_a_prolonged_time(self):
        # There is a timeframe for grouping events. Anything outside of that
        # window is considered separate.
        actor = PersonStub()
        activities = [
            BugActivityStub(next(self.timestamps), actor)
            for count in xrange(8)]
        grouped = self.group(comments=[], activities=activities)
        self.assertEqual(2, len(grouped))
        self.assertEqual(activities[:5], grouped[0])
        self.assertEqual(activities[5:], grouped[1])

    def test_two_comments_by_common_actor(self):
        # Only one comment will ever appear in a group.
        actor = PersonStub()
        comment1 = BugCommentStub(next(self.timestamps), actor)
        comment2 = BugCommentStub(next(self.timestamps), actor)
        grouped = self.group(comments=[comment1, comment2], activities=[])
        self.assertEqual([comment1, comment2], grouped)

    def test_two_comments_with_activity_by_common_actor(self):
        # Activity gets associated with earlier comment when all other factors
        # are unchanging.
        actor = PersonStub()
        activity1 = BugActivityStub(next(self.timestamps), actor)
        comment1 = BugCommentStub(next(self.timestamps), actor)
        activity2 = BugActivityStub(next(self.timestamps), actor)
        comment2 = BugCommentStub(next(self.timestamps), actor)
        activity3 = BugActivityStub(next(self.timestamps), actor)
        grouped = self.group(
            comments=[comment1, comment2],
            activities=[activity1, activity2, activity3])
        self.assertEqual([comment1, comment2], grouped)
        self.assertEqual([activity1, activity2], comment1.activity)
        self.assertEqual([activity3], comment2.activity)


class TestBugTasksAndNominationsView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTasksAndNominationsView, self).setUp()
        login(ADMIN_EMAIL)
        self.bug = self.factory.makeBug()
        self.view = BugTasksAndNominationsView(
            self.bug, LaunchpadTestRequest())

    def refresh(self):
        # The view caches, to see different scenarios, a refresh is needed.
        self.view = BugTasksAndNominationsView(
            self.bug, LaunchpadTestRequest())

    def test_current_user_affected_status(self):
        self.failUnlessEqual(
            None, self.view.current_user_affected_status)
        self.bug.markUserAffected(self.view.user, True)
        self.refresh()
        self.failUnlessEqual(
            True, self.view.current_user_affected_status)
        self.bug.markUserAffected(self.view.user, False)
        self.refresh()
        self.failUnlessEqual(
            False, self.view.current_user_affected_status)

    def test_current_user_affected_js_status(self):
        self.failUnlessEqual(
            'null', self.view.current_user_affected_js_status)
        self.bug.markUserAffected(self.view.user, True)
        self.refresh()
        self.failUnlessEqual(
            'true', self.view.current_user_affected_js_status)
        self.bug.markUserAffected(self.view.user, False)
        self.refresh()
        self.failUnlessEqual(
            'false', self.view.current_user_affected_js_status)

    def test_not_many_bugtasks(self):
        for count in range(10 - len(self.bug.bugtasks) - 1):
            self.factory.makeBugTask(bug=self.bug)
        self.view.initialize()
        self.failIf(self.view.many_bugtasks)
        row_view = self.view._getTableRowView(
            self.bug.default_bugtask, False, False)
        self.failIf(row_view.many_bugtasks)

    def test_many_bugtasks(self):
        for count in range(10 - len(self.bug.bugtasks)):
            self.factory.makeBugTask(bug=self.bug)
        self.view.initialize()
        self.failUnless(self.view.many_bugtasks)
        row_view = self.view._getTableRowView(
            self.bug.default_bugtask, False, False)
        self.failUnless(row_view.many_bugtasks)

    def test_other_users_affected_count(self):
        # The number of other users affected does not change when the
        # logged-in user marked him or herself as affected or not.
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)
        self.bug.markUserAffected(self.view.user, True)
        self.refresh()
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)
        self.bug.markUserAffected(self.view.user, False)
        self.refresh()
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)

    def test_other_users_affected_count_other_users(self):
        # The number of other users affected only changes when other
        # users mark themselves as affected.
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)
        other_user_1 = self.factory.makePerson()
        self.bug.markUserAffected(other_user_1, True)
        self.failUnlessEqual(
            2, self.view.other_users_affected_count)
        other_user_2 = self.factory.makePerson()
        self.bug.markUserAffected(other_user_2, True)
        self.failUnlessEqual(
            3, self.view.other_users_affected_count)
        self.bug.markUserAffected(other_user_1, False)
        self.failUnlessEqual(
            2, self.view.other_users_affected_count)
        self.bug.markUserAffected(self.view.user, True)
        self.refresh()
        self.failUnlessEqual(
            2, self.view.other_users_affected_count)

    def test_affected_statement_no_one_affected(self):
        self.bug.markUserAffected(self.bug.owner, False)
        self.failUnlessEqual(
            0, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "Does this bug affect you?",
            self.view.affected_statement)

    def test_affected_statement_only_you(self):
        self.view.context.markUserAffected(self.view.user, True)
        self.failUnless(self.bug.isUserAffected(self.view.user))
        self.view.context.markUserAffected(self.bug.owner, False)
        self.failUnlessEqual(
            0, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects you",
            self.view.affected_statement)

    def test_affected_statement_only_not_you(self):
        self.view.context.markUserAffected(self.view.user, False)
        self.failIf(self.bug.isUserAffected(self.view.user))
        self.view.context.markUserAffected(self.bug.owner, False)
        self.failUnlessEqual(
            0, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug doesn't affect you",
            self.view.affected_statement)

    def test_affected_statement_1_person_not_you(self):
        self.assertIs(None, self.bug.isUserAffected(self.view.user))
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects 1 person. Does this bug affect you?",
            self.view.affected_statement)

    def test_affected_statement_1_person_and_you(self):
        self.view.context.markUserAffected(self.view.user, True)
        self.failUnless(self.bug.isUserAffected(self.view.user))
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects you and 1 other person",
            self.view.affected_statement)

    def test_affected_statement_1_person_and_not_you(self):
        self.view.context.markUserAffected(self.view.user, False)
        self.failIf(self.bug.isUserAffected(self.view.user))
        self.failUnlessEqual(
            1, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects 1 person, but not you",
            self.view.affected_statement)

    def test_affected_statement_more_than_1_person_not_you(self):
        self.assertIs(None, self.bug.isUserAffected(self.view.user))
        other_user = self.factory.makePerson()
        self.view.context.markUserAffected(other_user, True)
        self.failUnlessEqual(
            2, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects 2 people. Does this bug affect you?",
            self.view.affected_statement)

    def test_affected_statement_more_than_1_person_and_you(self):
        self.view.context.markUserAffected(self.view.user, True)
        self.failUnless(self.bug.isUserAffected(self.view.user))
        other_user = self.factory.makePerson()
        self.view.context.markUserAffected(other_user, True)
        self.failUnlessEqual(
            2, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects you and 2 other people",
            self.view.affected_statement)

    def test_affected_statement_more_than_1_person_and_not_you(self):
        self.view.context.markUserAffected(self.view.user, False)
        self.failIf(self.bug.isUserAffected(self.view.user))
        other_user = self.factory.makePerson()
        self.view.context.markUserAffected(other_user, True)
        self.failUnlessEqual(
            2, self.view.other_users_affected_count)
        self.failUnlessEqual(
            "This bug affects 2 people, but not you",
            self.view.affected_statement)

    def test_anon_affected_statement_no_one_affected(self):
        self.bug.markUserAffected(self.bug.owner, False)
        self.failUnlessEqual(0, self.bug.users_affected_count)
        self.assertIs(None, self.view.anon_affected_statement)

    def test_anon_affected_statement_1_user_affected(self):
        self.failUnlessEqual(1, self.bug.users_affected_count)
        self.failUnlessEqual(
            "This bug affects 1 person",
            self.view.anon_affected_statement)

    def test_anon_affected_statement_2_users_affected(self):
        self.view.context.markUserAffected(self.view.user, True)
        self.failUnlessEqual(2, self.bug.users_affected_count)
        self.failUnlessEqual(
            "This bug affects 2 people",
            self.view.anon_affected_statement)


class TestBugTaskEditViewStatusField(TestCaseWithFactory):
    """We show only those options as possible value in the status
    field that the user can select.
    """

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTaskEditViewStatusField, self).setUp()
        product_owner = self.factory.makePerson(name='product-owner')
        bug_supervisor = self.factory.makePerson(name='bug-supervisor')
        product = self.factory.makeProduct(
            owner=product_owner, bug_supervisor=bug_supervisor)
        self.bug = self.factory.makeBug(product=product)

    def getWidgetOptionTitles(self, widget):
        """Return the titles of options of the given choice widget."""
        return [
            item.value.title for item in widget.field.vocabulary]

    def test_status_field_items_for_anonymous(self):
        # Anonymous users see only the current value.
        login(ANONYMOUS)
        view = BugTaskEditView(
            self.bug.default_bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            ['New'], self.getWidgetOptionTitles(view.form_fields['status']))

    def test_status_field_items_for_ordinary_users(self):
        # Ordinary users can set the status to all values except Won't fix,
        # Expired, Triaged, Unknown.
        login(NO_PRIVILEGE_EMAIL)
        view = BugTaskEditView(
            self.bug.default_bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            ['New', 'Incomplete', 'Opinion', 'Invalid', 'Confirmed',
             'In Progress', 'Fix Committed', 'Fix Released'],
            self.getWidgetOptionTitles(view.form_fields['status']))

    def test_status_field_privileged_persons(self):
        # The bug target owner and the bug target supervisor can set
        # the status to any value except Unknown and Expired.
        for user in (
            self.bug.default_bugtask.pillar.owner,
            self.bug.default_bugtask.pillar.bug_supervisor):
            login_person(user)
            view = BugTaskEditView(
                self.bug.default_bugtask, LaunchpadTestRequest())
            view.initialize()
            self.assertEqual(
                ['New', 'Incomplete', 'Opinion', 'Invalid', "Won't Fix",
                 'Confirmed', 'Triaged', 'In Progress', 'Fix Committed',
                 'Fix Released'],
                self.getWidgetOptionTitles(view.form_fields['status']),
                'Unexpected set of settable status options for %s'
                % user.name)

    def test_status_field_bug_task_in_status_unknown(self):
        # If a bugtask has the status Unknown, this status is included
        # in the options.
        owner = self.bug.default_bugtask.pillar.owner
        login_person(owner)
        self.bug.default_bugtask.transitionToStatus(
            BugTaskStatus.UNKNOWN, owner)
        login(NO_PRIVILEGE_EMAIL)
        view = BugTaskEditView(
            self.bug.default_bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            ['New', 'Incomplete', 'Opinion', 'Invalid', 'Confirmed',
             'In Progress', 'Fix Committed', 'Fix Released', 'Unknown'],
            self.getWidgetOptionTitles(view.form_fields['status']))

    def test_status_field_bug_task_in_status_expired(self):
        # If a bugtask has the status Expired, this status is included
        # in the options.
        removeSecurityProxy(self.bug.default_bugtask).status = (
            BugTaskStatus.EXPIRED)
        login(NO_PRIVILEGE_EMAIL)
        view = BugTaskEditView(
            self.bug.default_bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            ['New', 'Incomplete', 'Opinion', 'Invalid', 'Expired',
             'Confirmed', 'In Progress', 'Fix Committed', 'Fix Released'],
            self.getWidgetOptionTitles(view.form_fields['status']))


class TestBugTaskEditViewAssigneeField(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTaskEditViewAssigneeField, self).setUp()
        self.owner = self.factory.makePerson()
        self.product = self.factory.makeProduct(owner=self.owner)
        self.bugtask = self.factory.makeBug(
            product=self.product).default_bugtask

    def test_assignee_vocabulary_regular_user_with_bug_supervisor(self):
        # For regular users, the assignee vocabulary is
        # AllUserTeamsParticipation if there is a bug supervisor defined.
        login_person(self.owner)
        self.product.setBugSupervisor(self.owner, self.owner)
        login(USER_EMAIL)
        view = BugTaskEditView(self.bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            'AllUserTeamsParticipation',
            view.form_fields['assignee'].field.vocabularyName)

    def test_assignee_vocabulary_regular_user_without_bug_supervisor(self):
        # For regular users, the assignee vocabulary is
        # ValidAssignee is there is not a bug supervisor defined.
        login_person(self.owner)
        self.product.setBugSupervisor(None, self.owner)
        login(USER_EMAIL)
        view = BugTaskEditView(self.bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            'ValidAssignee',
            view.form_fields['assignee'].field.vocabularyName)

    def test_assignee_field_vocabulary_privileged_user(self):
        # Privileged users, like the bug task target owner, can
        # assign anybody.
        login_person(self.bugtask.target.owner)
        view = BugTaskEditView(self.bugtask, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(
            'ValidAssignee',
            view.form_fields['assignee'].field.vocabularyName)


class TestProjectGroupBugs(TestCaseWithFactory):
    """Test the bugs overview page for Project Groups."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestProjectGroupBugs, self).setUp()
        self.owner = self.factory.makePerson(name='bob')
        self.projectgroup = self.factory.makeProject(name='container',
                                                     owner=self.owner)

    def makeSubordinateProduct(self, tracks_bugs_in_lp):
        """Create a new product and add it to the project group."""
        product = self.factory.makeProduct(official_malone=tracks_bugs_in_lp)
        with person_logged_in(product.owner):
            product.project = self.projectgroup

    def test_empty_project_group(self):
        # An empty project group does not use Launchpad for bugs.
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs')
        self.assertFalse(self.projectgroup.hasProducts())
        self.assertFalse(view.should_show_bug_information)

    def test_project_group_with_subordinate_not_using_launchpad(self):
        # A project group with all subordinates not using Launchpad
        # will itself be marked as not using Launchpad for bugs.
        self.makeSubordinateProduct(False)
        self.assertTrue(self.projectgroup.hasProducts())
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs')
        self.assertFalse(view.should_show_bug_information)

    def test_project_group_with_subordinate_using_launchpad(self):
        # A project group with one subordinate using Launchpad
        # will itself be marked as using Launchpad for bugs.
        self.makeSubordinateProduct(True)
        self.assertTrue(self.projectgroup.hasProducts())
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs')
        self.assertTrue(view.should_show_bug_information)

    def test_project_group_with_mixed_subordinates(self):
        # A project group with one or more subordinates using Launchpad
        # will itself be marked as using Launchpad for bugs.
        self.makeSubordinateProduct(False)
        self.makeSubordinateProduct(True)
        self.assertTrue(self.projectgroup.hasProducts())
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs')
        self.assertTrue(view.should_show_bug_information)

    def test_project_group_has_no_portlets_if_not_using_LP(self):
        # A project group that has no projects using Launchpad will not have
        # bug portlets.
        self.makeSubordinateProduct(False)
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs',
            current_request=True)
        self.assertFalse(view.should_show_bug_information)
        contents = view.render()
        report_a_bug = find_tag_by_id(contents, 'bug-portlets')
        self.assertIs(None, report_a_bug)

    def test_project_group_has_portlets_link_if_using_LP(self):
        # A project group that has projects using Launchpad will have a
        # portlets.
        self.makeSubordinateProduct(True)
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs',
            current_request=True)
        self.assertTrue(view.should_show_bug_information)
        contents = view.render()
        report_a_bug = find_tag_by_id(contents, 'bug-portlets')
        self.assertIsNot(None, report_a_bug)

    def test_project_group_has_help_link_if_not_using_LP(self):
        # A project group that has no projects using Launchpad will have
        # a 'Getting started' help link.
        self.makeSubordinateProduct(False)
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs',
            current_request=True)
        contents = view.render()
        help_link = find_tag_by_id(contents, 'getting-started-help')
        self.assertIsNot(None, help_link)

    def test_project_group_has_no_help_link_if_using_LP(self):
        # A project group that has no projects using Launchpad will not have
        # a 'Getting started' help link.
        self.makeSubordinateProduct(True)
        view = create_initialized_view(
            self.projectgroup, name=u'+bugs', rootsite='bugs',
            current_request=True)
        contents = view.render()
        help_link = find_tag_by_id(contents, 'getting-started-help')
        print help_link
        self.assertIs(None, help_link)


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTest(DocTestSuite(bugtask))
    suite.addTest(LayeredDocFileSuite(
        'bugtask-target-link-titles.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
