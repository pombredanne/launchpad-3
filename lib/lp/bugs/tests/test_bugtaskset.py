# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTaskSet."""

__metaclass__ = type

import datetime
import subprocess
import transaction
from collections import namedtuple
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from operator import attrgetter
from storm.store import Store
from testtools.testcase import ExpectedException
from zope.component import getUtility
from zope.event import notify
from zope.security.interfaces import Unauthorized
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    BugTaskStatusSearch,
    IBugTaskSet,
    UserCannotEditBugTaskImportance,
    UserCannotEditBugTaskMilestone,
    )
from lp.bugs.interfaces.bug import (
    CreateBugParams,
    IBug,
    IBugSet,
    )
from lp.bugs.scripts.bugtasktargetnamecaches import (
    BugTaskTargetNameCacheUpdater)
from lp.registry.enums import InformationType
from lp.registry.interfaces.accesspolicy import (
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.distributionsourcepackage \
    import IDistributionSourcePackage
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.model.sourcepackage import SourcePackage
from lp.services.database.sqlbase import (
    flush_database_caches,
    flush_database_updates,
    )
from lp.services.log.logger import FakeLogger
from lp.services.searchbuilder import any
from lp.services.webapp.interfaces import ILaunchBag
from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


def login_foobar():
    """Helper to get the foobar logged in user"""
    launchbag = getUtility(ILaunchBag)
    login('foo.bar@canonical.com')
    return launchbag.user


def login_nopriv():
    launchbag = getUtility(ILaunchBag)
    login("no-priv@canonical.com")
    return launchbag.user


class TestBugTaskCreation(TestCaseWithFactory):
    """Test BugTaskSet creation methods."""

    layer = DatabaseFunctionalLayer

    def test_upstream_task(self):
        """A bug that has to be fixed in an upstream product."""
        bugtaskset = getUtility(IBugTaskSet)
        bug_one = getUtility(IBugSet).get(1)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')
        evolution = getUtility(IProductSet).get(5)

        upstream_task = bugtaskset.createTask(
            bug_one, mark, evolution,
            status=BugTaskStatus.NEW,
            importance=BugTaskImportance.MEDIUM)

        self.assertEqual(upstream_task.product, evolution)
        self.assertEqual(upstream_task.target, evolution)
        # getPackageComponent only applies to tasks that specify package info.
        self.assertEqual(upstream_task.getPackageComponent(), None)

    def test_distro_specific_bug(self):
        """A bug that needs to be fixed in a specific distro."""
        bugtaskset = getUtility(IBugTaskSet)
        bug_one = getUtility(IBugSet).get(1)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')

        a_distro = self.factory.makeDistribution(name='tubuntu')
        distro_task = bugtaskset.createTask(
            bug_one, mark, a_distro,
            status=BugTaskStatus.NEW,
            importance=BugTaskImportance.MEDIUM)

        self.assertEqual(distro_task.distribution, a_distro)
        self.assertEqual(distro_task.target, a_distro)
        # getPackageComponent only applies to tasks that specify package info.
        self.assertEqual(distro_task.getPackageComponent(), None)

    def test_distroseries_specific_bug(self):
        """A bug that needs to be fixed in a specific distro series

        These tasks are used for release management and backporting
        """
        bugtaskset = getUtility(IBugTaskSet)
        bug_one = getUtility(IBugSet).get(1)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')
        warty = getUtility(IDistroSeriesSet).get(1)

        distro_series_task = bugtaskset.createTask(
            bug_one, mark, warty,
            status=BugTaskStatus.NEW, importance=BugTaskImportance.MEDIUM)

        self.assertEqual(distro_series_task.distroseries, warty)
        self.assertEqual(distro_series_task.target, warty)
        # getPackageComponent only applies to tasks that specify package info.
        self.assertEqual(distro_series_task.getPackageComponent(), None)

    def test_createmany_bugtasks(self):
        """We can create a set of bugtasks around different targets"""
        bugtaskset = getUtility(IBugTaskSet)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')
        evolution = getUtility(IProductSet).get(5)
        warty = getUtility(IDistroSeriesSet).get(1)
        bug_many = getUtility(IBugSet).get(4)

        a_distro = self.factory.makeDistribution(name='tubuntu')
        taskset = bugtaskset.createManyTasks(bug_many, mark,
            [evolution, a_distro, warty], status=BugTaskStatus.FIXRELEASED)
        tasks = [(t.product, t.distribution, t.distroseries) for t in taskset]
        tasks.sort()

        self.assertEqual(tasks[0][2], warty)
        self.assertEqual(tasks[1][1], a_distro)
        self.assertEqual(tasks[2][0], evolution)


class TestBugTaskTargets(TestCase):
    """Verify we handle various bugtask targets correctly"""

    layer = DatabaseFunctionalLayer

    def test_bugtask_target_productseries(self):
        """The 'target' of a task can be a product series"""
        login('foo.bar@canonical.com')
        bugtaskset = getUtility(IBugTaskSet)
        productset = getUtility(IProductSet)
        bug_one = getUtility(IBugSet).get(1)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')

        firefox = productset['firefox']
        firefox_1_0 = firefox.getSeries("1.0")
        productseries_task = bugtaskset.createTask(bug_one, mark, firefox_1_0)

        self.assertEqual(productseries_task.target, firefox_1_0)
        # getPackageComponent only applies to tasks that specify package info.
        self.assertEqual(productseries_task.getPackageComponent(), None)

    def test_bugtask_target_distro_sourcepackage(self):
        """The 'target' of a task can be a distro sourcepackage"""
        login('foo.bar@canonical.com')
        bugtaskset = getUtility(IBugTaskSet)

        debian_ff_task = bugtaskset.get(4)
        self.assertTrue(
            IDistributionSourcePackage.providedBy(debian_ff_task.target))
        self.assertEqual(debian_ff_task.getPackageComponent(), None)

        target = debian_ff_task.target
        self.assertEqual(target.distribution.name, u'debian')
        self.assertEqual(target.sourcepackagename.name, u'mozilla-firefox')

        ubuntu_linux_task = bugtaskset.get(25)
        self.assertTrue(
            IDistributionSourcePackage.providedBy(ubuntu_linux_task.target))
        self.assertEqual(ubuntu_linux_task.getPackageComponent().name, 'main')

        target = ubuntu_linux_task.target
        self.assertEqual(target.distribution.name, u'ubuntu')
        self.assertEqual(target.sourcepackagename.name, u'linux-source-2.6.15')

    def test_bugtask_target_distroseries_sourcepackage(self):
        """The 'target' of a task can be a distroseries sourcepackage"""
        login('foo.bar@canonical.com')
        bugtaskset = getUtility(IBugTaskSet)
        distro_series_sp_task = bugtaskset.get(16)

        self.assertEqual(distro_series_sp_task.getPackageComponent().name,
            'main')

        expected_target = SourcePackage(
            distroseries=distro_series_sp_task.distroseries,
            sourcepackagename=distro_series_sp_task.sourcepackagename)
        got_target = distro_series_sp_task.target
        self.assertTrue(
            ISourcePackage.providedBy(distro_series_sp_task.target))
        self.assertEqual(got_target.distroseries,
            expected_target.distroseries)
        self.assertEqual(got_target.sourcepackagename,
            expected_target.sourcepackagename)


class TestBugTaskTargetName(TestCase):
    """Verify our targetdisplayname and targetname are correct."""

    layer = DatabaseFunctionalLayer

    def test_targetname_distribution(self):
        """The distribution name will be concat'd"""
        login('foo.bar@canonical.com')
        bugtaskset = getUtility(IBugTaskSet)
        bugtask = bugtaskset.get(17)

        self.assertEqual(bugtask.bugtargetdisplayname,
            u'mozilla-firefox (Ubuntu)')
        self.assertEqual(bugtask.bugtargetname,
            u'mozilla-firefox (Ubuntu)')

    def test_targetname_series_product(self):
        """The targetname for distro series/product versions will be name of
        source package or binary package. """
        login('foo.bar@canonical.com')
        bugtaskset = getUtility(IBugTaskSet)
        bugtask = bugtaskset.get(2)

        self.assertEqual(bugtask.bugtargetdisplayname, u'Mozilla Firefox')
        self.assertEqual(bugtask.bugtargetname, u'firefox')


class TestEditingBugTask(TestCase):
    """Verify out editing functionality of bugtasks."""

    layer = DatabaseFunctionalLayer

    def test_edit_upstream(self):
        """You cannot edit upstream tasks as ANONYMOUS"""
        login('foo.bar@canonical.com')
        bugtaskset = getUtility(IBugTaskSet)
        bug_one = getUtility(IBugSet).get(1)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')

        evolution = getUtility(IProductSet).get(5)
        upstream_task = bugtaskset.createTask(
            bug_one, mark, evolution,
            status=BugTaskStatus.NEW,
            importance=BugTaskImportance.MEDIUM)

        # An anonymous user cannot edit the bugtask.
        login(ANONYMOUS)
        with ExpectedException(Unauthorized, ''):
            upstream_task.transitionToStatus(
                BugTaskStatus.CONFIRMED, getUtility(ILaunchBag.user))

        # A logged in user can edit the upstream bugtask.
        login('jeff.waugh@ubuntulinux.com')
        upstream_task.transitionToStatus(
            BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user)

    def test_edit_distro_bugtasks(self):
        """Any logged-in user can edit tasks filed on distros

        However not if the bug is not marked private.
        So, as an anonymous user, we cannot edit anything:
        """
        login(ANONYMOUS)

        bugtaskset = getUtility(IBugTaskSet)
        distro_task = bugtaskset.get(25)

        # Anonymous cannot change the status.
        with ExpectedException(Unauthorized, ''):
            distro_task.transitionToStatus(
            BugTaskStatus.FIXRELEASED,
            getUtility(ILaunchBag).user)

        # Anonymous cannot change the assignee.
        sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        with ExpectedException(Unauthorized, ''):
            distro_task.transitionToAssignee(sample_person)

        login('test@canonical.com')

        distro_task.transitionToStatus(
            BugTaskStatus.FIXRELEASED,
            getUtility(ILaunchBag).user)
        distro_task.transitionToAssignee(sample_person)


class TestConjoinedBugTasks(TestCase):
    """Current distro dev series bugtasks are kept in sync.

    They represent the same piece of work. The same is true for product and
    productseries tasks, when the productseries task is targeted to the
    IProduct.developmentfocus. The following attributes are synced:

    * status
    * assignee
    * importance
    * milestone
    * sourcepackagename
    * date_confirmed
    * date_inprogress
    * date_assigned
    * date_closed
    * date_left_new
    * date_triaged
    * date_fix_committed
    * date_fix_released

    """

    layer = DatabaseFunctionalLayer

    def _build_ubuntu_netapplet_bug(self):
        """Helper to build buuntu_netapplet_bug"""
        login('test@canonical.com')
        launchbag = getUtility(ILaunchBag)

        BugHelper = namedtuple('BugHelper', ['distro', 'sourcepackage', 'bug'])
        ubuntu = getUtility(IDistributionSet).get(1)
        ubuntu_netapplet = ubuntu.getSourcePackage("netapplet")
        params = CreateBugParams(
            owner=launchbag.user,
            title="a test bug",
            comment="test bug description")
        ubuntu_netapplet_bug = ubuntu_netapplet.createBug(params)
        return BugHelper(ubuntu, ubuntu_netapplet, ubuntu_netapplet_bug)

    def test_conjoined_tasks_sync(self):
        """"""
        login_foobar()
        launchbag = getUtility(ILaunchBag)

        sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')

        ubuntu = getUtility(IDistributionSet).get(1)
        params = CreateBugParams(
            owner=launchbag.user,
            title="a test bug",
            comment="test bug description")
        ubuntu_bug = ubuntu.createBug(params)

        ubuntu_netapplet = ubuntu.getSourcePackage("netapplet")
        ubuntu_netapplet_bug = ubuntu_netapplet.createBug(params)
        generic_netapplet_task = ubuntu_netapplet_bug.bugtasks[0]

        # First, we'll target the bug for the current Ubuntu series, Hoary.
        # Note that the synced attributes are copied when the series-specific
        # tasks are created. We'll set non-default attribute values for each
        # generic task to demonstrate.
        self.assertEqual('hoary', ubuntu.currentseries.name)

        # Only owners, experts, or admins can create a milestone.
        ubuntu_edgy_milestone = ubuntu.currentseries.newMilestone("knot1")

        login('test@canonical.com')
        generic_netapplet_task.transitionToStatus(
            BugTaskStatus.INPROGRESS, getUtility(ILaunchBag).user)
        generic_netapplet_task.transitionToAssignee(sample_person)
        generic_netapplet_task.milestone = ubuntu_edgy_milestone
        generic_netapplet_task.transitionToImportance(
            BugTaskImportance.CRITICAL, ubuntu.owner)

        getUtility(IBugTaskSet).createTask(ubuntu_bug, launchbag.user,
            ubuntu.currentseries)
        current_series_netapplet_task = getUtility(IBugTaskSet).createTask(
            ubuntu_netapplet_bug, launchbag.user,
            ubuntu_netapplet.development_version)

        # The attributes were synced with the generic task.
        self.assertEqual('In Progress',
            current_series_netapplet_task.status.title)
        self.assertEqual('Sample Person',
            current_series_netapplet_task.assignee.displayname)
        self.assertEqual('knot1',
            current_series_netapplet_task.milestone.name)
        self.assertEqual('Critical',
            current_series_netapplet_task.importance.title)

        self.assertEqual(current_series_netapplet_task.date_assigned,
            generic_netapplet_task.date_assigned)
        self.assertEqual(current_series_netapplet_task.date_confirmed,
           generic_netapplet_task.date_confirmed)
        self.assertEqual(current_series_netapplet_task.date_inprogress,
            generic_netapplet_task.date_inprogress)
        self.assertEqual(current_series_netapplet_task.date_closed,
           generic_netapplet_task.date_closed)

        # We'll also add some product and productseries tasks.
        alsa_utils = getUtility(IProductSet)['alsa-utils']
        self.assertEqual('trunk', alsa_utils.development_focus.name)

        # The status attribute is synced.
        self.assertEqual('In Progress', generic_netapplet_task.status.title)
        self.assertEqual('In Progress',
            current_series_netapplet_task.status.title)
        self.assertIsNone(generic_netapplet_task.date_closed)
        self.assertIsNone(current_series_netapplet_task.date_closed)

        current_series_netapplet_task.transitionToStatus(
            BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user)

        self.assertIsInstance(generic_netapplet_task.date_left_new,
            datetime.datetime,)
        self.assertEqual(generic_netapplet_task.date_left_new,
            current_series_netapplet_task.date_left_new)

        self.assertIsInstance(generic_netapplet_task.date_triaged,
            datetime.datetime)
        self.assertEqual(generic_netapplet_task.date_triaged,
            current_series_netapplet_task.date_triaged)

        self.assertIsInstance(generic_netapplet_task.date_fix_committed,
            datetime.datetime)
        self.assertEqual(generic_netapplet_task.date_fix_committed,
            current_series_netapplet_task.date_fix_committed)

        self.assertEqual('Fix Released', generic_netapplet_task.status.title)
        self.assertEqual('Fix Released',
            current_series_netapplet_task.status.title)

        self.assertIsInstance(generic_netapplet_task.date_closed,
            datetime.datetime)
        self.assertEqual(generic_netapplet_task.date_closed,
            current_series_netapplet_task.date_closed)
        self.assertIsInstance(generic_netapplet_task.date_fix_released,
            datetime.datetime)
        self.assertEqual(generic_netapplet_task.date_fix_released,
            current_series_netapplet_task.date_fix_released)

    def test_conjoined_assignee_sync(self):
        """The assignee is synced across conjoined tasks"""
        login('test@canonical.com')
        launchbag = getUtility(ILaunchBag)
        no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')

        data = self._build_ubuntu_netapplet_bug()

        alsa_utils = getUtility(IProductSet)['alsa-utils']
        generic_alsa_utils_task = getUtility(IBugTaskSet).createTask(
            data.bug, launchbag.user, alsa_utils)
        devel_focus_alsa_utils_task = getUtility(IBugTaskSet).createTask(
            data.bug, launchbag.user,
            alsa_utils.getSeries("trunk"))

        self.assertIsNone(generic_alsa_utils_task.assignee)
        self.assertIsNone(devel_focus_alsa_utils_task.assignee)
        self.assertIsNone(generic_alsa_utils_task.date_assigned)
        self.assertIsNone(devel_focus_alsa_utils_task.date_assigned)

        devel_focus_alsa_utils_task.transitionToAssignee(no_priv)

        self.assertEqual('No Privileges Person',
            generic_alsa_utils_task.assignee.displayname)
        self.assertEqual('No Privileges Person',
            devel_focus_alsa_utils_task.assignee.displayname)

        self.assertIsInstance(generic_alsa_utils_task.date_assigned,
            datetime.datetime)
        self.assertEqual(generic_alsa_utils_task.date_assigned,
            devel_focus_alsa_utils_task.date_assigned)

    def test_conjoined_importance_synced(self):
        """The importance is synced across conjoined tasks."""
        login('test@canonical.com')
        launchbag = getUtility(ILaunchBag)
        no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
        data = self._build_ubuntu_netapplet_bug()

        current_series_netapplet_task = getUtility(IBugTaskSet).createTask(
            data.bug, launchbag.user,
            data.sourcepackage.development_version)
        generic_netapplet_task = data.bug.bugtasks[0]
        generic_netapplet_task.transitionToImportance(
            BugTaskImportance.CRITICAL, data.distro.owner)
        self.assertEqual(generic_netapplet_task.importance.title,
            'Critical')
        self.assertEqual(current_series_netapplet_task.importance.title,
            'Critical')

        current_series_netapplet_task.transitionToImportance(
            BugTaskImportance.MEDIUM, data.distro.owner)

        self.assertEqual(generic_netapplet_task.importance.title,
            'Medium')
        self.assertEqual(current_series_netapplet_task.importance.title,
            'Medium')

        # Not everyone can edit the importance, though. If an unauthorised
        # user is passed to transitionToImportance an exception is raised.
        with ExpectedException(UserCannotEditBugTaskImportance, ''):
            current_series_netapplet_task.transitionToImportance(
                BugTaskImportance.LOW, no_priv)
        self.assertEqual(generic_netapplet_task.importance.title, 'Medium')

    def test_conjoined_milestone(self):
        """Milestone attribute will sync across conjoined tasks."""
        data = self._build_ubuntu_netapplet_bug()

        login('foo.bar@canonical.com')
        launchbag = getUtility(ILaunchBag)

        alsa_utils = getUtility(IProductSet)['alsa-utils']
        generic_alsa_utils_task = getUtility(IBugTaskSet).createTask(
            data.bug, launchbag.user, alsa_utils)
        devel_focus_alsa_utils_task = getUtility(IBugTaskSet).createTask(
            data.bug, launchbag.user,
            alsa_utils.getSeries("trunk"))

        test_milestone = alsa_utils.development_focus.newMilestone("test")
        noway_milestone = alsa_utils.development_focus.newMilestone("noway")
        Store.of(test_milestone).flush()

        self.assertIsNone(generic_alsa_utils_task.milestone)
        self.assertIsNone(devel_focus_alsa_utils_task.milestone)

        devel_focus_alsa_utils_task.transitionToMilestone(
            test_milestone, alsa_utils.owner)

        self.assertEqual(generic_alsa_utils_task.milestone.name,
            'test')
        self.assertEqual(devel_focus_alsa_utils_task.milestone.name,
            'test')

        # But a normal unprivileged user can't set the milestone.
        no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
        with ExpectedException(UserCannotEditBugTaskMilestone, ''):
            devel_focus_alsa_utils_task.transitionToMilestone(
                noway_milestone, no_priv)
        self.assertEqual(devel_focus_alsa_utils_task.milestone.name,
            'test')

        devel_focus_alsa_utils_task.transitionToMilestone(
            test_milestone, alsa_utils.owner)

        self.assertEqual(generic_alsa_utils_task.milestone.name,
            'test')
        self.assertEqual(devel_focus_alsa_utils_task.milestone.name,
            'test')

    def test_conjoined_syncs_sourcepackage_name(self):
        """Conjoined tasks will sync source package names."""
        data = self._build_ubuntu_netapplet_bug()
        generic_netapplet_task = data.bug.bugtasks[0]

        login('foo.bar@canonical.com')
        launchbag = getUtility(ILaunchBag)

        ubuntu_pmount = data.distro.getSourcePackage("pmount")
        current_series_netapplet_task = getUtility(IBugTaskSet).createTask(
            data.bug, launchbag.user,
            data.sourcepackage.development_version)

        self.assertEqual(generic_netapplet_task.sourcepackagename.name,
            'netapplet')
        self.assertEqual(current_series_netapplet_task.sourcepackagename.name,
            'netapplet')

        current_series_netapplet_task.transitionToTarget(
            ubuntu_pmount.development_version)

        self.assertEqual(generic_netapplet_task.sourcepackagename.name,
            'pmount')
        self.assertEqual(current_series_netapplet_task.sourcepackagename.name,
            'pmount')

    def test_non_current_dev_lacks_conjoined(self):
        """Tasks not the current dev focus lacks conjoined masters or slaves.
        """
        # Only owners, experts, or admins can create a series.
        login('foo.bar@canonical.com')
        launchbag = getUtility(ILaunchBag)
        ubuntu = getUtility(IDistributionSet).get(1)
        alsa_utils = getUtility(IProductSet)['alsa-utils']
        ubuntu_netapplet = ubuntu.getSourcePackage("netapplet")

        params = CreateBugParams(
            owner=launchbag.user,
            title="a test bug",
            comment="test bug description")
        ubuntu_netapplet_bug = ubuntu_netapplet.createBug(params)

        alsa_utils_stable = alsa_utils.newSeries(
            launchbag.user, 'stable', 'The stable series.')

        login('test@canonical.com')
        Store.of(alsa_utils_stable).flush()
        self.assertNotEqual(alsa_utils.development_focus, alsa_utils_stable)

        stable_netapplet_task = getUtility(IBugTaskSet).createTask(
            ubuntu_netapplet_bug, launchbag.user, alsa_utils_stable)
        self.assertIsNone(stable_netapplet_task.conjoined_master)
        self.assertIsNone(stable_netapplet_task.conjoined_slave)

        warty = ubuntu.getSeries('warty')
        self.assertNotEqual(warty, ubuntu.currentseries)

        warty_netapplet_task = getUtility(IBugTaskSet).createTask(
            ubuntu_netapplet_bug, launchbag.user,
            warty.getSourcePackage(ubuntu_netapplet.sourcepackagename))

        self.assertIsNone(warty_netapplet_task.conjoined_master)
        self.assertIsNone(warty_netapplet_task.conjoined_slave)

    def test_no_conjoined_without_current_series(self):
        """Distributions without current series lack a conjoined master/slave.
        """
        login('foo.bar@canonical.com')
        launchbag = getUtility(ILaunchBag)
        ubuntu = getUtility(IDistributionSet).get(1)
        ubuntu_netapplet = ubuntu.getSourcePackage("netapplet")
        params = CreateBugParams(
            owner=launchbag.user,
            title="a test bug",
            comment="test bug description")
        ubuntu_netapplet_bug = ubuntu_netapplet.createBug(params)

        gentoo = getUtility(IDistributionSet).getByName('gentoo')
        self.assertIsNone(gentoo.currentseries)

        gentoo_netapplet_task = getUtility(IBugTaskSet).createTask(
            ubuntu_netapplet_bug, launchbag.user,
            gentoo.getSourcePackage(ubuntu_netapplet.sourcepackagename))
        self.assertIsNone(gentoo_netapplet_task.conjoined_master)
        self.assertIsNone(gentoo_netapplet_task.conjoined_slave)

    def test_conjoined_broken_relationship(self):
        """A conjoined relationship can be broken, though.

        If the development task (i.e the conjoined master) is Won't Fix, it
        means that the bug is deferred to the next series. In this case the
        development task should be Won't Fix, while the generic task keeps the
        value it had before, allowing it to stay open.
        """
        login('foo.bar@canonical.com')
        launchbag = getUtility(ILaunchBag)
        ubuntu = getUtility(IDistributionSet).get(1)
        params = CreateBugParams(
            owner=launchbag.user,
            title="a test bug",
            comment="test bug description")
        ubuntu_netapplet = ubuntu.getSourcePackage("netapplet")
        ubuntu_netapplet_bug = ubuntu_netapplet.createBug(params)
        generic_netapplet_task = ubuntu_netapplet_bug.bugtasks[0]
        current_series_netapplet_task = getUtility(IBugTaskSet).createTask(
            ubuntu_netapplet_bug, launchbag.user,
            ubuntu_netapplet.development_version)

        # First let's change the status from Fix Released, since it doesn't
        # make sense to reject such a task.
        current_series_netapplet_task.transitionToStatus(
            BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user)
        self.assertEqual(generic_netapplet_task.status.title,
            'Confirmed')
        self.assertEqual(current_series_netapplet_task.status.title,
            'Confirmed')
        self.assertIsNone(generic_netapplet_task.date_closed)
        self.assertIsNone(current_series_netapplet_task.date_closed)

        # Now, if we set the current series task to Won't Fix, the generic task
        # will still be confirmed.
        netapplet_owner = current_series_netapplet_task.pillar.owner
        current_series_netapplet_task.transitionToStatus(
            BugTaskStatus.WONTFIX, netapplet_owner)

        self.assertEqual(generic_netapplet_task.status.title,
            'Confirmed')
        self.assertEqual(current_series_netapplet_task.status.title,
            "Won't Fix")

        self.assertIsNone(generic_netapplet_task.date_closed)
        self.assertIsNotNone(current_series_netapplet_task.date_closed)

        # And the bugtasks are no longer conjoined:
        self.assertIsNone(generic_netapplet_task.conjoined_master)
        self.assertIsNone(current_series_netapplet_task.conjoined_slave)

        # If the current development release is marked as Invalid, then the
        # bug is invalid for all future series too, and so the general bugtask
        # is therefore Invalid also. In other words, conjoined again.

        current_series_netapplet_task.transitionToStatus(
            BugTaskStatus.NEW, getUtility(ILaunchBag).user)

        # XXX Gavin Panella 2007-06-06 bug=112746:
        # We must make two transitions.
        current_series_netapplet_task.transitionToStatus(
            BugTaskStatus.INVALID, getUtility(ILaunchBag).user)

        self.assertEqual(generic_netapplet_task.status.title,
            'Invalid')
        self.assertEqual(current_series_netapplet_task.status.title,
            'Invalid')

        self.assertIsNotNone(generic_netapplet_task.date_closed)
        self.assertIsNotNone(current_series_netapplet_task.date_closed)


class TestBugTaskPrivacy(TestCase):
    """Verify that the bug is either private or public."""

    layer = DatabaseFunctionalLayer

    def test_bugtask_privacy(self):
        # Let's log in as the user Foo Bar (to be allowed to edit bugs):
        foobar = login_foobar()

        # Mark one of the Firefox bugs private. While we do this, we're also
        # going to subscribe the Ubuntu team to the bug report to help
        # demonstrate later on the interaction between privacy and teams (see
        # the section entitled _Privacy and Team Awareness_):
        bug_upstream_firefox_crashes = getUtility(IBugTaskSet).get(15)

        ubuntu_team = getUtility(IPersonSet).getByEmail('support@ubuntu.com')
        bug_upstream_firefox_crashes.bug.subscribe(ubuntu_team, ubuntu_team)

        old_state = Snapshot(bug_upstream_firefox_crashes.bug,
            providing=IBug)
        self.assertTrue(bug_upstream_firefox_crashes.bug.setPrivate(True,
            foobar))

        bug_set_private = ObjectModifiedEvent(
            bug_upstream_firefox_crashes.bug, old_state,
            ["id", "title", "private"])
        notify(bug_set_private)
        flush_database_updates()

        # If we now login as someone who was neither implicitly nor explicitly
        # subscribed to this bug, e.g. No Privileges Person, they will not be
        # able to access or set properties of the bugtask.
        mr_no_privs = login_nopriv()

        with ExpectedException(Unauthorized, ''):
            bug_upstream_firefox_crashes.status

        with ExpectedException(Unauthorized, ''):
            bug_upstream_firefox_crashes.transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, getUtility(ILaunchBag).user)

        # The private bugs will be invisible to No Privileges Person in the
        # search results:
        params = BugTaskSearchParams(
            status=any(BugTaskStatus.NEW, BugTaskStatus.CONFIRMED),
            orderby="id", user=mr_no_privs)
        upstream_mozilla = getUtility(IProductSet).getByName('firefox')
        bugtasks = upstream_mozilla.searchTasks(params)
        self.assertEqual(bugtasks.count(), 3)

        bug_ids = [bt.bug.id for bt in bugtasks]
        self.assertEqual(sorted(bug_ids), [1, 4, 5])

        # We can create an access policy grant on the pillar to which the bug
        # is targeted and No Privileges Person will have access to the private
        # bug
        aps = getUtility(IAccessPolicySource)
        [policy] = aps.find(
            [(upstream_mozilla, InformationType.USERDATA)])
        apgs = getUtility(IAccessPolicyGrantSource)
        apgs.grant([(policy, mr_no_privs, ubuntu_team)])
        bugtasks = upstream_mozilla.searchTasks(params)
        self.assertEqual(bugtasks.count(), 4)

        bug_ids = [bt.bug.id for bt in bugtasks]
        self.assertEqual(sorted(bug_ids), [1, 4, 5, 6])
        apgs.revoke([(policy, mr_no_privs)])

        # Privacy and Priviledged Users
        # Now, we'll log in as Mark Shuttleworth, who was assigned to this bug
        # when it was marked private:
        login("mark@example.com")

        # And note that he can access and set the bugtask attributes:
        self.assertEqual(bug_upstream_firefox_crashes.status.title,
            'New')
        bug_upstream_firefox_crashes.transitionToStatus(
            BugTaskStatus.NEW, getUtility(ILaunchBag).user)

        # Privacy and Team Awareness
        # No Privileges Person can't see the private bug, because he's not a
        # subscriber:
        no_priv = login_nopriv()
        params = BugTaskSearchParams(
            status=any(BugTaskStatus.NEW, BugTaskStatus.CONFIRMED),
                user=no_priv)

        firefox = getUtility(IProductSet)['firefox']
        firefox_bugtasks = firefox.searchTasks(params)
        self.assertEqual([bugtask.bug.id for bugtask in firefox_bugtasks],
            [1, 4, 5])

        # But if we add No Privileges Person to the Ubuntu Team, and because
        # the Ubuntu Team *is* subscribed to the bug, No Privileges Person
        # will see the private bug.

        login("mark@example.com")
        ubuntu_team.addMember(no_priv, reviewer=ubuntu_team.teamowner)

        login("no-priv@canonical.com")
        params = BugTaskSearchParams(
            status=any(BugTaskStatus.NEW, BugTaskStatus.CONFIRMED),
                user=foobar)
        firefox_bugtasks = firefox.searchTasks(params)
        self.assertEqual([bugtask.bug.id for bugtask in firefox_bugtasks],
            [1, 4, 5, 6])

        # Privacy and Launchpad Admins
        # ----------------------------
        # Let's log in as Daniel Henrique Debonzi:
        launchbag = getUtility(ILaunchBag)
        login("daniel.debonzi@canonical.com")
        debonzi = launchbag.user

        # The same search as above yields the same result, because Daniel
        # Debonzi is an administrator.
        firefox = getUtility(IProductSet).get(4)
        params = BugTaskSearchParams(status=any(BugTaskStatus.NEW,
                                                BugTaskStatus.CONFIRMED),
                                     user=debonzi)
        firefox_bugtasks = firefox.searchTasks(params)
        self.assertEqual([bugtask.bug.id for bugtask in firefox_bugtasks],
            [1, 4, 5, 6])

        # Trying to retrieve the bug directly will work fine:
        bug_upstream_firefox_crashes = getUtility(IBugTaskSet).get(15)
        # As will attribute access:
        self.assertEqual(bug_upstream_firefox_crashes.status.title,
            'New')

        # And attribute setting:
        bug_upstream_firefox_crashes.transitionToStatus(
            BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user)
        bug_upstream_firefox_crashes.transitionToStatus(
            BugTaskStatus.NEW, getUtility(ILaunchBag).user)


class TestCountsForProducts(TestCase):
    """Test BugTaskSet.getOpenBugTasksPerProduct"""

    layer = DatabaseFunctionalLayer

    def test_open_product_counts(self):
        # IBugTaskSet.getOpenBugTasksPerProduct() will return a dictionary
        # of product_id:count entries for bugs in an open status that
        # the user given as a parameter is allowed to see. If a product,
        # such as id=3 does not have any open bugs, it will not appear
        # in the result.
        foobar = login_foobar()

        productset = getUtility(IProductSet)
        products = [productset.get(id) for id in (3, 5, 20)]
        sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        bugtask_counts = getUtility(IBugTaskSet).getOpenBugTasksPerProduct(
            sample_person, products)
        res = sorted(bugtask_counts.items())
        self.assertEqual(
            'product_id=%d count=%d' % tuple(res[0]),
            'product_id=5 count=1')
        self.assertEqual(
            'product_id=%d count=%d' % tuple(res[1]),
            'product_id=20 count=2')

        # A Launchpad admin will get a higher count for the product with id=20
        # because he can see the private bug.
        bugtask_counts = getUtility(IBugTaskSet).getOpenBugTasksPerProduct(
            foobar, products)
        res = sorted(bugtask_counts.items())
        self.assertEqual(
            'product_id=%d count=%d' % tuple(res[0]),
            'product_id=5 count=1')
        self.assertEqual(
            'product_id=%d count=%d' % tuple(res[1]),
            'product_id=20 count=3')

        # Someone subscribed to the private bug on the product with id=20
        # will also have it added to the count.
        karl = getUtility(IPersonSet).getByName('karl')
        bugtask_counts = getUtility(IBugTaskSet).getOpenBugTasksPerProduct(
            karl, products)
        res = sorted(bugtask_counts.items())
        self.assertEqual(
            'product_id=%d count=%d' % tuple(res[0]),
            'product_id=5 count=1')
        self.assertEqual(
            'product_id=%d count=%d' % tuple(res[1]),
            'product_id=20 count=3')


class TestSortingBugTasks(TestCase):
    """Bug tasks need to sort in a very particular order."""

    layer = DatabaseFunctionalLayer

    def test_sortingorder(self):
        """We want product tasks, then ubuntu, then distro-related.

        In the distro-related tasks we want a distribution-task first, then
        distroseries-tasks for that same distribution. The distroseries tasks
        should be sorted by distroseries version.
        """
        login('foo.bar@canonical.com')
        bug_one = getUtility(IBugSet).get(1)
        tasks = bug_one.bugtasks
        task_names = [task.bugtargetdisplayname for task in tasks]
        self.assertEqual(task_names, [
            u'Mozilla Firefox',
            'mozilla-firefox (Ubuntu)',
            'mozilla-firefox (Debian)',
        ])


class TestBugTaskAdaptation(TestCase):
    """Verify bugtask adaptation."""

    layer = DatabaseFunctionalLayer

    def test_bugtask_adaptation(self):
        """An IBugTask can be adapted to an IBug"""
        login('foo.bar@canonical.com')
        bugtask_four = getUtility(IBugTaskSet).get(4)
        bug = IBug(bugtask_four)
        self.assertEqual(bug.title,
            u'Firefox does not support SVG')


class TestTargetNameCache(TestCase):
    """BugTask table has a stored computed attribute.

    This targetnamecache attribute which stores a computed value to allow us
    to sort and search on that value without having to do lots of SQL joins.
    This cached value gets updated daily by the
    update-bugtask-targetnamecaches cronscript and whenever the bugtask is
    changed.  Of course, it's also computed and set when a bugtask is
    created.

    `BugTask.bugtargetdisplayname` simply returns `targetnamecache`, and
    the latter is not exposed in `IBugTask`, so the `bugtargetdisplayname`
    is used here.
    """

    layer = DatabaseFunctionalLayer

    def test_cron_updating_targetnamecache(self):
        """Verify the initial target name cache."""
        login('foo.bar@canonical.com')
        bug_one = getUtility(IBugSet).get(1)
        mark = getUtility(IPersonSet).getByEmail('mark@example.com')
        netapplet = getUtility(IProductSet).get(11)

        upstream_task = getUtility(IBugTaskSet).createTask(
            bug_one, mark, netapplet,
            status=BugTaskStatus.NEW, importance=BugTaskImportance.MEDIUM)
        self.assertEqual(upstream_task.bugtargetdisplayname,
            u'NetApplet')

        thunderbird = getUtility(IProductSet).get(8)
        upstream_task_id = upstream_task.id
        upstream_task.transitionToTarget(thunderbird)
        self.assertEqual(upstream_task.bugtargetdisplayname,
            u'Mozilla Thunderbird')

        thunderbird.name = 'thunderbird-ng'
        thunderbird.displayname = 'Mozilla Thunderbird NG'

        # XXX Guilherme Salgado 2005-11-07 bug=3989:
        # This flush_database_updates() shouldn't be needed because we
        # already have the transaction.commit() here, but without it
        # (flush_database_updates), the cronscript won't see the thunderbird
        # name change.
        flush_database_updates()
        transaction.commit()

        process = subprocess.Popen(
            'cronscripts/update-bugtask-targetnamecaches.py', shell=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()

        self.assertTrue(err.startswith(("INFO    Creating lockfile: "
            "/var/lock/launchpad-launchpad-targetnamecacheupdater.lock")))
        self.assertTrue('INFO    Updating targetname cache of bugtasks' in err)
        self.assertTrue('INFO    Calculating targets.' in err)
        self.assertTrue('INFO    Will check ', err)
        self.assertTrue("INFO    Updating (u'Mozilla Thunderbird',)" in err)
        self.assertTrue('INFO    Updated 1 target names.' in err)
        self.assertTrue('INFO    Finished updating targetname cache' in err)

        self.assertEqual(process.returncode, 0)

        # XXX Guilherme Salgado 2005-11-07:
        # If we don't call flush_database_caches() here, we won't see the
        # changes made by the cronscript in objects we already have cached.
        flush_database_caches()
        transaction.commit()

        self.assertEqual(
            getUtility(IBugTaskSet).get(upstream_task_id).bugtargetdisplayname,
            u'Mozilla Thunderbird NG')

        # With sourcepackage bugtasks that have accepted nominations to a
        # series, additional sourcepackage bugtasks are automatically
        # nominated to the same series. The nominations are implicitly
        # accepted and have targetnamecache updated.
        ubuntu = getUtility(IDistributionSet).get(1)

        new_bug, new_bug_event = getUtility(IBugSet).createBugWithoutTarget(
            CreateBugParams(mark, 'New Bug', comment='New Bug'))

        # The first message of a new bug has index 0.
        self.assertEqual(new_bug.bug_messages[0].index, 0)

        getUtility(IBugTaskSet).createTask(
            new_bug, mark, ubuntu.getSourcePackage('mozilla-firefox'))

        # The first task has been created and successfully nominated to Hoary.
        new_bug.addNomination(mark, ubuntu.currentseries).approve(mark)

        task_set = [task.bugtargetdisplayname for task in new_bug.bugtasks]
        self.assertEqual(task_set, [
            'mozilla-firefox (Ubuntu)',
            'mozilla-firefox (Ubuntu Hoary)',
        ])

        getUtility(IBugTaskSet).createTask(
            new_bug, mark, ubuntu.getSourcePackage('alsa-utils'))

        # The second task has been created and has also been successfully
        # nominated to Hoary.

        task_set = [task.bugtargetdisplayname for task in new_bug.bugtasks]
        self.assertEqual(task_set, [
            'alsa-utils (Ubuntu)',
            'mozilla-firefox (Ubuntu)',
            'alsa-utils (Ubuntu Hoary)',
            'mozilla-firefox (Ubuntu Hoary)',
        ])

        # The updating of targetnamecaches is usually done by the cronjob,
        # however it can also be invoked directly.
        thunderbird.name = 'thunderbird'
        thunderbird.displayname = 'Mozilla Thunderbird'
        transaction.commit()

        self.assertEqual(upstream_task.bugtargetdisplayname,
            u'Mozilla Thunderbird NG')

        logger = FakeLogger()
        updater = BugTaskTargetNameCacheUpdater(transaction, logger)
        updater.run()

        flush_database_caches()
        transaction.commit()
        self.assertEqual(upstream_task.bugtargetdisplayname,
            u'Mozilla Thunderbird')


class TestTargetUsesMalone(TestCase):
    """Verify bug task flag for using Malone is set."""

    layer = DatabaseFunctionalLayer

    def test_bugtask_users_malone(self):
        """Verify the target uses Malone as its official bugtracker.
        """
        login('foo.bar@canonical.com')
        bug_one = getUtility(IBugSet).get(1)
        malone_info = [(task.bugtargetdisplayname, task.target_uses_malone)
            for task in bug_one.bugtasks]

        self.assertEqual(malone_info, [
            ('Mozilla Firefox', True),
            ('mozilla-firefox (Ubuntu)', True),
            ('mozilla-firefox (Debian)', False),
        ])


class TestBugTaskBadges(TestCaseWithFactory):

    """Verify getBugTaskBadgeProperties"""

    layer = DatabaseFunctionalLayer

    def test_butask_badges_populated(self):
        """getBugTaskBadgeProperties(), calcs properties for multiple tasks.

        A bug can have certain properties, which results in a badge being
        displayed in bug listings.
        """
        login('foo.bar@canonical.com')

        def get_badge_properties(badge_properties):
            bugtasks = sorted(badge_properties.keys(), key=attrgetter('id'))
            res = []
            for bugtask in bugtasks:
                res.append("Properties for bug %s:" % (bugtask.bug.id))
                for key, value in sorted(badge_properties[bugtask].items()):
                    res.append(" %s: %s" % (key, value))
            return res

        bug_two = getUtility(IBugSet).get(2)
        some_bugtask = bug_two.bugtasks[0]
        bug_three = getUtility(IBugSet).get(3)
        another_bugtask = bug_three.bugtasks[0]
        badge_properties = getUtility(IBugTaskSet).getBugTaskBadgeProperties(
            [some_bugtask, another_bugtask])

        self.assertEqual(get_badge_properties(badge_properties),
           ['Properties for bug 2:',
           ' has_branch: False',
           ' has_patch: False',
           ' has_specification: False',
           'Properties for bug 3:',
           ' has_branch: False',
           ' has_patch: False',
           ' has_specification: False'])

        # a specification gets linked...
        spec = getUtility(ISpecificationSet).all_specifications[0]
        spec.linkBug(bug_two)

        # or a branch gets linked to the bug...
        no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
        branch = self.factory.makeAnyBranch()
        bug_three.linkBranch(branch, no_priv)

        # the properties for the bugtasks reflect this.
        badge_properties = getUtility(IBugTaskSet).getBugTaskBadgeProperties(
            [some_bugtask, another_bugtask])
        self.assertEqual(get_badge_properties(badge_properties), [
        'Properties for bug 2:',
        ' has_branch: False',
        ' has_patch: False',
        ' has_specification: True',
        'Properties for bug 3:',
        ' has_branch: True',
        ' has_patch: False',
        ' has_specification: False',
         ])


class TestBugTaskTags(TestCase):
    """List of bugtasks often need to display related tasks."""

    layer = DatabaseFunctionalLayer

    def test_getting_tags_from_bugs(self):
        """Tags are related to bugtasks via bugs.

        BugTaskSet has a method getBugTaskTags that can calculate the tags in
        one query.
        """
        login('foo.bar@canonical.com')
        bug_two = getUtility(IBugSet).get(2)
        some_bugtask = bug_two.bugtasks[0]
        bug_three = getUtility(IBugSet).get(3)
        another_bugtask = bug_three.bugtasks[0]

        some_bugtask.bug.tags = [u'foo', u'bar']
        another_bugtask.bug.tags = [u'baz', u'bop']
        tags_by_task = getUtility(IBugTaskSet).getBugTaskTags([
            some_bugtask, another_bugtask])

        self.assertEqual(tags_by_task,
            {3: [u'bar', u'foo'], 6: [u'baz', u'bop']})


class TestSimilarBugs(TestCaseWithFactory):
    """It's possible to get a list of bugs similar to the current one."""

    layer = DatabaseFunctionalLayer

    def _verifySimilarResults(self, similar, expected):
        """Helper to test the similar results with expected set."""
        bug_info = [(bug.id, bug.title)
            for bug in sorted(similar, key=attrgetter('id'))]
        self.assertEqual(bug_info, expected)

    def test_similar_bugs_property(self):

        """Find similar via the similar_bugs property of its bug tasks."""
        firefox = getUtility(IProductSet)['firefox']
        new_ff_bug = self.factory.makeBug(product=firefox, title="Firefox")
        ff_bugtask = new_ff_bug.bugtasks[0]
        sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')

        similar_bugs = ff_bugtask.findSimilarBugs(user=sample_person)
        self._verifySimilarResults(similar_bugs, [
            (1, u'Firefox does not support SVG'),
            (5, u'Firefox install instructions should be complete'),
        ])

    def test_similar_bugs_distributions(self):
        """This also works for distributions."""
        firefox = getUtility(IProductSet)['firefox']
        new_ff_bug = self.factory.makeBug(product=firefox, title="Firefox")
        sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        ubuntu = getUtility(IDistributionSet).get(1)
        ubuntu_bugtask = self.factory.makeBugTask(bug=new_ff_bug,
            target=ubuntu)
        self.factory.makeBugTask(bug=new_ff_bug, target=ubuntu)
        similar_bugs = ubuntu_bugtask.findSimilarBugs(user=sample_person)
        self._verifySimilarResults(similar_bugs, [
            (1, u'Firefox does not support SVG'),
        ])

    def test_similar_bugs_sourcepackages(self):
        """Similar bugs should also be found through source packages"""
        firefox = getUtility(IProductSet)['firefox']
        sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        ubuntu = getUtility(IDistributionSet).get(1)

        a_ff_bug = self.factory.makeBug(product=firefox, title="a Firefox")
        firefox_package = ubuntu.getSourcePackage('mozilla-firefox')
        firefox_package_bugtask = self.factory.makeBugTask(
            bug=a_ff_bug, target=firefox_package)

        similar_bugs = firefox_package_bugtask.findSimilarBugs(
             user=sample_person)
        self._verifySimilarResults(similar_bugs, [
            (1, u'Firefox does not support SVG'),
        ])

    def test_similar_bugs_privacy(self):
        """Private bugs won't show up unless the user is a direct subscriber.

        We'll demonstrate this by creating a new bug against Firefox.
        """
        firefox = getUtility(IProductSet)['firefox']
        new_ff_bug = self.factory.makeBug(product=firefox, title="Firefox")
        ff_bugtask = new_ff_bug.bugtasks[0]
        no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')

        second_ff_bug = self.factory.makeBug(
            product=firefox, title="Yet another Firefox bug")
        similar_bugs = ff_bugtask.findSimilarBugs(user=no_priv)
        self._verifySimilarResults(similar_bugs, [
            (1, u'Firefox does not support SVG'),
            (5, u'Firefox install instructions should be complete'),
            (17, u'Yet another Firefox bug'),
        ])

        # If we mark the new bug as private, it won't appear in the similar
        # bugs list for no_priv any more, since they're not a direct
        # subscriber.
        foobar = login_foobar()
        self.assertEqual(second_ff_bug.setPrivate(True, foobar), True)

        similar_bugs = ff_bugtask.findSimilarBugs(user=no_priv)
        self._verifySimilarResults(similar_bugs, [
            (1, u'Firefox does not support SVG'),
            (5, u'Firefox install instructions should be complete'),
        ])


class TestStatusCountsForProductSeries(TestCaseWithFactory):
    """Test BugTaskSet.getStatusCountsForProductSeries()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestStatusCountsForProductSeries, self).setUp()
        self.bugtask_set = getUtility(IBugTaskSet)
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.product = self.factory.makeProduct(owner=self.owner)
        self.series = self.factory.makeProductSeries(product=self.product)
        self.milestone = self.factory.makeMilestone(productseries=self.series)

    def get_counts(self, user):
        return self.bugtask_set.getStatusCountsForProductSeries(
            user, self.series)

    def createBugs(self):
        self.factory.makeBug(milestone=self.milestone)
        self.factory.makeBug(
            milestone=self.milestone,
            information_type=InformationType.USERDATA)
        self.factory.makeBug(series=self.series)
        self.factory.makeBug(
            series=self.series, information_type=InformationType.USERDATA)

    def test_privacy_and_counts_for_unauthenticated_user(self):
        # An unauthenticated user should see bug counts for each status
        # that do not include private bugs.
        self.createBugs()
        self.assertEqual(
            {BugTaskStatus.NEW: 2},
            self.get_counts(None))

    def test_privacy_and_counts_for_owner(self):
        # The owner should see bug counts for each status that do
        # include all private bugs.
        self.createBugs()
        self.assertEqual(
            {BugTaskStatus.NEW: 4},
            self.get_counts(self.owner))

    def test_privacy_and_counts_for_other_user(self):
        # A random authenticated user should see bug counts for each
        # status that do include all private bugs, since it is costly to
        # query just the private bugs that the user has access to view,
        # and this query may be run many times on a single page.
        self.createBugs()
        other = self.factory.makePerson()
        self.assertEqual(
            {BugTaskStatus.NEW: 4},
            self.get_counts(other))

    def test_multiple_statuses(self):
        # Test that separate counts are provided for each status that
        # bugs are found in.
        statuses = [
            BugTaskStatus.INVALID,
            BugTaskStatus.OPINION,
            ]
        for status in statuses:
            self.factory.makeBug(milestone=self.milestone, status=status)
            self.factory.makeBug(series=self.series, status=status)
        for i in range(3):
            self.factory.makeBug(series=self.series)
        expected = {
            BugTaskStatus.INVALID: 2,
            BugTaskStatus.OPINION: 2,
            BugTaskStatus.NEW: 3,
            }
        self.assertEqual(expected, self.get_counts(None))

    def test_incomplete_status(self):
        # INCOMPLETE is stored as either INCOMPLETE_WITH_RESPONSE or
        # INCOMPLETE_WITHOUT_RESPONSE so the stats do not include a count of
        # INCOMPLETE tasks.
        statuses = [
            BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE,
            BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE,
            BugTaskStatus.INCOMPLETE,
            ]
        for status in statuses:
            self.factory.makeBug(series=self.series, status=status)
        flush_database_updates()
        expected = {
            BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE: 1,
            BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE: 2,
            }
        self.assertEqual(expected, self.get_counts(None))


class TestBugTaskMilestones(TestCaseWithFactory):
    """Tests that appropriate milestones are returned for bugtasks."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTaskMilestones, self).setUp()
        self.product = self.factory.makeProduct()
        self.product_bug = self.factory.makeBug(product=self.product)
        self.product_milestone = self.factory.makeMilestone(
            product=self.product)
        self.distribution = self.factory.makeDistribution()
        self.distribution_bug = self.factory.makeBug(
            distribution=self.distribution)
        self.distribution_milestone = self.factory.makeMilestone(
            distribution=self.distribution)
        self.bugtaskset = getUtility(IBugTaskSet)

    def test_get_target_milestones_with_one_task(self):
        milestones = list(self.bugtaskset.getBugTaskTargetMilestones(
            [self.product_bug.default_bugtask]))
        self.assertEqual(
            [self.product_milestone],
            milestones)

    def test_get_target_milestones_multiple_tasks(self):
        tasks = [
            self.product_bug.default_bugtask,
            self.distribution_bug.default_bugtask,
            ]
        milestones = sorted(
            self.bugtaskset.getBugTaskTargetMilestones(tasks))
        self.assertEqual(
            sorted([self.product_milestone, self.distribution_milestone]),
            milestones)
