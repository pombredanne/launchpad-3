# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from new import classobj
import sys
import unittest

from zope.component import getUtility

from canonical.launchpad.searchbuilder import any
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    )

from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.interfaces.bugattachment import BugAttachmentType
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class SearchTestBase:
    """A mixin class with tests useful for all targets and search variants."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(SearchTestBase, self).setUp()
        self.bugtask_set = getUtility(IBugTaskSet)

    def test_search_all_bugtasks_for_target(self):
        # BugTaskSet.search() returns all bug tasks for a given bug
        # target, if only the bug target is passed as a search parameter.
        params = self.getBugTaskSearchParams(user=None)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)

    def test_private_bug_in_search_result(self):
        # Private bugs are not included in search results for anonymous users.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        params = self.getBugTaskSearchParams(user=None)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)[:-1]
        self.assertEqual(expected, search_result)

        # Private bugs are not included in search results for ordinary users.
        user = self.factory.makePerson()
        params = self.getBugTaskSearchParams(user=user)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)[:-1]
        self.assertEqual(expected, search_result)

        # If the user is subscribed to the bug, it is included in the
        # search result.
        user = self.factory.makePerson()
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.subscribe(user, self.owner)
        params = self.getBugTaskSearchParams(user=user)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)

        # Private bugs are included in search results for admins.
        admin = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        params = self.getBugTaskSearchParams(user=admin)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)

    def test_search_by_bug_reporter(self):
        # Search results can be limited to bugs filed by a given person.
        bugtask = self.bugtasks[0]
        reporter = bugtask.bug.owner
        params = self.getBugTaskSearchParams(
            user=None, bug_reporter=reporter)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks([bugtask])
        self.assertEqual(expected, search_result)

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
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks([expected])
        self.assertEqual(expected, search_result)

    def test_search_by_person_affected_by_bug(self):
        # Search results can be limited to bugs which affect a given person.
        affected_user = self.factory.makePerson()
        expected = self.bugtasks[0]
        with person_logged_in(affected_user):
            expected.bug.markUserAffected(affected_user)
        params = self.getBugTaskSearchParams(
            user=None, affected_user=affected_user)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks([expected])
        self.assertEqual(expected, search_result)

    def test_search_by_bugtask_assignee(self):
        # Search results can be limited to bugtask assigned to a given
        # person.
        assignee = self.factory.makePerson()
        expected = self.bugtasks[0]
        with person_logged_in(assignee):
            expected.transitionToAssignee(assignee)
        params = self.getBugTaskSearchParams(user=None, assignee=assignee)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks([expected])
        self.assertEqual(expected, search_result)

    def test_search_by_bug_subscriber(self):
        # Search results can be limited to bugs to which a given person
        # is subscribed.
        subscriber = self.factory.makePerson()
        expected = self.bugtasks[0]
        with person_logged_in(subscriber):
            expected.bug.subscribe(subscriber, subscribed_by=subscriber)
        params = self.getBugTaskSearchParams(user=None, subscriber=subscriber)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks([expected])
        self.assertEqual(expected, search_result)

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
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks[:1])
        self.assertEqual(expected, search_result)
        # ... for bugs with patches...
        params = self.getBugTaskSearchParams(
            user=None, attachmenttype=BugAttachmentType.PATCH)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks[1:2])
        self.assertEqual(expected, search_result)
        # and for bugs with patches or attachments
        params = self.getBugTaskSearchParams(
            user=None, attachmenttype=any(
                BugAttachmentType.PATCH,
                BugAttachmentType.UNSPECIFIED))
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks[:2])
        self.assertEqual(expected, search_result)

    def setUpSearchTests(self):
        # Set text fields indexed by Bug.fti, BugTask.fti or
        # MessageChunk.fti to values we can search for.
        for bugtask, number in zip(self.bugtasks, ('one', 'two', 'three')):
            commenter = self.bugtasks[0].bug.owner
            with person_logged_in(commenter):
                bugtask.statusexplanation = 'status explanation %s' % number
                bugtask.bug.title = 'bug title %s' % number
                bugtask.bug.newMessage(
                    owner=commenter, content='comment %s' % number)

    def test_fulltext_search(self):
        # Full text searches find text indexed by Bug.fti...
        self.setUpSearchTests()
        params = self.getBugTaskSearchParams(user=None, searchtext='one title')
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks[:1])
        self.assertEqual(expected, search_result)
        # ... by BugTask.fti ...
        params = self.getBugTaskSearchParams(
            user=None, searchtext='one explanation')
        search_result = self.runSearch(params)
        self.assertEqual(expected, search_result)
        # ...and by MessageChunk.fti
        params = self.getBugTaskSearchParams(
            user=None, searchtext='one comment')
        search_result = self.runSearch(params)
        self.assertEqual(expected, search_result)

    def test_fast_fulltext_search(self):
        # Fast full text searches find text indexed by Bug.fti...
        self.setUpSearchTests()
        params = self.getBugTaskSearchParams(
            user=None, fast_searchtext='one title')
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks[:1])
        self.assertEqual(expected, search_result)
        # ... but not text indexed by BugTask.fti ...
        params = self.getBugTaskSearchParams(
            user=None, fast_searchtext='one explanation')
        search_result = self.runSearch(params)
        self.assertEqual([], search_result)
        # ..or by MessageChunk.fti
        params = self.getBugTaskSearchParams(
            user=None, fast_searchtext='one comment')
        search_result = self.runSearch(params)
        self.assertEqual([], search_result)

    def test_has_no_upstream_bugtask(self):
        # Search results can be limited to bugtasks of bugs that do
        # not have a related upstream task.
        #
        bug = self.makeBugWithOneTarget()

        params = self.getBugTaskSearchParams(
            user=None, has_no_upstream_bugtask=True)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)


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
        params = self.getBugTaskSearchParams(
            user=None, nominated_for=series1)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks[:1])
        self.assertEqual(expected, search_result)


class BugTargetTestBase:
    """A base class for the bug target mixin classes."""

    def makeBugTasks(self, bugtarget):
        self.bugtasks = []
        with person_logged_in(self.owner):
            assert(bug.default_bugtask.target == bugtarget)
            self.bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            self.bugtasks[-1].importance = BugTaskImportance.HIGH
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.TRIAGED, self.owner)

            self.bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            self.bugtasks[-1].importance = BugTaskImportance.LOW
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.NEW, self.owner)

            self.bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            self.bugtasks[-1].importance = BugTaskImportance.CRITICAL
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.owner)


class BugTargetWithBugSuperVisor:
    """A base class for bug targets which have a bug supervisor."""

    def test_search_by_bug_supervisor(self):
        # We can search for bugs by bug supervisor.
        # We have by default no bug supervisor set, so searching for
        # bugs by supervisor returns no data.
        supervisor = self.factory.makeTeam(owner=self.owner)
        params = self.getBugTaskSearchParams(
            user=None, bug_supervisor=supervisor)
        search_result = self.runSearch(params)
        self.assertEqual([], search_result)

        # If we appoint a bug supervisor, searching for bug tasks
        # by supervisor will return all bugs for our test target.
        self.setSupervisor(supervisor)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task target."""
        with person_logged_in(self.owner):
            self.searchtarget.setBugSupervisor(supervisor, self.owner)


class ProductTarget(BugTargetTestBase, ProductAndDistributionTests,
                    BugTargetWithBugSuperVisor):
    """Use a product as the bug target."""

    def setUp(self):
        super(ProductTarget, self).setUp()
        self.searchtarget = self.factory.makeProduct()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setProduct(self.searchtarget)
        return params

    def makeSeries(self):
        """See `ProductAndDistributionTests`."""
        return self.factory.makeProductSeries(product=self.searchtarget)


class ProductSeriesTarget(BugTargetTestBase):
    """Use a product series as the bug target."""

    def setUp(self):
        super(ProductSeriesTarget, self).setUp()
        self.searchtarget = self.factory.makeProductSeries()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setProductSeries(self.searchtarget)
        return params


class ProjectGroupTarget(BugTargetTestBase, BugTargetWithBugSuperVisor):
    """Use a project group as the bug target."""

    def setUp(self):
        super(ProjectGroupTarget, self).setUp()
        self.searchtarget = self.factory.makeProject()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setProject(self.searchtarget)
        return params

    def makeBugTasks(self):
        """Create bug tasks for the search target."""
        self.bugtasks = []
        with person_logged_in(self.owner):
            product = self.factory.makeProduct(owner=self.owner)
            product.project = self.searchtarget
            self.bugtasks.append(
                self.factory.makeBugTask(target=product))
            self.bugtasks[-1].importance = BugTaskImportance.HIGH
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.TRIAGED, self.owner)

            product = self.factory.makeProduct(owner=self.owner)
            product.project = self.searchtarget
            self.bugtasks.append(
                self.factory.makeBugTask(target=product))
            self.bugtasks[-1].importance = BugTaskImportance.LOW
            self.bugtasks[-1].transitionToStatus(
            BugTaskStatus.NEW, self.owner)

            product = self.factory.makeProduct(owner=self.owner)
            product.project = self.searchtarget
            self.bugtasks.append(
                self.factory.makeBugTask(target=product))
            self.bugtasks[-1].importance = BugTaskImportance.CRITICAL
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.owner)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task targets."""
        with person_logged_in(self.owner):
            # We must set the bug supervisor for each bug task target
            for bugtask in self.bugtasks:
                bugtask.target.setBugSupervisor(supervisor, self.owner)


class MilestoneTarget(BugTargetTestBase):
    """Use a milestone as the bug target."""

    def setUp(self):
        super(MilestoneTarget, self).setUp()
        self.product = self.factory.makeProduct()
        self.searchtarget = self.factory.makeMilestone(product=self.product)
        self.owner = self.product.owner
        self.makeBugTasks(self.product)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(milestone=self.searchtarget, *args, **kw)
        return params

    def makeBugTasks(self, bugtarget):
        """Create bug tasks for a product and assign them to a milestone."""
        super(MilestoneTarget, self).makeBugTasks(bugtarget)
        with person_logged_in(self.owner):
            for bugtask in self.bugtasks:
                bugtask.transitionToMilestone(self.searchtarget, self.owner)


class DistributionTarget(BugTargetTestBase, ProductAndDistributionTests,
                         BugTargetWithBugSuperVisor):
    """Use a distribution as the bug target."""

    def setUp(self):
        super(DistributionTarget, self).setUp()
        self.searchtarget = self.factory.makeDistribution()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setDistribution(self.searchtarget)
        return params

    def makeSeries(self):
        """See `ProductAndDistributionTests`."""
        return self.factory.makeDistroSeries(distribution=self.searchtarget)


class DistroseriesTarget(BugTargetTestBase):
    """Use a distro series as the bug target."""

    def setUp(self):
        super(DistroseriesTarget, self).setUp()
        self.searchtarget = self.factory.makeDistroSeries()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setDistroSeries(self.searchtarget)
        return params


class SourcePackageTarget(BugTargetTestBase):
    """Use a source package as the bug target."""

    def setUp(self):
        super(SourcePackageTarget, self).setUp()
        self.searchtarget = self.factory.makeSourcePackage()
        self.owner = self.searchtarget.distroseries.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setSourcePackage(self.searchtarget)
        return params


class DistributionSourcePackageTarget(BugTargetTestBase,
                                      BugTargetWithBugSuperVisor):
    """Use a distribution source package as the bug target."""

    def setUp(self):
        super(DistributionSourcePackageTarget, self).setUp()
        self.searchtarget = self.factory.makeDistributionSourcePackage()
        self.owner = self.searchtarget.distribution.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setSourcePackage(self.searchtarget)
        return params

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task target."""
        with person_logged_in(self.owner):
            self.searchtarget.distribution.setBugSupervisor(
                supervisor, self.owner)


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


class PreloadBugtaskTargets:
    """Preload bug targets during a BugTaskSet.search() query."""

    def setUp(self):
        super(PreloadBugtaskTargets, self).setUp()

    def runSearch(self, params, *args):
        """Run BugTaskSet.search() and preload bugtask target objects."""
        return list(self.bugtask_set.search(params, *args, _noprejoins=False))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return expected_bugtasks


class NoPreloadBugtaskTargets:
    """Do not preload bug targets during a BugTaskSet.search() query."""

    def setUp(self):
        super(NoPreloadBugtaskTargets, self).setUp()

    def runSearch(self, params, *args):
        """Run BugTaskSet.search() without preloading bugtask targets."""
        return list(self.bugtask_set.search(params, *args, _noprejoins=True))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return expected_bugtasks


class QueryBugIDs:
    """Search bug IDs."""

    def setUp(self):
        super(QueryBugIDs, self).setUp()

    def runSearch(self, params, *args):
        """Run BugTaskSet.searchBugIds()."""
        return list(self.bugtask_set.searchBugIds(params))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return [bugtask.bug.id for bugtask in expected_bugtasks]


def test_suite():
    module = sys.modules[__name__]
    for bug_target_search_type_class in (
        PreloadBugtaskTargets, NoPreloadBugtaskTargets, QueryBugIDs):
        for target_mixin in bug_targets_mixins:
            class_name = 'Test%s%s' % (
                bug_target_search_type_class.__name__,
                target_mixin.__name__)
            # Dynamically build a test class from the target mixin class,
            # from the search type mixin class, from the mixin class
            # having all tests and from a unit test base class.
            test_class = classobj(
                class_name,
                (target_mixin, bug_target_search_type_class, SearchTestBase,
                 TestCaseWithFactory),
                {})
            # Add the new unit test class to the module.
            module.__dict__[class_name] = test_class
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite
