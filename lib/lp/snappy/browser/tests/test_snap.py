# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package views."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.snappy.browser.snap import SnapView
from lp.snappy.interfaces.snap import SNAP_FEATURE_FLAG
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.publication import test_traverse


class TestSnapNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapNavigation, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_canonical_url(self):
        owner = self.factory.makePerson(name="person")
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, name=u"snap")
        self.assertEqual(
            "http://launchpad.dev/~person/+snap/snap", canonical_url(snap))

    def test_snap(self):
        snap = self.factory.makeSnap()
        obj, _, _ = test_traverse(
            "http://launchpad.dev/~%s/+snap/%s" % (snap.owner.name, snap.name))
        self.assertEqual(snap, obj)


class TestSnapView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.distroseries = self.factory.makeDistroSeries(
            distribution=self.ubuntu, name="shiny", displayname="Shiny")
        processor = getUtility(IProcessorSet).getByName("386")
        self.distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, architecturetag="i386",
            processor=processor)
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")
        self.factory.makeBuilder(virtualized=True)

    def makeSnap(self, branch=None, git_ref=None):
        kwargs = {}
        if branch is None and git_ref is None:
            branch = self.factory.makeAnyBranch()
        if branch is not None:
            kwargs["branch"] = branch
        else:
            kwargs["git_repository"] = git_ref.repository
            kwargs["git_path"] = git_ref.path
        return self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, name=u"snap-name", **kwargs)

    def makeBuild(self, snap=None, archive=None, date_created=None, **kwargs):
        if snap is None:
            snap = self.makeSnap()
        if archive is None:
            archive = self.ubuntu.main_archive
        if date_created is None:
            date_created = datetime.now(pytz.UTC) - timedelta(hours=1)
        return self.factory.makeSnapBuild(
            requester=self.person, snap=snap, archive=archive,
            distroarchseries=self.distroarchseries, date_created=date_created,
            **kwargs)

    def test_index(self):
        build = self.makeBuild(
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=30))
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Snap packages snap-name
            .*
            Snap package information
            Owner: Test Person
            Distribution series: Ubuntu Shiny
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_success_with_buildlog(self):
        # The build log is shown if it is there.
        build = self.makeBuild(
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=30))
        build.setLog(self.factory.makeLibraryFileAlias())
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago buildlog \(.*\) i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_hides_builds_into_private_archive(self):
        # The index page hides builds into archives the user can't view.
        archive = self.factory.makeArchive(private=True)
        with person_logged_in(archive.owner):
            snap = self.makeBuild(archive=archive).snap
        self.assertIn(
            "This snap package has not been built yet.",
            self.getMainText(snap))

    def test_index_no_builds(self):
        # A message is shown when there are no builds.
        snap = self.factory.makeSnap()
        self.assertIn(
            "This snap package has not been built yet.",
            self.getMainText(snap))

    def test_index_pending(self):
        # A pending build is listed as such.
        build = self.makeBuild()
        build.queueBuild()
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status When complete Architecture Archive
            Needs building in .* \(estimated\) i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def setStatus(self, build, status):
        build.updateStatus(
            BuildStatus.BUILDING, date_started=build.date_created)
        build.updateStatus(
            status, date_finished=build.date_started + timedelta(minutes=30))

    def test_builds(self):
        # SnapView.builds produces reasonable results.
        snap = self.makeSnap()
        # Create oldest builds first so that they sort properly by id.
        date_gen = time_counter(
            datetime(2000, 1, 1, tzinfo=pytz.UTC), timedelta(days=1))
        builds = [
            self.makeBuild(snap=snap, date_created=next(date_gen))
            for i in range(11)]
        view = SnapView(snap, None)
        self.assertEqual(list(reversed(builds)), view.builds)
        self.setStatus(builds[10], BuildStatus.FULLYBUILT)
        self.setStatus(builds[9], BuildStatus.FAILEDTOBUILD)
        # When there are >= 9 pending builds, only the most recent of any
        # completed builds is returned.
        self.assertEqual(
            list(reversed(builds[:9])) + [builds[10]], view.builds)
        for build in builds[:9]:
            self.setStatus(build, BuildStatus.FULLYBUILT)
        self.assertEqual(list(reversed(builds[1:])), view.builds)
