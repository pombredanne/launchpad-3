# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running tests agains IBugTarget implementations.

This module runs the interface test against the Product, ProductSeries
ProjectGroup, DistributionSourcePackage, and DistroSeries implementations
IBugTarget. It runs the bugtarget-bugcount.txt, and
bugtarget-questiontarget.txt tests.
"""
# pylint: disable-msg=C0103

__metaclass__ = type

__all__ = []

import random
from testtools.matchers import Equals
import unittest

from storm.expr import LeftJoin
from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.bugs.model.bugtask import BugTask
from lp.registry.interfaces.distribution import (
    IDistribution,
    IDistributionSet,
    )
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.projectgroup import IProjectGroupSet
from lp.registry.model.milestone import Milestone
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


def bugtarget_filebug(bugtarget, summary, status=None):
    """File a bug as the current user on the bug target and return it."""
    return bugtarget.createBug(CreateBugParams(
        getUtility(ILaunchBag).user, summary, comment=summary, status=status))


def productSetUp(test):
    """Setup the `IProduct` test."""
    setUp(test)
    test.globs['bugtarget'] = getUtility(IProductSet).getByName('firefox')
    test.globs['filebug'] = bugtarget_filebug
    test.globs['question_target'] = test.globs['bugtarget']


def project_filebug(project, summary, status=None):
    """File a bug on a project.

    Since it's not possible to file a bug on a project directly, the bug
    will be filed on one of its products.
    """
    # It doesn't matter which product the bug is filed on.
    product = random.choice(list(project.products))
    bug = bugtarget_filebug(product, summary, status=status)
    return bug


def projectSetUp(test):
    """Setup the `IProjectGroup` test."""
    setUp(test)
    projectgroups = getUtility(IProjectGroupSet)
    test.globs['bugtarget'] = projectgroups.getByName('mozilla')
    test.globs['filebug'] = project_filebug


def productseries_filebug(productseries, summary, status=None):
    """File a bug on a product series.

    Since it's not possible to file a bug on a product series directly,
    the bug will first be filed on its product, then a series task will
    be created.
    """
    bug = bugtarget_filebug(productseries.product, summary, status=status)
    getUtility(IBugTaskSet).createTask(
        bug, getUtility(ILaunchBag).user, productseries=productseries,
        status=status)
    return bug


def productSeriesSetUp(test):
    """Setup the `IProductSeries` test."""
    setUp(test)
    firefox = getUtility(IProductSet).getByName('firefox')
    test.globs['bugtarget'] = firefox.getSeries('trunk')
    test.globs['filebug'] = productseries_filebug
    test.globs['question_target'] = firefox


def distributionSetUp(test):
    """Setup the `IDistribution` test."""
    setUp(test)
    test.globs['bugtarget'] = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['filebug'] = bugtarget_filebug
    test.globs['question_target'] = test.globs['bugtarget']


def distributionSourcePackageSetUp(test):
    """Setup the `IDistributionSourcePackage` test."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['bugtarget'] = ubuntu.getSourcePackage('mozilla-firefox')
    test.globs['filebug'] = bugtarget_filebug
    test.globs['question_target'] = test.globs['bugtarget']


def distroseries_filebug(distroseries, summary, sourcepackagename=None,
                          status=None):
    """File a bug on a distroseries.

    Since bugs can't be filed on distroseriess directly, a bug will
    first be filed on its distribution, and then a series task will be
    added.
    """
    bug = bugtarget_filebug(distroseries.distribution, summary, status=status)
    getUtility(IBugTaskSet).createTask(
        bug, getUtility(ILaunchBag).user, distroseries=distroseries,
        sourcepackagename=sourcepackagename, status=status)
    return bug


def distributionSeriesSetUp(test):
    """Setup the `IDistroSeries` test."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['bugtarget'] = ubuntu.getSeries('hoary')
    test.globs['filebug'] = distroseries_filebug
    test.globs['question_target'] = ubuntu


def sourcepackage_filebug(source_package, summary, status=None):
    """File a bug on a source package in a distroseries."""
    bug = distroseries_filebug(
        source_package.distroseries, summary,
        sourcepackagename=source_package.sourcepackagename, status=status)
    return bug


def sourcepackage_filebug_for_question(source_package, summary, status=None):
    """Setup a bug with only one BugTask that can provide a QuestionTarget."""
    bug = sourcepackage_filebug(source_package, summary, status=status)
    # The distribution bugtask interferes with bugtarget-questiontarget.txt.
    for bugtask in bug.bugtasks:
        if IDistribution.providedBy(bugtask.target):
            bugtask.transitionToStatus(
                BugTaskStatus.INVALID, getUtility(ILaunchBag).user)
    return bug


def sourcePackageSetUp(test):
    """Setup the `ISourcePackage` test."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    warty = ubuntu.getSeries('warty')
    test.globs['bugtarget'] = warty.getSourcePackage('mozilla-firefox')
    test.globs['filebug'] = sourcepackage_filebug
    test.globs['question_target'] = ubuntu.getSourcePackage('mozilla-firefox')


def sourcePackageForQuestionSetUp(test):
    """Setup the `ISourcePackage` test for QuestionTarget testing."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    warty = ubuntu.getSeries('warty')
    test.globs['bugtarget'] = warty.getSourcePackage('mozilla-firefox')
    test.globs['filebug'] = sourcepackage_filebug_for_question
    test.globs['question_target'] = ubuntu.getSourcePackage('mozilla-firefox')


class TestBugTargetSearchTasks(TestCaseWithFactory):
    """Tests of IHasBugs.searchTasks()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTargetSearchTasks, self).setUp()
        self.bug = self.factory.makeBug()
        self.target = self.bug.default_bugtask.target
        self.milestone = self.factory.makeMilestone(product=self.target)
        with person_logged_in(self.target.owner):
            self.bug.default_bugtask.transitionToMilestone(
                self.milestone, self.target.owner)
        self.store = Store.of(self.bug)
        self.store.flush()
        self.store.invalidate()

    def test_preload_other_objects(self):
        # We can prejoin objects in calls of searchTasks().

        # Without prejoining the table Milestone, accessing the
        # BugTask property milestone requires an extra query.
        with StormStatementRecorder() as recorder:
            params = BugTaskSearchParams(user=None)
            found_tasks = self.target.searchTasks(params)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(2)))

        # When we prejoin Milestone, the milestone of our bugtask is
        # already loaded during the main search query.
        self.store.invalidate()
        with StormStatementRecorder() as recorder:
            params = BugTaskSearchParams(user=None)
            prejoins = [(Milestone,
                         LeftJoin(Milestone,
                                  BugTask.milestone == Milestone.id))]
            found_tasks = self.target.searchTasks(params, prejoins=prejoins)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_preload_other_objects_for_person_search_no_params_passed(self):
        # We can prejoin objects in calls of Person.searchTasks().
        owner = self.bug.owner
        with StormStatementRecorder() as recorder:
            found_tasks = owner.searchTasks(None, user=None)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(2)))

        self.store.invalidate()
        with StormStatementRecorder() as recorder:
            prejoins = [(Milestone,
                         LeftJoin(Milestone,
                                  BugTask.milestone == Milestone.id))]
            found_tasks = owner.searchTasks(
                None, user=None, prejoins=prejoins)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_preload_other_objects_for_person_search_no_keywords_passed(self):
        # We can prejoin objects in calls of Person.searchTasks().
        owner = self.bug.owner
        params = BugTaskSearchParams(user=None, owner=owner)
        with StormStatementRecorder() as recorder:
            found_tasks = owner.searchTasks(params)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(2)))

        self.store.invalidate()
        with StormStatementRecorder() as recorder:
            prejoins = [(Milestone,
                         LeftJoin(Milestone,
                                  BugTask.milestone == Milestone.id))]
            found_tasks = owner.searchTasks(params, prejoins=prejoins)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_preload_other_objects_for_person_search_keywords_passed(self):
        # We can prejoin objects in calls of Person.searchTasks().
        owner = self.bug.owner
        params = BugTaskSearchParams(user=None, owner=owner)
        with StormStatementRecorder() as recorder:
            found_tasks = owner.searchTasks(params, order_by=BugTask.id)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(2)))

        self.store.invalidate()
        with StormStatementRecorder() as recorder:
            prejoins = [(Milestone,
                         LeftJoin(Milestone,
                                  BugTask.milestone == Milestone.id))]
            found_tasks = owner.searchTasks(params, prejoins=prejoins)
            found_tasks[0].milestone
        self.assertThat(recorder, HasQueryCount(Equals(1)))


def test_suite():
    """Return the `IBugTarget` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        productSeriesSetUp,
        distributionSetUp,
        distributionSourcePackageSetUp,
        distributionSeriesSetUp,
        sourcePackageForQuestionSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = LayeredDocFileSuite('bugtarget-questiontarget.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=DatabaseFunctionalLayer)
        suite.addTest(test)

    setUpMethods.remove(sourcePackageForQuestionSetUp)
    setUpMethods.append(sourcePackageSetUp)
    setUpMethods.append(projectSetUp)

    for setUpMethod in setUpMethods:
        test = LayeredDocFileSuite('bugtarget-bugcount.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=DatabaseFunctionalLayer)
        suite.addTest(test)

    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite
