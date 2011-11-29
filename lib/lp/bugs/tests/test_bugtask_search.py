# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import unittest

import pytz
from storm.expr import Join
from storm.store import Store
from testtools.matchers import Equals
from zope.component import getUtility

from canonical.launchpad.searchbuilder import (
    all,
    any,
    greater_than,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.bugs.interfaces.bugattachment import BugAttachmentType
from lp.bugs.interfaces.bugtask import (
    BugBlueprintSearch,
    BugBranchSearch,
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.bugs.model.bugsummary import BugSummary
from lp.bugs.model.bugtask import BugTask
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.model.person import Person
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


PRIVATE_BUG_VISIBILITY_FLAG = {
    'disclosure.private_bug_visibility_rules.enabled': 'on'}
PRIVATE_BUG_VISIBILITY_CTE_FLAG = {
    'disclosure.private_bug_visibility_cte.enabled': 'on'}


class SearchTestBase:
    """A mixin class with tests useful for all targets and search variants."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(SearchTestBase, self).setUp()
        self.bugtask_set = getUtility(IBugTaskSet)
        # We need a feature flag so that multipillar bugs can be made private.
        feature_flag = {
                'disclosure.allow_multipillar_private_bugs.enabled': 'on'}
        flags = FeatureFixture(feature_flag)
        flags.setUp()
        self.addCleanup(flags.cleanUp)

    def assertSearchFinds(self, params, expected_bugtasks):
        # Run a search for the given search parameters and check if
        # the result matches the expected bugtasks.
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(expected_bugtasks)
        self.assertEqual(expected, search_result)

    def test_aggregate_by_target(self):
        # BugTaskSet.search supports returning the counts for each target (as
        # long as only one type of target was selected).
        if self.group_on is None:
            # Not a useful/valid permutation.
            return
        self.getBugTaskSearchParams(user=None, multitarget=True)
        # The test data has 3 bugs for searchtarget and 6 for searchtarget2.
        user = self.factory.makePerson()
        expected = {(self.targetToGroup(self.searchtarget),): 3,
            (self.targetToGroup(self.searchtarget2),): 6}
        actual = self.bugtask_set.countBugs(
            user, (self.searchtarget, self.searchtarget2),
            group_on=self.group_on)
        self.assertEqual(expected, actual)

    def test_search_all_bugtasks_for_target(self):
        # BugTaskSet.search() returns all bug tasks for a given bug
        # target, if only the bug target is passed as a search parameter.
        params = self.getBugTaskSearchParams(user=None)
        self.assertSearchFinds(params, self.bugtasks)

    def test_private_bug_in_search_result_anonymous_users(self):
        # Private bugs are not included in search results for anonymous users.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        params = self.getBugTaskSearchParams(user=None)
        self.assertSearchFinds(params, self.bugtasks[:-1])

    def test_private_bug_in_search_result_unauthorised_users(self):
        # Private bugs are not included in search results for ordinary users.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        user = self.factory.makePerson()
        params = self.getBugTaskSearchParams(user=user)
        self.assertSearchFinds(params, self.bugtasks[:-1])

    def test_private_bug_in_search_result_subscribers(self):
        # If the user is subscribed to the bug, it is included in the
        # search result.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        user = self.factory.makePerson()
        admin = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        with person_logged_in(admin):
            bug = self.bugtasks[-1].bug
            bug.subscribe(user, self.owner)
        params = self.getBugTaskSearchParams(user=user)
        self.assertSearchFinds(params, self.bugtasks)

    def test_private_bug_in_search_result_admins(self):
        # Private bugs are included in search results for admins.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        admin = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        params = self.getBugTaskSearchParams(user=admin)
        self.assertSearchFinds(params, self.bugtasks)

    def test_private_bug_in_search_result_assignees(self):
        # Private bugs are included in search results for the assignee.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        bugtask = self.bugtasks[-1]
        user = self.factory.makePerson()
        admin = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        with person_logged_in(admin):
            bugtask.transitionToAssignee(user)
        params = self.getBugTaskSearchParams(user=user)
        self.assertSearchFinds(params, self.bugtasks)

    def test_private_bug_in_search_result_pillar_owners(self):
        # Private, non-security bugs are included in search results for the
        # pillar owners if the correct feature flag is enabled.
        bugtask = self.bugtasks[-1]
        pillar_owner = bugtask.pillar.owner
        with person_logged_in(self.owner):
            bugtask.bug.setPrivate(True, self.owner)
            bugtask.bug.unsubscribe(pillar_owner, self.owner)
        params = self.getBugTaskSearchParams(user=pillar_owner)
        # Check the results with the feature flag.
        with FeatureFixture(PRIVATE_BUG_VISIBILITY_FLAG):
            self.assertSearchFinds(params, self.bugtasks)
        # Check the results without the feature flag.
        self.assertSearchFinds(params, self.bugtasks[:-1])

        # Make the bugtask security related.
        with person_logged_in(self.owner):
            bugtask.bug.setSecurityRelated(True, self.owner)
            bugtask.bug.unsubscribe(pillar_owner, self.owner)
        # It should now be excluded from the results.
        with FeatureFixture(PRIVATE_BUG_VISIBILITY_FLAG):
            self.assertSearchFinds(params, self.bugtasks[:-1])

    def test_private_bug_in_search_result_pillar_owners_cte(self):
        # Like test_private_bug_in_search_result_pillar_owners, but with
        # the new CTE-based visibility query.
        bugtask = self.bugtasks[-1]
        pillar_owner = bugtask.pillar.owner
        with person_logged_in(self.owner):
            bugtask.bug.setPrivate(True, self.owner)
            bugtask.bug.unsubscribe(pillar_owner, self.owner)
        params = self.getBugTaskSearchParams(user=pillar_owner)
        # Check the results with the feature flag.
        flags = dict()
        flags.update(PRIVATE_BUG_VISIBILITY_FLAG)
        flags.update(PRIVATE_BUG_VISIBILITY_CTE_FLAG)
        with FeatureFixture(flags):
            self.assertSearchFinds(params, self.bugtasks)
        # Check the results without the feature flag.
        self.assertSearchFinds(params, self.bugtasks[:-1])

        # Make the bugtask security related.
        with person_logged_in(self.owner):
            bugtask.bug.setSecurityRelated(True, self.owner)
            bugtask.bug.unsubscribe(pillar_owner, self.owner)
        # It should now be excluded from the results.
        with FeatureFixture(PRIVATE_BUG_VISIBILITY_FLAG):
            self.assertSearchFinds(params, self.bugtasks[:-1])

    def test_search_by_bug_reporter(self):
        # Search results can be limited to bugs filed by a given person.
        bugtask = self.bugtasks[0]
        reporter = bugtask.bug.owner
        params = self.getBugTaskSearchParams(
            user=None, bug_reporter=reporter)
        self.assertSearchFinds(params, [bugtask])

    def test_search_by_bug_commenter(self):
        # Search results can be limited to bugs having a comment from a
        # given person.
        # Note that this does not include the bug description (which is
        # stored as the first comment of a bug.) Hence, if we let the
        # reporter of our first test bug comment on the second test bug,
        # a search for bugs having comments from this person retruns only
        # the second bug.
        commenter = self.bugtasks[0].bug.owner
        expected = self.bugtasks[1]
        with person_logged_in(commenter):
            expected.bug.newMessage(owner=commenter, content='a comment')
        params = self.getBugTaskSearchParams(
            user=None, bug_commenter=commenter)
        self.assertSearchFinds(params, [expected])

    def test_search_by_person_affected_by_bug(self):
        # Search results can be limited to bugs which affect a given person.
        affected_user = self.factory.makePerson()
        expected = self.bugtasks[0]
        with person_logged_in(affected_user):
            expected.bug.markUserAffected(affected_user)
        params = self.getBugTaskSearchParams(
            user=None, affected_user=affected_user)
        self.assertSearchFinds(params, [expected])

    def test_search_by_bugtask_assignee(self):
        # Search results can be limited to bugtask assigned to a given
        # person.
        assignee = self.factory.makePerson()
        expected = self.bugtasks[0]
        with person_logged_in(assignee):
            expected.transitionToAssignee(assignee)
        params = self.getBugTaskSearchParams(user=None, assignee=assignee)
        self.assertSearchFinds(params, [expected])

    def test_search_by_bug_subscriber(self):
        # Search results can be limited to bugs to which a given person
        # is subscribed.
        subscriber = self.factory.makePerson()
        expected = self.bugtasks[0]
        with person_logged_in(subscriber):
            expected.bug.subscribe(subscriber, subscribed_by=subscriber)
        params = self.getBugTaskSearchParams(user=None, subscriber=subscriber)
        self.assertSearchFinds(params, [expected])

    def subscribeToTarget(self, subscriber):
        # Subscribe the given person to the search target.
        with person_logged_in(subscriber):
            self.searchtarget.addSubscription(
                subscriber, subscribed_by=subscriber)

    def _findBugtaskForOtherProduct(self, bugtask, main_product):
        # Return the bugtask for the product that is not related to the
        # main bug target.
        #
        # The default bugtasks of this test suite are created by
        # ObjectFactory.makeBugTask() as follows:
        # - a new bug is created having a new product as the target.
        # - another bugtask is created for self.searchtarget (or,
        #   when self.searchtarget is a milestone, for the product
        #   of the milestone)
        # This method returns the bug task for the product that is not
        # related to the main bug target.
        bug = bugtask.bug
        for other_task in bug.bugtasks:
            other_target = other_task.target
            if (IProduct.providedBy(other_target)
                and other_target != main_product):
                return other_task
        self.fail(
            'No bug task found for a product that is not the target of '
            'the main test bugtask.')

    def findBugtaskForOtherProduct(self, bugtask):
        # Return the bugtask for the product that is not related to the
        # main bug target.
        #
        # This method must ober overridden for product related tests.
        return self._findBugtaskForOtherProduct(bugtask, None)

    def test_search_by_structural_subscriber(self):
        # Search results can be limited to bugs with a bug target to which
        # a given person has a structural subscription.
        subscriber = self.factory.makePerson()
        # If the given person is not subscribed, no bugtasks are returned.
        params = self.getBugTaskSearchParams(
            user=None, structural_subscriber=subscriber)
        self.assertSearchFinds(params, [])
        # When the person is subscribed, all bugtasks are returned.
        self.subscribeToTarget(subscriber)
        params = self.getBugTaskSearchParams(
            user=None, structural_subscriber=subscriber)
        self.assertSearchFinds(params, self.bugtasks)

        # Searching for a structural subscriber does not return a bugtask,
        # if the person is subscribed to another target than the main
        # bug target.
        other_subscriber = self.factory.makePerson()
        other_bugtask = self.findBugtaskForOtherProduct(self.bugtasks[0])
        other_target = other_bugtask.target
        with person_logged_in(other_subscriber):
            other_target.addSubscription(
                other_subscriber, subscribed_by=other_subscriber)
        params = self.getBugTaskSearchParams(
            user=None, structural_subscriber=other_subscriber)
        self.assertSearchFinds(params, [])

    def test_search_by_bug_attachment(self):
        # Search results can be limited to bugs having attachments of
        # a given type.
        with person_logged_in(self.owner):
            self.bugtasks[0].bug.addAttachment(
                owner=self.owner, data='filedata', comment='a comment',
                filename='file1.txt', is_patch=False)
            self.bugtasks[1].bug.addAttachment(
                owner=self.owner, data='filedata', comment='a comment',
                filename='file1.txt', is_patch=True)
        # We can search for bugs with non-patch attachments...
        params = self.getBugTaskSearchParams(
            user=None, attachmenttype=BugAttachmentType.UNSPECIFIED)
        self.assertSearchFinds(params, self.bugtasks[:1])
        # ... for bugs with patches...
        params = self.getBugTaskSearchParams(
            user=None, attachmenttype=BugAttachmentType.PATCH)
        self.assertSearchFinds(params, self.bugtasks[1:2])
        # and for bugs with patches or attachments
        params = self.getBugTaskSearchParams(
            user=None, attachmenttype=any(
                BugAttachmentType.PATCH,
                BugAttachmentType.UNSPECIFIED))
        self.assertSearchFinds(params, self.bugtasks[:2])

    def setUpFullTextSearchTests(self):
        # Set text fields indexed by Bug.fti, or
        # MessageChunk.fti to values we can search for.
        for bugtask, number in zip(self.bugtasks, ('one', 'two', 'three')):
            commenter = self.bugtasks[0].bug.owner
            with person_logged_in(commenter):
                bugtask.bug.title = 'bug title %s' % number
                bugtask.bug.newMessage(
                    owner=commenter, content='comment %s' % number)

    def test_fulltext_search(self):
        # Full text searches find text indexed by Bug.fti...
        self.setUpFullTextSearchTests()
        params = self.getBugTaskSearchParams(
            user=None, searchtext='one title')
        self.assertSearchFinds(params, self.bugtasks[:1])
        # ...and by MessageChunk.fti
        params = self.getBugTaskSearchParams(
            user=None, searchtext='three comment')
        self.assertSearchFinds(params, self.bugtasks[2:3])

    def test_fast_fulltext_search(self):
        # Fast full text searches find text indexed by Bug.fti...
        self.setUpFullTextSearchTests()
        params = self.getBugTaskSearchParams(
            user=None, fast_searchtext='one title')
        self.assertSearchFinds(params, self.bugtasks[:1])
        # ..or by MessageChunk.fti
        params = self.getBugTaskSearchParams(
            user=None, fast_searchtext='three comment')
        self.assertSearchFinds(params, [])

    def test_has_no_upstream_bugtask(self):
        # Search results can be limited to bugtasks of bugs that do
        # not have a related upstream task.
        #
        # All bugs created in makeBugTasks() have at least one
        # bug task for a product: The default bug task created
        # by lp.testing.factory.Factory.makeBug() if neither a
        # product nor a distribution is specified. For distribution
        # related tests we need another bug which does not have
        # an upstream (aka product) bug task, otherwise the set of
        # bugtasks returned for a search for has_no_upstream_bugtask
        # would always be empty.
        if (IDistribution.providedBy(self.searchtarget) or
            ISourcePackage.providedBy(self.searchtarget) or
            IDistributionSourcePackage.providedBy(self.searchtarget)):
            if IDistribution.providedBy(self.searchtarget):
                bug = self.factory.makeBug(distribution=self.searchtarget)
                expected = [bug.default_bugtask]
            else:
                bug = self.factory.makeBug(
                    distribution=self.searchtarget.distribution,
                    sourcepackagename=self.factory.makeSourcePackageName())
                bugtask = self.factory.makeBugTask(
                    bug=bug, target=self.searchtarget)
                expected = [bugtask]
        elif IDistroSeries.providedBy(self.searchtarget):
            bug = self.factory.makeBug(
                distribution=self.searchtarget.distribution)
            bugtask = self.factory.makeBugTask(
                bug=bug, target=self.searchtarget)
            expected = [bugtask]
        else:
            # Bugs without distribution related bugtasks have always at
            # least one product related bugtask, hence a
            # has_no_upstream_bugtask search will always return an
            # empty result set.
            expected = []
        params = self.getBugTaskSearchParams(
            user=None, has_no_upstream_bugtask=True)
        self.assertSearchFinds(params, expected)

    def changeStatusOfBugTaskForOtherProduct(self, bugtask, new_status):
        # Change the status of another bugtask of the same bug to the
        # given status.
        other_task = self.findBugtaskForOtherProduct(bugtask)
        with person_logged_in(other_task.target.owner):
            other_task.transitionToStatus(new_status, other_task.target.owner)

    def test_upstream_status(self):
        # Search results can be filtered by the status of an upstream
        # bug task.
        #
        # The bug task status of the default test data has only bug tasks
        # with status NEW for the "other" product, hence all bug tasks
        # will be returned in a search for bugs that are open upstream.
        params = self.getBugTaskSearchParams(user=None, open_upstream=True)
        self.assertSearchFinds(params, self.bugtasks)
        # A search for tasks resolved upstream does not yield any bugtask.
        params = self.getBugTaskSearchParams(
            user=None, resolved_upstream=True)
        self.assertSearchFinds(params, [])
        # But if we set upstream bug tasks to "fix committed" or "fix
        # released", the related bug tasks for our test target appear in
        # the search result.
        self.changeStatusOfBugTaskForOtherProduct(
            self.bugtasks[0], BugTaskStatus.FIXCOMMITTED)
        self.changeStatusOfBugTaskForOtherProduct(
            self.bugtasks[1], BugTaskStatus.FIXRELEASED)
        self.assertSearchFinds(params, self.bugtasks[:2])
        # A search for bug tasks open upstream now returns only one
        # test task.
        params = self.getBugTaskSearchParams(user=None, open_upstream=True)
        self.assertSearchFinds(params, self.bugtasks[2:])

    def test_tags(self):
        # Search results can be limited to bugs having given tags.
        with person_logged_in(self.owner):
            self.bugtasks[0].bug.tags = ['tag1', 'tag2']
            self.bugtasks[1].bug.tags = ['tag1', 'tag3']
        params = self.getBugTaskSearchParams(
            user=None, tag=any('tag2', 'tag3'))
        self.assertSearchFinds(params, self.bugtasks[:2])

        params = self.getBugTaskSearchParams(
            user=None, tag=all('tag2', 'tag3'))
        self.assertSearchFinds(params, [])

        params = self.getBugTaskSearchParams(
            user=None, tag=all('tag1', 'tag3'))
        self.assertSearchFinds(params, self.bugtasks[1:2])

        params = self.getBugTaskSearchParams(
            user=None, tag=all('tag1', '-tag3'))
        self.assertSearchFinds(params, self.bugtasks[:1])

        params = self.getBugTaskSearchParams(
            user=None, tag=all('-tag1'))
        self.assertSearchFinds(params, self.bugtasks[2:])

        params = self.getBugTaskSearchParams(
            user=None, tag=all('*'))
        self.assertSearchFinds(params, self.bugtasks[:2])

        params = self.getBugTaskSearchParams(
            user=None, tag=all('-*'))
        self.assertSearchFinds(params, self.bugtasks[2:])

    def test_date_closed(self):
        # Search results can be filtered by the date_closed time
        # of a bugtask.
        with person_logged_in(self.owner):
            self.bugtasks[2].transitionToStatus(
                BugTaskStatus.FIXRELEASED, self.owner)
        utc_now = datetime.now(pytz.timezone('UTC'))
        self.assertTrue(utc_now >= self.bugtasks[2].date_closed)
        params = self.getBugTaskSearchParams(
            user=None, date_closed=greater_than(utc_now - timedelta(days=1)))
        self.assertSearchFinds(params, self.bugtasks[2:])
        params = self.getBugTaskSearchParams(
            user=None, date_closed=greater_than(utc_now + timedelta(days=1)))
        self.assertSearchFinds(params, [])

    def test_created_since(self):
        # Search results can be limited to bugtasks created after a
        # given time.
        one_day_ago = self.bugtasks[0].datecreated - timedelta(days=1)
        two_days_ago = self.bugtasks[0].datecreated - timedelta(days=2)
        with person_logged_in(self.owner):
            self.bugtasks[0].datecreated = two_days_ago
        params = self.getBugTaskSearchParams(
            user=None, created_since=one_day_ago)
        self.assertSearchFinds(params, self.bugtasks[1:])

    def test_modified_since(self):
        # Search results can be limited to bugs modified after a
        # given time.
        one_day_ago = (
            self.bugtasks[0].bug.date_last_updated - timedelta(days=1))
        two_days_ago = (
            self.bugtasks[0].bug.date_last_updated - timedelta(days=2))
        with person_logged_in(self.owner):
            self.bugtasks[0].bug.date_last_updated = two_days_ago
        params = self.getBugTaskSearchParams(
            user=None, modified_since=one_day_ago)
        self.assertSearchFinds(params, self.bugtasks[1:])

    def test_branches_linked(self):
        # Search results can be limited to bugs with or without linked
        # branches.
        with person_logged_in(self.owner):
            branch = self.factory.makeBranch()
            self.bugtasks[0].bug.linkBranch(branch, self.owner)
        params = self.getBugTaskSearchParams(
            user=None, linked_branches=BugBranchSearch.BUGS_WITH_BRANCHES)
        self.assertSearchFinds(params, self.bugtasks[:1])
        params = self.getBugTaskSearchParams(
            user=None, linked_branches=BugBranchSearch.BUGS_WITHOUT_BRANCHES)
        self.assertSearchFinds(params, self.bugtasks[1:])

    def test_blueprints_linked(self):
        # Search results can be limited to bugs with or without linked
        # blueprints.
        with person_logged_in(self.owner):
            blueprint = self.factory.makeSpecification()
            blueprint.linkBug(self.bugtasks[0].bug)
        params = self.getBugTaskSearchParams(
            user=None, linked_blueprints=(
                BugBlueprintSearch.BUGS_WITH_BLUEPRINTS))
        self.assertSearchFinds(params, self.bugtasks[:1])
        params = self.getBugTaskSearchParams(
            user=None, linked_blueprints=(
                BugBlueprintSearch.BUGS_WITHOUT_BLUEPRINTS))
        self.assertSearchFinds(params, self.bugtasks[1:])

    def test_limit_search_to_one_bug(self):
        # Search results can be limited to a given bug.
        params = self.getBugTaskSearchParams(
            user=None, bug=self.bugtasks[0].bug)
        self.assertSearchFinds(params, self.bugtasks[:1])
        other_bug = self.factory.makeBug()
        params = self.getBugTaskSearchParams(user=None, bug=other_bug)
        self.assertSearchFinds(params, [])

    def test_filter_by_status(self):
        # Search results can be limited to bug tasks with a given status.
        params = self.getBugTaskSearchParams(
            user=None, status=BugTaskStatus.FIXCOMMITTED)
        self.assertSearchFinds(params, self.bugtasks[2:])
        params = self.getBugTaskSearchParams(
            user=None, status=any(BugTaskStatus.NEW, BugTaskStatus.TRIAGED))
        self.assertSearchFinds(params, self.bugtasks[:2])
        params = self.getBugTaskSearchParams(
            user=None, status=BugTaskStatus.WONTFIX)
        self.assertSearchFinds(params, [])

    def test_filter_by_importance(self):
        # Search results can be limited to bug tasks with a given importance.
        params = self.getBugTaskSearchParams(
            user=None, importance=BugTaskImportance.HIGH)
        self.assertSearchFinds(params, self.bugtasks[:1])
        params = self.getBugTaskSearchParams(
            user=None,
            importance=any(BugTaskImportance.HIGH, BugTaskImportance.LOW))
        self.assertSearchFinds(params, self.bugtasks[:2])
        params = self.getBugTaskSearchParams(
            user=None, importance=BugTaskImportance.MEDIUM)
        self.assertSearchFinds(params, [])

    def test_omit_duplicate_bugs(self):
        # Duplicate bugs can optionally be excluded from search results.
        # The default behaviour is to include duplicates.
        duplicate_bug = self.bugtasks[0].bug
        master_bug = self.bugtasks[1].bug
        with person_logged_in(self.owner):
            duplicate_bug.markAsDuplicate(master_bug)
        params = self.getBugTaskSearchParams(user=None)
        self.assertSearchFinds(params, self.bugtasks)
        # If we explicitly pass the parameter omit_duplicates=False, we get
        # the same result.
        params = self.getBugTaskSearchParams(user=None, omit_dupes=False)
        self.assertSearchFinds(params, self.bugtasks)
        # If omit_duplicates is set to True, the first task bug is omitted.
        params = self.getBugTaskSearchParams(user=None, omit_dupes=True)
        self.assertSearchFinds(params, self.bugtasks[1:])

    def test_has_cve(self):
        # Search results can be limited to bugs linked to a CVE.
        with person_logged_in(self.owner):
            cve = self.factory.makeCVE('2010-0123')
            self.bugtasks[0].bug.linkCVE(cve, self.owner)
        params = self.getBugTaskSearchParams(user=None, has_cve=True)
        self.assertSearchFinds(params, self.bugtasks[:1])

    def test_sort_by_milestone_name(self):
        expected = self.setUpMilestoneSorting()
        params = self.getBugTaskSearchParams(
            user=None, orderby='milestone_name')
        self.assertSearchFinds(params, expected)
        expected.reverse()
        params = self.getBugTaskSearchParams(
            user=None, orderby='-milestone_name')
        self.assertSearchFinds(params, expected)

    def test_sort_by_bug_reporter(self):
        params = self.getBugTaskSearchParams(user=None, orderby='reporter')
        expected = sorted(self.bugtasks, key=lambda task: task.bug.owner.name)
        self.assertSearchFinds(params, expected)
        expected.reverse()
        params = self.getBugTaskSearchParams(user=None, orderby='-reporter')
        self.assertSearchFinds(params, expected)

    def test_sort_by_bug_assignee(self):
        with person_logged_in(self.owner):
            self.bugtasks[2].transitionToAssignee(
                self.factory.makePerson(name="assignee-1"))
            self.bugtasks[1].transitionToAssignee(
                self.factory.makePerson(name="assignee-2"))
        expected = [self.bugtasks[2], self.bugtasks[1], self.bugtasks[0]]
        params = self.getBugTaskSearchParams(user=None, orderby='assignee')
        self.assertSearchFinds(params, expected)
        expected.reverse()
        params = self.getBugTaskSearchParams(user=None, orderby='-assignee')
        self.assertSearchFinds(params, expected)

    def test_sort_by_bug_title(self):
        params = self.getBugTaskSearchParams(user=None, orderby='title')
        expected = sorted(self.bugtasks, key=lambda task: task.bug.title)
        self.assertSearchFinds(params, expected)
        expected.reverse()
        params = self.getBugTaskSearchParams(user=None, orderby='-title')
        self.assertSearchFinds(params, expected)

    def test_sort_by_tag(self):
        with person_logged_in(self.owner):
            self.bugtasks[2].bug.tags = ['tag-a', 'tag-d']
            self.bugtasks[1].bug.tags = ['tag-b', 'tag-c']
        params = self.getBugTaskSearchParams(user=None, orderby='tag')
        expected = [self.bugtasks[2], self.bugtasks[1], self.bugtasks[0]]
        self.assertSearchFinds(params, expected)
        expected.reverse()
        params = self.getBugTaskSearchParams(user=None, orderby='-tag')
        self.assertSearchFinds(params, expected)

    def test_sort_by_linked_specification(self):
        with person_logged_in(self.owner):
            spec_1 = self.factory.makeSpecification(
                name='spec-1', owner=self.owner)
            spec_1.linkBug(self.bugtasks[2].bug)
            spec_1_1 = self.factory.makeSpecification(
                name='spec-1-1', owner=self.owner)
            spec_1_1.linkBug(self.bugtasks[2].bug)
            spec_2 = self.factory.makeSpecification(
                name='spec-2', owner=self.owner)
            spec_2.linkBug(self.bugtasks[1].bug)
        params = self.getBugTaskSearchParams(
            user=None, orderby='specification')
        expected = [self.bugtasks[2], self.bugtasks[1], self.bugtasks[0]]
        self.assertSearchFinds(params, expected)
        expected.reverse()
        params = self.getBugTaskSearchParams(
            user=None, orderby='-specification')
        self.assertSearchFinds(params, expected)


class DeactivatedProductBugTaskTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(DeactivatedProductBugTaskTestCase, self).setUp()
        self.person = self.factory.makePerson()
        self.active_product = self.factory.makeProduct()
        self.inactive_product = self.factory.makeProduct()
        bug = self.factory.makeBug(
            product=self.active_product,
            description="Monkeys are bad.")
        self.active_bugtask = self.factory.makeBugTask(
            bug=bug,
            target=self.active_product)
        self.inactive_bugtask = self.factory.makeBugTask(
            bug=bug,
            target=self.inactive_product)
        with person_logged_in(self.person):
            self.active_bugtask.transitionToAssignee(self.person)
            self.inactive_bugtask.transitionToAssignee(self.person)
        admin = getUtility(IPersonSet).getByEmail('admin@canonical.com')
        with person_logged_in(admin):
            self.inactive_product.active = False

    def test_deactivated_listings_not_seen(self):
        # Someone without permission to see deactiveated projects does
        # not see bugtasks for deactivated projects.
        bugtask_set = getUtility(IBugTaskSet)
        param = BugTaskSearchParams(user=None, fast_searchtext='Monkeys')
        results = bugtask_set.search(param, _noprejoins=True)
        self.assertEqual([self.active_bugtask], list(results))


class ProductAndDistributionTests:
    """Tests which are useful for distributions and products."""

    def makeSeries(self):
        """Return a series for the main bug target of this class."""
        raise NotImplementedError

    def test_search_by_bug_nomination(self):
        # Search results can be limited to bugs nominated to a given
        # series.
        series1 = self.makeSeries()
        series2 = self.makeSeries()
        nominator = self.factory.makePerson()
        with person_logged_in(self.owner):
            self.bugtasks[0].bug.addNomination(nominator, series1)
            self.bugtasks[1].bug.addNomination(nominator, series2)
        params = self.getBugTaskSearchParams(user=None, nominated_for=series1)
        self.assertSearchFinds(params, self.bugtasks[:1])


class ProjectGroupAndDistributionTests:
    """Tests which are useful for project groups and distributions."""

    def setUpStructuralSubscriptions(self):
        # Subscribe a user to the search target of this test and to
        # another target.
        raise NotImplementedError

    def test_unique_results_for_multiple_structural_subscriptions(self):
        # Searching for a subscriber who is more than once subscribed to a
        # bug task returns this bug task only once.
        subscriber = self.setUpStructuralSubscriptions()
        params = self.getBugTaskSearchParams(
            user=None, structural_subscriber=subscriber)
        self.assertSearchFinds(params, self.bugtasks)


class BugTargetTestBase:
    """A base class for the bug target mixin classes.

    :ivar searchtarget: A bug context to search within.
    :ivar searchtarget2: A sibling bug context for testing cross-context
        searches. Created on demand when
        getBugTaskSearchParams(multitarget=True) is called.
    :ivar bugtasks2: Bugtasks created for searchtarget2. Twice as many are
        made as for searchtarget.
    :ivar group_on: The columns to group on when calling countBugs. None
        if the target being testing is not sensible/implemented for counting
        bugs. For instance, grouping by project group may be interesting but
        at the time of writing is not implemented.
    """

    def makeBugTasks(self, bugtarget=None, bugtasks=None, owner=None):
        if bugtasks is None:
            self.bugtasks = []
            bugtasks = self.bugtasks
        if bugtarget is None:
            bugtarget = self.searchtarget
        if owner is None:
            owner = self.owner
        with person_logged_in(owner):
            bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            bugtasks[-1].importance = BugTaskImportance.HIGH
            bugtasks[-1].transitionToStatus(
                BugTaskStatus.TRIAGED, owner)

            bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            bugtasks[-1].importance = BugTaskImportance.LOW
            bugtasks[-1].transitionToStatus(
                BugTaskStatus.NEW, owner)

            bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            bugtasks[-1].importance = BugTaskImportance.CRITICAL
            bugtasks[-1].transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, owner)

    def getBugTaskSearchParams(self, multitarget=False, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.

        :param multitarget: If True multiple targets are used using any(
            self.searchtarget, self.searchtarget2).
        """
        params = BugTaskSearchParams(*args, **kw)
        if multitarget and getattr(self, 'searchtarget2', None) is None:
            self.setUpTarget2()
        if not multitarget:
            target = self.searchtarget
        else:
            target = any(self.searchtarget, self.searchtarget2)
        self.setBugParamsTarget(params, target)
        return params

    def targetToGroup(self, target):
        """Convert a search target to a group_on result."""
        return target.id


class BugTargetWithBugSuperVisor:
    """A base class for bug targets which have a bug supervisor."""

    def test_search_by_bug_supervisor(self):
        # We can search for bugs by bug supervisor.
        # We have by default no bug supervisor set, so searching for
        # bugs by supervisor returns no data.
        supervisor = self.factory.makeTeam(owner=self.owner)
        params = self.getBugTaskSearchParams(
            user=None, bug_supervisor=supervisor)
        self.assertSearchFinds(params, [])

        # If we appoint a bug supervisor, searching for bug tasks
        # by supervisor will return all bugs for our test target.
        self.setSupervisor(supervisor)
        self.assertSearchFinds(params, self.bugtasks)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task target."""
        with person_logged_in(self.owner):
            self.searchtarget.setBugSupervisor(supervisor, self.owner)


class ProductTarget(BugTargetTestBase, ProductAndDistributionTests,
                    BugTargetWithBugSuperVisor):
    """Use a product as the bug target."""

    def setUp(self):
        super(ProductTarget, self).setUp()
        self.group_on = (BugSummary.product_id,)
        self.searchtarget = self.factory.makeProduct()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeProduct()
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)

    def setBugParamsTarget(self, params, target):
        params.setProduct(target)

    def makeSeries(self):
        """See `ProductAndDistributionTests`."""
        return self.factory.makeProductSeries(product=self.searchtarget)

    def findBugtaskForOtherProduct(self, bugtask):
        # Return the bugtask for the product that is not related to the
        # main bug target.
        return self._findBugtaskForOtherProduct(bugtask, self.searchtarget)

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                product=self.searchtarget, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                product=self.searchtarget, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


class ProductSeriesTarget(BugTargetTestBase):
    """Use a product series as the bug target."""

    def setUp(self):
        super(ProductSeriesTarget, self).setUp()
        self.group_on = (BugSummary.productseries_id,)
        self.searchtarget = self.factory.makeProductSeries()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeProductSeries(
            product=self.searchtarget.product)
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)

    def setBugParamsTarget(self, params, target):
        params.setProductSeries(target)

    def changeStatusOfBugTaskForOtherProduct(self, bugtask, new_status):
        # Change the status of another bugtask of the same bug to the
        # given status.
        #
        # This method is called by SearchTestBase.test_upstream_status().
        # A search for bugs which are open or closed upstream has an
        # odd behaviour when the search target is a product series: In
        # this case, all bugs with an open or closed bug task for _any_
        # product are returned, including bug tasks for the main product
        # of the series. Hence we must set the status for all products
        # in order to avoid a failure of test_upstream_status().
        for other_task in bugtask.related_tasks:
            other_target = other_task.target
            if IProduct.providedBy(other_target):
                with person_logged_in(other_target.owner):
                    other_task.transitionToStatus(
                        new_status, other_target.owner)

    def findBugtaskForOtherProduct(self, bugtask):
        # Return the bugtask for the product that not related to the
        # main bug target.
        return self._findBugtaskForOtherProduct(
            bugtask, self.searchtarget.product)

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                productseries=self.searchtarget, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                productseries=self.searchtarget, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


class ProjectGroupTarget(BugTargetTestBase, BugTargetWithBugSuperVisor,
                         ProjectGroupAndDistributionTests):
    """Use a project group as the bug target."""

    def setUp(self):
        super(ProjectGroupTarget, self).setUp()
        self.group_on = None
        self.searchtarget = self.factory.makeProject()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeProject()
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)

    def setBugParamsTarget(self, params, target):
        params.setProject(target)

    def makeBugTasks(self, bugtarget=None, bugtasks=None, owner=None):
        """Create bug tasks for the search target."""
        if bugtasks is None:
            self.bugtasks = []
            bugtasks = self.bugtasks
        if bugtarget is None:
            bugtarget = self.searchtarget
        if owner is None:
            owner = self.owner
        self.products = []
        with person_logged_in(owner):
            product = self.factory.makeProduct(owner=owner)
            self.products.append(product)
            product.project = self.searchtarget
            bugtasks.append(
                self.factory.makeBugTask(target=product))
            bugtasks[-1].importance = BugTaskImportance.HIGH
            bugtasks[-1].transitionToStatus(
                BugTaskStatus.TRIAGED, owner)

            product = self.factory.makeProduct(owner=owner)
            self.products.append(product)
            product.project = self.searchtarget
            bugtasks.append(
                self.factory.makeBugTask(target=product))
            bugtasks[-1].importance = BugTaskImportance.LOW
            bugtasks[-1].transitionToStatus(
            BugTaskStatus.NEW, owner)

            product = self.factory.makeProduct(owner=owner)
            self.products.append(product)
            product.project = self.searchtarget
            bugtasks.append(
                self.factory.makeBugTask(target=product))
            bugtasks[-1].importance = BugTaskImportance.CRITICAL
            bugtasks[-1].transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, owner)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task targets."""
        with person_logged_in(self.owner):
            # We must set the bug supervisor for each bug task target
            for bugtask in self.bugtasks:
                bugtask.target.setBugSupervisor(supervisor, self.owner)

    def findBugtaskForOtherProduct(self, bugtask):
        # Return the bugtask for the product that not related to the
        # main bug target.
        bug = bugtask.bug
        for other_task in bug.bugtasks:
            other_target = other_task.target
            if (IProduct.providedBy(other_target)
                and other_target not in self.products):
                return other_task
        self.fail(
            'No bug task found for a product that is not the target of '
            'the main test bugtask.')

    def setUpStructuralSubscriptions(self):
        # See `ProjectGroupAndDistributionTests`.
        subscriber = self.factory.makePerson()
        self.subscribeToTarget(subscriber)
        with person_logged_in(subscriber):
            self.bugtasks[0].target.addSubscription(
                subscriber, subscribed_by=subscriber)
        return subscriber

    def test_disable_targetnames_search(self):
        # searching in the target name is contentious and arguably a bug. To
        # permit incremental changes we allow it to be disabled via a feature
        # flag.
        with person_logged_in(self.owner):
            product1 = self.factory.makeProduct(name='product-foo',
                owner=self.owner, project=self.searchtarget)
            product2 = self.factory.makeProduct(name='product-bar',
                owner=self.owner, project=self.searchtarget)
            bug1 = self.factory.makeBug(product=product1)
            bug1.default_bugtask.updateTargetNameCache()
            self.factory.makeBug(product=product2)
        params = self.getBugTaskSearchParams(user=None, searchtext='uct-fo')
        # With no flag, we find the first bug.
        self.assertSearchFinds(params, [bug1.default_bugtask])
        with FeatureFixture({'malone.disable_targetnamesearch': u'on'}):
            # With a flag set, no bugs are found.
            self.assertSearchFinds(params, [])

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                product=self.bugtasks[1].target, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                product=self.bugtasks[2].target, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


class MilestoneTarget(BugTargetTestBase):
    """Use a milestone as the bug target."""

    def setUp(self):
        super(MilestoneTarget, self).setUp()
        self.product = self.factory.makeProduct()
        self.group_on = (BugSummary.milestone_id,)
        self.searchtarget = self.factory.makeMilestone(product=self.product)
        self.owner = self.product.owner
        self.makeBugTasks(bugtarget=self.product)

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeMilestone(product=self.product)
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.product,
            bugtasks=self.bugtasks2, owner=self.product.owner,
            searchtarget=self.searchtarget2)
        self.makeBugTasks(bugtarget=self.product,
            bugtasks=self.bugtasks2, owner=self.product.owner,
            searchtarget=self.searchtarget2)

    def setBugParamsTarget(self, params, target):
        params.milestone = target

    def makeBugTasks(self, bugtarget=None, bugtasks=None, owner=None,
        searchtarget=None):
        """Create bug tasks for a product and assign them to a milestone."""
        super(MilestoneTarget, self).makeBugTasks(bugtarget=bugtarget,
            bugtasks=bugtasks, owner=owner)
        if bugtasks is None:
            bugtasks = self.bugtasks
        if owner is None:
            owner = self.owner
        if searchtarget is None:
            searchtarget = self.searchtarget
        with person_logged_in(owner):
            for bugtask in bugtasks:
                bugtask.transitionToMilestone(searchtarget, owner)

    def findBugtaskForOtherProduct(self, bugtask):
        # Return the bugtask for the product that not related to the
        # main bug target.
        return self._findBugtaskForOtherProduct(bugtask, self.product)

    def setUpMilestoneSorting(self):
        # Setup for a somewhat pointless test: All bugtasks are already
        # assigned to same milestone. This means essentially that the
        # search result should be ordered by the secondary sort order,
        # BugTask.importance.
        # Note that reversing the sort direction of milestone does not
        # affect the sort direction of the bug ID.
        return sorted(self.bugtasks, key=lambda bugtask: bugtask.importance)


class DistributionTarget(BugTargetTestBase, ProductAndDistributionTests,
                         BugTargetWithBugSuperVisor,
                         ProjectGroupAndDistributionTests):
    """Use a distribution as the bug target."""

    def setUp(self):
        super(DistributionTarget, self).setUp()
        self.group_on = (BugSummary.distribution_id,)
        self.searchtarget = self.factory.makeDistribution()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeDistribution()
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)

    def setBugParamsTarget(self, params, target):
        params.setDistribution(target)

    def makeSeries(self):
        """See `ProductAndDistributionTests`."""
        return self.factory.makeDistroSeries(distribution=self.searchtarget)

    def setUpStructuralSubscriptions(self):
        # See `ProjectGroupAndDistributionTests`.
        subscriber = self.factory.makePerson()
        sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=self.searchtarget)
        self.bugtasks.append(self.factory.makeBugTask(target=sourcepackage))
        self.subscribeToTarget(subscriber)
        with person_logged_in(subscriber):
            sourcepackage.addSubscription(
                subscriber, subscribed_by=subscriber)
        return subscriber

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                distribution=self.searchtarget, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                distribution=self.searchtarget, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


class DistroseriesTarget(BugTargetTestBase):
    """Use a distro series as the bug target."""

    def setUp(self):
        super(DistroseriesTarget, self).setUp()
        self.group_on = (BugSummary.distroseries_id,)
        self.searchtarget = self.factory.makeDistroSeries()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeDistroSeries(
            distribution=self.searchtarget.distribution)
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2, owner=self.searchtarget2.owner)

    def setBugParamsTarget(self, params, target):
        params.setDistroSeries(target)

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                distribution=self.searchtarget.distribution, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                distribution=self.searchtarget.distribution, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


class SourcePackageTarget(BugTargetTestBase):
    """Use a source package as the bug target."""

    def setUp(self):
        super(SourcePackageTarget, self).setUp()
        self.group_on = (BugSummary.sourcepackagename_id,)
        self.searchtarget = self.factory.makeSourcePackage()
        self.owner = self.searchtarget.distroseries.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeSourcePackage(
            distroseries=self.searchtarget.distroseries)
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2,
            owner=self.searchtarget2.distroseries.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2,
            owner=self.searchtarget2.distroseries.owner)

    def setBugParamsTarget(self, params, target):
        params.setSourcePackage(target)

    def subscribeToTarget(self, subscriber):
        # Subscribe the given person to the search target.
        # Source packages do not support structural subscriptions,
        # so we subscribe to the distro series instead.
        with person_logged_in(subscriber):
            self.searchtarget.distroseries.addSubscription(
                subscriber, subscribed_by=subscriber)

    def targetToGroup(self, target):
        return target.sourcepackagename.id

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                distribution=self.searchtarget.distribution, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                distribution=self.searchtarget.distribution, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


class DistributionSourcePackageTarget(BugTargetTestBase,
                                      BugTargetWithBugSuperVisor):
    """Use a distribution source package as the bug target."""

    def setUp(self):
        super(DistributionSourcePackageTarget, self).setUp()
        self.group_on = (BugSummary.sourcepackagename_id,)
        self.searchtarget = self.factory.makeDistributionSourcePackage()
        self.owner = self.searchtarget.distribution.owner
        self.makeBugTasks()

    def setUpTarget2(self):
        self.searchtarget2 = self.factory.makeDistributionSourcePackage(
            distribution=self.searchtarget.distribution)
        self.bugtasks2 = []
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2,
            owner=self.searchtarget2.distribution.owner)
        self.makeBugTasks(bugtarget=self.searchtarget2,
            bugtasks=self.bugtasks2,
            owner=self.searchtarget2.distribution.owner)

    def setBugParamsTarget(self, params, target):
        params.setSourcePackage(target)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task target."""
        with person_logged_in(self.owner):
            self.searchtarget.distribution.setBugSupervisor(
                supervisor, self.owner)

    def targetToGroup(self, target):
        return target.sourcepackagename.id

    def setUpMilestoneSorting(self):
        with person_logged_in(self.owner):
            milestone_1 = self.factory.makeMilestone(
                distribution=self.searchtarget.distribution, name='1.0')
            milestone_2 = self.factory.makeMilestone(
                distribution=self.searchtarget.distribution, name='2.0')
            self.bugtasks[1].transitionToMilestone(milestone_1, self.owner)
            self.bugtasks[2].transitionToMilestone(milestone_2, self.owner)
        return self.bugtasks[1:] + self.bugtasks[:1]


bug_targets_mixins = (
    DistributionTarget,
    DistributionSourcePackageTarget,
    DistroseriesTarget,
    MilestoneTarget,
    ProductSeriesTarget,
    ProductTarget,
    ProjectGroupTarget,
    SourcePackageTarget,
    )


class MultipleParams:
    """A mixin class for tests with more than one search parameter object.

    BugTaskSet.search() can be called with more than one
    BugTaskSearchParams instances, while BugTaskSet.searchBugIds()
    accepts exactly one instance.
    """

    def test_two_param_objects(self):
        # We can pass more than one BugTaskSearchParams instance to
        # BugTaskSet.search().
        params1 = self.getBugTaskSearchParams(
            user=None, status=BugTaskStatus.FIXCOMMITTED)
        subscriber = self.factory.makePerson()
        self.subscribeToTarget(subscriber)
        params2 = self.getBugTaskSearchParams(
            user=None, status=BugTaskStatus.NEW,
            structural_subscriber=subscriber)
        search_result = self.runSearch(params1, params2)
        expected = self.resultValuesForBugtasks(self.bugtasks[1:])
        self.assertEqual(expected, search_result)


class PreloadBugtaskTargets(MultipleParams):
    """Preload bug targets during a BugTaskSet.search() query."""

    def runSearch(self, params, *args, **kw):
        """Run BugTaskSet.search() and preload bugtask target objects."""
        return list(self.bugtask_set.search(
            params, *args, _noprejoins=False, **kw))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return expected_bugtasks

    def test_preload_additional_objects(self):
        # It is possible to join additional tables in the search query
        # in order to load related Storm objects during the query.
        store = Store.of(self.bugtasks[0])
        store.invalidate()

        # If we do not prejoin the owner, two queries a run
        # in order to retrieve the owner of the bugtask.
        with StormStatementRecorder() as recorder:
            params = self.getBugTaskSearchParams(user=None)
            found_tasks = self.runSearch(params)
            found_tasks[0].owner
            self.assertTrue(len(recorder.statements) > 1)

        # If we join the table person on bugtask.owner == person.id
        # the owner object is loaded in the query that retrieves the
        # bugtasks.
        store.invalidate()
        with StormStatementRecorder() as recorder:
            params = self.getBugTaskSearchParams(user=None)
            found_tasks = self.runSearch(
                params,
                prejoins=[(Person, Join(Person, BugTask.owner == Person.id))])
            # More than one query may have been performed
            search_count = recorder.count
            # Accessing the owner does not trigger more queries.
            found_tasks[0].owner
            self.assertThat(recorder, HasQueryCount(Equals(search_count)))


class NoPreloadBugtaskTargets(MultipleParams):
    """Do not preload bug targets during a BugTaskSet.search() query."""

    def runSearch(self, params, *args):
        """Run BugTaskSet.search() without preloading bugtask targets."""
        return list(self.bugtask_set.search(params, *args, _noprejoins=True))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return expected_bugtasks


class QueryBugIDs:
    """Search bug IDs."""

    def runSearch(self, params, *args):
        """Run BugTaskSet.searchBugIds()."""
        return list(self.bugtask_set.searchBugIds(params))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return [bugtask.bug.id for bugtask in expected_bugtasks]


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for bug_target_search_type_class in (
        PreloadBugtaskTargets, NoPreloadBugtaskTargets, QueryBugIDs):
        for target_mixin in bug_targets_mixins:
            class_name = 'Test%s%s' % (
                bug_target_search_type_class.__name__,
                target_mixin.__name__)
            class_bases = (
                target_mixin, bug_target_search_type_class,
                SearchTestBase, TestCaseWithFactory)
            # Dynamically build a test class from the target mixin class,
            # from the search type mixin class, from the mixin class
            # having all tests and from a unit test base class.
            test_class = type(class_name, class_bases, {})
            # Add the new unit test class to the suite.
            suite.addTest(loader.loadTestsFromTestCase(test_class))
    suite.addTest(loader.loadTestsFromName(__name__))
    return suite
