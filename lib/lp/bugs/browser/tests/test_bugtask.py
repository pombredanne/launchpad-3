# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
import simplejson
from canonical.launchpad.webapp.interfaces import ILaunchBag

__metaclass__ = type

import transaction

from datetime import datetime

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from pytz import UTC
from storm.store import Store
from testtools.matchers import LessThan
from zope.component import (
    getMultiAdapter,
    getUtility,
    )
from zope.event import notify
from zope.interface import providedBy
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    login_person,
    )
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.browser.bugtask import (
    BugActivityItem,
    BugTaskEditView,
    BugTasksAndNominationsView,
    )
from lp.bugs.interfaces.bugactivity import IBugActivitySet
from lp.bugs.interfaces.bugnomination import IBugNomination
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IBugTask,
    IBugTaskSet,
    )
from lp.services.propertycache import get_property_cache
from lp.soyuz.interfaces.component import IComponentSet
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import (
    BrowsesWithQueryLimit,
    HasQueryCount,
    )
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
        self.assertThat(recorder, HasQueryCount(LessThan(74)))
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

    def test_rendered_query_counts_constant_with_attachments(self):
        with celebrity_logged_in('admin'):
            browses_under_limit = BrowsesWithQueryLimit(
                78, self.factory.makePerson())

            # First test with a single attachment.
            task = self.factory.makeBugTask()
            self.factory.makeBugAttachment(bug=task.bug)
        self.assertThat(task, browses_under_limit)

        with celebrity_logged_in('admin'):
            # And now with 10.
            task = self.factory.makeBugTask()
            self.factory.makeBugTask(bug=task.bug)
            for i in range(10):
                self.factory.makeBugAttachment(bug=task.bug)
        self.assertThat(task, browses_under_limit)

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

    def test_error_for_changing_target_with_invalid_status(self):
        # If a user moves a bug task with a restricted status (say,
        # Triaged) to a target where they do not have permission to set
        # that status, they will be unable to complete the retargeting
        # and will instead receive an error in the UI.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(
            name='product1', owner=person, official_malone=True)
        with person_logged_in(person):
            product.setBugSupervisor(person, person)
        product_2 = self.factory.makeProduct(
            name='product2', official_malone=True)
        with person_logged_in(product_2.owner):
            product_2.setBugSupervisor(product_2.owner, product_2.owner)
        bug = self.factory.makeBug(
            product=product, owner=person)
        # We need to commit here, otherwise all the sample data we
        # created gets destroyed when the transaction is rolled back.
        transaction.commit()
        with person_logged_in(person):
            form_data = {
                '%s.target' % product.name: 'product',
                '%s.target.product' % product.name: product_2.name,
                '%s.status' % product.name: BugTaskStatus.TRIAGED.title,
                '%s.actions.save' % product.name: 'Save Changes',
                }
            view = create_initialized_view(
                bug.default_bugtask, name=u'+editstatus',
                form=form_data)
            # The bugtask's target won't have changed, since an error
            # happend. The error will be listed in the view.
            self.assertEqual(1, len(view.errors))
            self.assertEqual(product, bug.default_bugtask.target)


class TestBugTasksAndNominationsView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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

    def test_getTargetLinkTitle_product(self):
        # The target link title is always none for products.
        target = self.factory.makeProduct()
        bug_task = self.factory.makeBugTask(bug=self.bug, target=target)
        self.view.initialize()
        self.assertEqual(None, self.view.getTargetLinkTitle(bug_task.target))

    def test_getTargetLinkTitle_productseries(self):
        # The target link title is always none for productseries.
        target = self.factory.makeProductSeries()
        bug_task = self.factory.makeBugTask(bug=self.bug, target=target)
        self.view.initialize()
        self.assertEqual(None, self.view.getTargetLinkTitle(bug_task.target))

    def test_getTargetLinkTitle_distribution(self):
        # The target link title is always none for distributions.
        target = self.factory.makeDistribution()
        bug_task = self.factory.makeBugTask(bug=self.bug, target=target)
        self.view.initialize()
        self.assertEqual(None, self.view.getTargetLinkTitle(bug_task.target))

    def test_getTargetLinkTitle_distroseries(self):
        # The target link title is always none for distroseries.
        target = self.factory.makeDistroSeries()
        bug_task = self.factory.makeBugTask(bug=self.bug, target=target)
        self.view.initialize()
        self.assertEqual(None, self.view.getTargetLinkTitle(bug_task.target))

    def test_getTargetLinkTitle_unpublished_distributionsourcepackage(self):
        # The target link title states that the package is not published
        # in the current release.
        distribution = self.factory.makeDistribution(name='boy')
        spn = self.factory.makeSourcePackageName('badger')
        component = getUtility(IComponentSet)['universe']
        maintainer = self.factory.makePerson(name="jim")
        creator = self.factory.makePerson(name="tim")
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distribution.currentseries, version='2.0',
            component=component, sourcepackagename=spn,
            date_uploaded=datetime(2008, 7, 18, 10, 20, 30, tzinfo=UTC),
            maintainer=maintainer, creator=creator)
        target = distribution.getSourcePackage('badger')
        bug_task = self.factory.makeBugTask(
            bug=self.bug, target=target, publish=False)
        self.view.initialize()
        self.assertEqual({}, self.view.target_releases)
        self.assertEqual(
            'No current release for this source package in Boy',
            self.view.getTargetLinkTitle(bug_task.target))

    def test_getTargetLinkTitle_published_distributionsourcepackage(self):
        # The target link title states the information about the current
        # package in the distro.
        distribution = self.factory.makeDistribution(name='koi')
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)
        spn = self.factory.makeSourcePackageName('finch')
        component = getUtility(IComponentSet)['universe']
        maintainer = self.factory.makePerson(name="jim")
        creator = self.factory.makePerson(name="tim")
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, version='2.0',
            component=component, sourcepackagename=spn,
            date_uploaded=datetime(2008, 7, 18, 10, 20, 30, tzinfo=UTC),
            maintainer=maintainer, creator=creator)
        target = distribution.getSourcePackage('finch')
        bug_task = self.factory.makeBugTask(
            bug=self.bug, target=target, publish=False)
        self.view.initialize()
        self.assertTrue(
            target in self.view.target_releases.keys())
        self.assertEqual(
            'Latest release: 2.0, uploaded to universe on '
            '2008-07-18 10:20:30+00:00 by Tim (tim), maintained by Jim (jim)',
            self.view.getTargetLinkTitle(bug_task.target))

    def test_getTargetLinkTitle_published_sourcepackage(self):
        # The target link title states the information about the current
        # package in the distro.
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName('bunny')
        component = getUtility(IComponentSet)['universe']
        maintainer = self.factory.makePerson(name="jim")
        creator = self.factory.makePerson(name="tim")
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, version='2.0',
            component=component, sourcepackagename=spn,
            date_uploaded=datetime(2008, 7, 18, 10, 20, 30, tzinfo=UTC),
            maintainer=maintainer, creator=creator)
        target = distroseries.getSourcePackage('bunny')
        bug_task = self.factory.makeBugTask(
            bug=self.bug, target=target, publish=False)
        self.view.initialize()
        self.assertTrue(
            target in self.view.target_releases.keys())
        self.assertEqual(
            'Latest release: 2.0, uploaded to universe on '
            '2008-07-18 10:20:30+00:00 by Tim (tim), maintained by Jim (jim)',
            self.view.getTargetLinkTitle(bug_task.target))

    def _get_object_type(self, task_or_nomination):
        if IBugTask.providedBy(task_or_nomination):
            return "bugtask"
        elif IBugNomination.providedBy(task_or_nomination):
            return "nomination"
        else:
            return "unknown"

    def test_bugtask_listing_for_inactive_projects(self):
        # Bugtasks should only be listed for active projects.

        product_foo = self.factory.makeProduct(name="foo")
        product_bar = self.factory.makeProduct(name="bar")
        foo_bug = self.factory.makeBug(product=product_foo)
        bugtask_set = getUtility(IBugTaskSet)
        bugtask_set.createTask(foo_bug, foo_bug.owner, product_bar)

        removeSecurityProxy(product_bar).active = False

        request = LaunchpadTestRequest()
        foo_bugtasks_and_nominations_view = getMultiAdapter(
            (foo_bug, request), name="+bugtasks-and-nominations-table")
        foo_bugtasks_and_nominations_view.initialize()

        task_and_nomination_views = (
            foo_bugtasks_and_nominations_view.getBugTaskAndNominationViews())
        actual_results = []
        for task_or_nomination_view in task_and_nomination_views:
            task_or_nomination = task_or_nomination_view.context
            actual_results.append((
                self._get_object_type(task_or_nomination),
                task_or_nomination.status.title,
                task_or_nomination.target.bugtargetdisplayname))
        # Only the one active project's task should be listed.
        self.assertEqual([("bugtask", "New", "Foo")], actual_results)

    def test_listing_with_no_bugtasks(self):
        # Test the situation when there are no bugtasks to show.

        product_foo = self.factory.makeProduct(name="foo")
        foo_bug = self.factory.makeBug(product=product_foo)
        removeSecurityProxy(product_foo).active = False

        request = LaunchpadTestRequest()
        foo_bugtasks_and_nominations_view = getMultiAdapter(
            (foo_bug, request), name="+bugtasks-and-nominations-table")
        foo_bugtasks_and_nominations_view.initialize()

        task_and_nomination_views = (
            foo_bugtasks_and_nominations_view.getBugTaskAndNominationViews())
        self.assertEqual([], task_and_nomination_views)

    def test_bugtarget_parent_shown_for_orphaned_series_tasks(self):
        # Test that a row is shown for the parent of a series task, even
        # if the parent doesn't actually have a task.
        series = self.factory.makeProductSeries()
        bug = self.factory.makeBug(series=series)
        self.assertEqual(2, len(bug.bugtasks))
        new_prod = self.factory.makeProduct()
        bug.getBugTask(series.product).transitionToTarget(new_prod)

        view = create_initialized_view(bug, "+bugtasks-and-nominations-table")
        subviews = view.getBugTaskAndNominationViews()
        self.assertEqual([
            (series.product, '+bugtasks-and-nominations-table-row'),
            (bug.getBugTask(series), '+bugtasks-and-nominations-table-row'),
            (bug.getBugTask(new_prod), '+bugtasks-and-nominations-table-row'),
            ], [(v.context, v.__name__) for v in subviews])

        content = subviews[0]()
        self.assertIn(
            'href="%s"' % canonical_url(
                series.product, path_only_if_possible=True),
            content)
        self.assertIn(series.product.displayname, content)


class TestBugTaskEditViewStatusField(TestCaseWithFactory):
    """We show only those options as possible value in the status
    field that the user can select.
    """

    layer = DatabaseFunctionalLayer

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

    layer = DatabaseFunctionalLayer

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


class TestBugTaskEditView(TestCaseWithFactory):
    """Test the bug task edit form."""

    layer = DatabaseFunctionalLayer

    def test_retarget_already_exists_error(self):
        user = self.factory.makePerson()
        login_person(user)
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        dsp_1 = self.factory.makeDistributionSourcePackage(
            distribution=ubuntu, sourcepackagename='mouse')
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=ubuntu.currentseries,
            sourcepackagename=dsp_1.sourcepackagename)
        bug_task_1 = self.factory.makeBugTask(target=dsp_1)
        dsp_2 = self.factory.makeDistributionSourcePackage(
            distribution=ubuntu, sourcepackagename='rabbit')
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=ubuntu.currentseries,
            sourcepackagename=dsp_2.sourcepackagename)
        bug_task_2 = self.factory.makeBugTask(
            bug=bug_task_1.bug, target=dsp_2)
        form = {
            'ubuntu_rabbit.actions.save': 'Save Changes',
            'ubuntu_rabbit.status': 'In Progress',
            'ubuntu_rabbit.importance': 'High',
            'ubuntu_rabbit.assignee.option':
                'ubuntu_rabbit.assignee.assign_to_nobody',
            'ubuntu_rabbit.target': 'package',
            'ubuntu_rabbit.target.distribution': 'ubuntu',
            'ubuntu_rabbit.target.package': 'mouse',
            }
        view = create_initialized_view(
            bug_task_2, name='+editstatus', form=form, principal=user)
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'A fix for this bug has already been requested for mouse in '
            'Ubuntu',
            view.errors[0])

    def setUpRetargetMilestone(self):
        """Setup a bugtask with a milestone and a product to retarget to."""
        first_product = self.factory.makeProduct(name='bunny')
        with person_logged_in(first_product.owner):
            first_product.official_malone = True
            bug = self.factory.makeBug(product=first_product)
            bug_task = bug.bugtasks[0]
            milestone = self.factory.makeMilestone(
                productseries=first_product.development_focus, name='1.0')
            bug_task.transitionToMilestone(milestone, first_product.owner)
        second_product = self.factory.makeProduct(name='duck')
        with person_logged_in(second_product.owner):
            second_product.official_malone = True
        return bug_task, second_product

    def test_retarget_product_with_milestone(self):
        # Milestones are always cleared when retargeting a product bug task.
        bug_task, second_product = self.setUpRetargetMilestone()
        user = self.factory.makePerson()
        login_person(user)
        form = {
            'bunny.status': 'In Progress',
            'bunny.assignee.option': 'bunny.assignee.assign_to_nobody',
            'bunny.target': 'product',
            'bunny.target.product': 'duck',
            'bunny.actions.save': 'Save Changes',
            }
        view = create_initialized_view(
            bug_task, name='+editstatus', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(second_product, bug_task.target)
        self.assertEqual(None, bug_task.milestone)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = ('The Bunny 1.0 milestone setting has been removed')
        self.assertTrue(notifications.pop().message.startswith(expected))

    def test_retarget_product_and_assign_milestone(self):
        # Milestones are always cleared when retargeting a product bug task.
        bug_task, second_product = self.setUpRetargetMilestone()
        login_person(bug_task.target.owner)
        milestone_id = bug_task.milestone.id
        bug_task.transitionToMilestone(None, bug_task.target.owner)
        form = {
            'bunny.status': 'In Progress',
            'bunny.assignee.option': 'bunny.assignee.assign_to_nobody',
            'bunny.target': 'product',
            'bunny.target.product': 'duck',
            'bunny.milestone': milestone_id,
            'bunny.actions.save': 'Save Changes',
            }
        view = create_initialized_view(
            bug_task, name='+editstatus', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(second_product, bug_task.target)
        self.assertEqual(None, bug_task.milestone)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = ('The milestone setting was ignored')
        self.assertTrue(notifications.pop().message.startswith(expected))

    def createNameChangingViewForSourcePackageTask(self, bug_task, new_name):
        login_person(bug_task.owner)
        form_prefix = '%s_%s_%s' % (
            bug_task.target.distroseries.distribution.name,
            bug_task.target.distroseries.name,
            bug_task.target.sourcepackagename.name)
        form = {
            form_prefix + '.sourcepackagename': new_name,
            form_prefix + '.actions.save': 'Save Changes',
            }
        view = create_initialized_view(
            bug_task, name='+editstatus', form=form)
        return view

    def test_retarget_sourcepackage(self):
        # The sourcepackagename of a SourcePackage task can be changed.
        ds = self.factory.makeDistroSeries()
        sp1 = self.factory.makeSourcePackage(distroseries=ds, publish=True)
        sp2 = self.factory.makeSourcePackage(distroseries=ds, publish=True)
        bug_task = self.factory.makeBugTask(target=sp1)

        view = self.createNameChangingViewForSourcePackageTask(
            bug_task, sp2.sourcepackagename.name)
        self.assertEqual([], view.errors)
        self.assertEqual(sp2, bug_task.target)
        notifications = view.request.response.notifications
        self.assertEqual(0, len(notifications))

    def test_retarget_sourcepackage_to_binary_name(self):
        # The sourcepackagename of a SourcePackage task can be changed
        # to a binarypackagename, which gets mapped back to the source.
        ds = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(distroseries=ds)
        sp1 = self.factory.makeSourcePackage(distroseries=ds, publish=True)
        # Now create a binary and its corresponding SourcePackage.
        bp = self.factory.makeBinaryPackagePublishingHistory(
            distroarchseries=das)
        bpr = bp.binarypackagerelease
        spn = bpr.build.source_package_release.sourcepackagename
        sp2 = self.factory.makeSourcePackage(
            distroseries=ds, sourcepackagename=spn, publish=True)
        bug_task = self.factory.makeBugTask(target=sp1)

        view = self.createNameChangingViewForSourcePackageTask(
            bug_task, bpr.binarypackagename.name)
        self.assertEqual([], view.errors)
        self.assertEqual(sp2, bug_task.target)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            "'%s' is a binary package. This bug has been assigned to its "
            "source package '%s' instead."
            % (bpr.binarypackagename.name, spn.name))
        self.assertTrue(notifications.pop().message.startswith(expected))

    def test_retarget_sourcepackage_to_distroseries(self):
        # A SourcePackage task can be changed to a DistroSeries one.
        ds = self.factory.makeDistroSeries()
        sp = self.factory.makeSourcePackage(distroseries=ds, publish=True)
        bug_task = self.factory.makeBugTask(target=sp)

        view = self.createNameChangingViewForSourcePackageTask(
            bug_task, '')
        self.assertEqual([], view.errors)
        self.assertEqual(ds, bug_task.target)
        notifications = view.request.response.notifications
        self.assertEqual(0, len(notifications))


class TestBugTaskSubscriptionPortletDetails(TestCaseWithFactory):
    # Tests for BugTaskSubscriptionPortletDetails

    layer = DatabaseFunctionalLayer

    def test_view_render(self):
        person = self.factory.makePerson()
        bug = self.factory.makeBug()
        login_person(person)
        bug.subscribe(person, person)
        bugtask = self.factory.makeBugTask(bug=bug)
        getUtility(ILaunchBag).add(bugtask)
        view = create_initialized_view(
            bugtask, name='+portlet-subscription-details', rootsite='bugs')
        content_data = simplejson.loads(view.render())

        # The view returns a dict containing  html and cache_data.
        contents = content_data['html']
        portlet = find_tag_by_id(contents, 'portlet-subscription')
        self.assertIsNot(None, portlet)
        cache_data = content_data['cache_data']
        self.assertFalse(cache_data['other_subscription_notifications'])
        subscription_data = cache_data['subscription']
        self.assertEqual(
            'http://launchpad.dev/api/devel/bugs/%s' % bug.id,
            subscription_data['bug_link'])
        self.assertEqual(
            'http://launchpad.dev/api/devel/~%s' % person.name,
            subscription_data['person_link'])
        self.assertEqual(
            'Discussion', subscription_data['bug_notification_level'])


class TestProjectGroupBugs(TestCaseWithFactory):
    """Test the bugs overview page for Project Groups."""

    layer = DatabaseFunctionalLayer

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
        self.assertIs(None, help_link)


class TestBugActivityItem(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setAttribute(self, obj, attribute, value):
        obj_before_modification = Snapshot(obj, providing=providedBy(obj))
        setattr(removeSecurityProxy(obj), attribute, value)
        notify(ObjectModifiedEvent(
            obj, obj_before_modification, [attribute],
            self.factory.makePerson()))

    def test_escapes_assignee(self):
        with celebrity_logged_in('admin'):
            task = self.factory.makeBugTask()
            self.setAttribute(
                task, 'assignee',
                self.factory.makePerson(displayname="Foo &<>", name='foo'))
        self.assertEquals(
            "nobody &#8594; Foo &amp;&lt;&gt; (foo)",
            BugActivityItem(task.bug.activity[-1]).change_details)

    def test_escapes_title(self):
        with celebrity_logged_in('admin'):
            bug = self.factory.makeBug(title="foo")
            self.setAttribute(bug, 'title', "bar &<>")
        self.assertEquals(
            "- foo<br />+ bar &amp;&lt;&gt;",
            BugActivityItem(bug.activity[-1]).change_details)
