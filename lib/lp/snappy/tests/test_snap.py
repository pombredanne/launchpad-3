# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap packages."""

__metaclass__ = type

from datetime import datetime

from lazr.lifecycle.event import ObjectModifiedEvent
import pytz
from storm.locals import Store
import transaction
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.snappy.interfaces.snap import (
    CannotDeleteSnap,
    ISnap,
    ISnapSet,
    SNAP_FEATURE_FLAG,
    SnapBuildAlreadyPending,
    SnapBuildDisallowedArchitecture,
    SnapFeatureDisabled,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.testing import (
    admin_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestSnapFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new Snaps.
        person = self.factory.makePerson()
        self.assertRaises(
            SnapFeatureDisabled, getUtility(ISnapSet).new,
            person, person, None, None, True, None)


class TestSnap(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnap, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_implements_interfaces(self):
        # Snap implements ISnap.
        snap = self.factory.makeSnap()
        with admin_logged_in():
            self.assertProvides(snap, ISnap)

    def test_initial_date_last_modified(self):
        # The initial value of date_last_modified is date_created.
        snap = self.factory.makeSnap(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC))
        self.assertEqual(snap.date_created, snap.date_last_modified)

    def test_modifiedevent_sets_date_last_modified(self):
        # When a Snap receives an object modified event, the last modified
        # date is set to UTC_NOW.
        snap = self.factory.makeSnap(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC))
        notify(ObjectModifiedEvent(
            removeSecurityProxy(snap), snap, [ISnap["name"]]))
        self.assertSqlAttributeEqualsDate(snap, "date_last_modified", UTC_NOW)

    def makeBuildableDistroArchSeries(self, **kwargs):
        das = self.factory.makeDistroArchSeries(**kwargs)
        fake_chroot = self.factory.makeLibraryFileAlias(
            filename="fake_chroot.tar.gz", db_only=True)
        das.addOrUpdateChroot(fake_chroot)
        return das

    def test_requestBuild(self):
        # requestBuild creates a new SnapBuild.
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            processor=processor)
        snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor])
        build = snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        self.assertTrue(ISnapBuild.providedBy(build))
        self.assertEqual(snap.owner, build.requester)
        self.assertEqual(snap.distro_series.main_archive, build.archive)
        self.assertEqual(distroarchseries, build.distro_arch_series)
        self.assertEqual(PackagePublishingPocket.RELEASE, build.pocket)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)
        store = Store.of(build)
        store.flush()
        build_queue = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id ==
                removeSecurityProxy(build).build_farm_job_id).one()
        self.assertProvides(build_queue, IBuildQueue)
        self.assertEqual(
            snap.distro_series.main_archive.require_virtualized,
            build_queue.virtualized)
        self.assertEqual(BuildQueueStatus.WAITING, build_queue.status)

    def test_requestBuild_score(self):
        # Build requests have a relatively low queue score (2505).
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            processor=processor)
        snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor])
        build = snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2505, queue_record.lastscore)

    def test_requestBuild_relative_build_score(self):
        # Offsets for archives are respected.
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            processor=processor)
        snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries, processors=[processor])
        archive = self.factory.makeArchive(owner=snap.owner)
        removeSecurityProxy(archive).relative_build_score = 100
        build = snap.requestBuild(
            snap.owner, archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2605, queue_record.lastscore)

    def test_requestBuild_rejects_repeats(self):
        # requestBuild refuses if there is already a pending build.
        distroseries = self.factory.makeDistroSeries()
        procs = []
        arches = []
        for i in range(2):
            procs.append(self.factory.makeProcessor(supports_virtualized=True))
            arches.append(self.makeBuildableDistroArchSeries(
                distroseries=distroseries, processor=procs[i]))
        snap = self.factory.makeSnap(
            distroseries=distroseries, processors=[procs[0], procs[1]])
        old_build = snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, arches[0],
            PackagePublishingPocket.RELEASE)
        self.assertRaises(
            SnapBuildAlreadyPending, snap.requestBuild,
            snap.owner, snap.distro_series.main_archive, arches[0],
            PackagePublishingPocket.RELEASE)
        # We can build for a different archive.
        snap.requestBuild(
            snap.owner, self.factory.makeArchive(owner=snap.owner), arches[0],
            PackagePublishingPocket.RELEASE)
        # We can build for a different distroarchseries.
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, arches[1],
            PackagePublishingPocket.RELEASE)
        # Changing the status of the old build allows a new build.
        old_build.updateStatus(BuildStatus.BUILDING)
        old_build.updateStatus(BuildStatus.FULLYBUILT)
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, arches[0],
            PackagePublishingPocket.RELEASE)

    def test_requestBuild_rejects_unconfigured_arch(self):
        # Snap.requestBuild only allows dispatching a build for one of the
        # configured architectures.
        distroseries = self.factory.makeDistroSeries()
        procs = []
        arches = []
        for i in range(2):
            procs.append(self.factory.makeProcessor(supports_virtualized=True))
            arches.append(self.makeBuildableDistroArchSeries(
                distroseries=distroseries, processor=procs[i]))
        snap = self.factory.makeSnap(
            distroseries=distroseries, processors=[procs[0]])
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, arches[0],
            PackagePublishingPocket.RELEASE)
        self.assertRaises(
            SnapBuildDisallowedArchitecture, snap.requestBuild,
            snap.owner, snap.distro_series.main_archive, arches[1],
            PackagePublishingPocket.RELEASE)

    def test_requestBuild_virtualization(self):
        # New builds are virtualized if any of the processor, snap or
        # archive require it.
        proc_arches = {}
        for proc_nonvirt in True, False:
            processor = self.factory.makeProcessor(
                supports_virtualized=True,
                supports_nonvirtualized=proc_nonvirt)
            distroarchseries = self.makeBuildableDistroArchSeries(
                processor=processor)
            proc_arches[proc_nonvirt] = (processor, distroarchseries)
        for proc_nonvirt, snap_virt, archive_virt, build_virt in (
                (True, False, False, False),
                (True, False, True, True),
                (True, True, False, True),
                (True, True, True, True),
                (False, False, False, True),
                (False, False, True, True),
                (False, True, False, True),
                (False, True, True, True),
                ):
            processor, distroarchseries = proc_arches[proc_nonvirt]
            snap = self.factory.makeSnap(
                distroseries=distroarchseries.distroseries,
                require_virtualized=snap_virt, processors=[processor])
            archive = self.factory.makeArchive(
                distribution=distroarchseries.distroseries.distribution,
                owner=snap.owner, virtualized=archive_virt)
            build = snap.requestBuild(
                snap.owner, archive, distroarchseries,
                PackagePublishingPocket.RELEASE)
            self.assertEqual(build_virt, build.virtualized)

    def test_requestBuild_nonvirtualized(self):
        # A non-virtualized processor can build a snap package iff the snap
        # has require_virtualized set to False.
        processor = self.factory.makeProcessor(
            supports_virtualized=False, supports_nonvirtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            processor=processor)
        snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries, processors=[processor])
        self.assertRaises(
            SnapBuildDisallowedArchitecture, snap.requestBuild,
            snap.owner, snap.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        with admin_logged_in():
            snap.require_virtualized = False
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)

    def test_getBuilds(self):
        # Test the various getBuilds methods.
        snap = self.factory.makeSnap()
        builds = [self.factory.makeSnapBuild(snap=snap) for x in range(3)]
        # We want the latest builds first.
        builds.reverse()

        self.assertEqual(builds, list(snap.builds))
        self.assertEqual([], list(snap.completed_builds))
        self.assertEqual(builds, list(snap.pending_builds))

        # Change the status of one of the builds and retest.
        builds[0].updateStatus(BuildStatus.BUILDING)
        builds[0].updateStatus(BuildStatus.FULLYBUILT)
        self.assertEqual(builds, list(snap.builds))
        self.assertEqual(builds[:1], list(snap.completed_builds))
        self.assertEqual(builds[1:], list(snap.pending_builds))

    def test_getBuilds_cancelled_never_started_last(self):
        # A cancelled build that was never even started sorts to the end.
        snap = self.factory.makeSnap()
        fullybuilt = self.factory.makeSnapBuild(snap=snap)
        instacancelled = self.factory.makeSnapBuild(snap=snap)
        fullybuilt.updateStatus(BuildStatus.BUILDING)
        fullybuilt.updateStatus(BuildStatus.FULLYBUILT)
        instacancelled.updateStatus(BuildStatus.CANCELLED)
        self.assertEqual([fullybuilt, instacancelled], list(snap.builds))
        self.assertEqual(
            [fullybuilt, instacancelled], list(snap.completed_builds))
        self.assertEqual([], list(snap.pending_builds))

    def test_getBuilds_privacy(self):
        # The various getBuilds methods exclude builds against invisible
        # archives.
        snap = self.factory.makeSnap()
        archive = self.factory.makeArchive(
            distribution=snap.distro_series.distribution, owner=snap.owner,
            private=True)
        with person_logged_in(snap.owner):
            build = self.factory.makeSnapBuild(snap=snap, archive=archive)
            self.assertEqual([build], list(snap.builds))
            self.assertEqual([build], list(snap.pending_builds))
        self.assertEqual([], list(snap.builds))
        self.assertEqual([], list(snap.pending_builds))

    def test_delete_without_builds(self):
        # A snap package with no builds can be deleted.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, distroseries=distroseries,
            name=u"condemned")
        self.assertTrue(getUtility(ISnapSet).exists(owner, u"condemned"))
        with person_logged_in(snap.owner):
            snap.destroySelf()
        self.assertFalse(getUtility(ISnapSet).exists(owner, u"condemned"))

    def test_delete_with_builds(self):
        # A snap package with builds cannot be deleted.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, distroseries=distroseries,
            name=u"condemned")
        self.factory.makeSnapBuild(snap=snap)
        self.assertTrue(getUtility(ISnapSet).exists(owner, u"condemned"))
        with person_logged_in(snap.owner):
            self.assertRaises(CannotDeleteSnap, snap.destroySelf)
        self.assertTrue(getUtility(ISnapSet).exists(owner, u"condemned"))


class TestSnapSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapSet, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_class_implements_interfaces(self):
        # The SnapSet class implements ISnapSet.
        self.assertProvides(getUtility(ISnapSet), ISnapSet)

    def makeSnapComponents(self, branch=None, git_ref=None):
        """Return a dict of values that can be used to make a Snap.

        Suggested use: provide as kwargs to ISnapSet.new.

        :param branch: An `IBranch`, or None.
        :param git_ref: An `IGitRef`, or None.
        """
        registrant = self.factory.makePerson()
        components = dict(
            registrant=registrant,
            owner=self.factory.makeTeam(owner=registrant),
            distro_series=self.factory.makeDistroSeries(),
            name=self.factory.getUniqueString(u"snap-name"))
        if branch is None and git_ref is None:
            branch = self.factory.makeAnyBranch()
        if branch is not None:
            components["branch"] = branch
        else:
            components["git_repository"] = git_ref.repository
            components["git_path"] = git_ref.path
        return components

    def test_creation_bzr(self):
        # The metadata entries supplied when a Snap is created for a Bazaar
        # branch are present on the new object.
        branch = self.factory.makeAnyBranch()
        components = self.makeSnapComponents(branch=branch)
        snap = getUtility(ISnapSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], snap.registrant)
        self.assertEqual(components["owner"], snap.owner)
        self.assertEqual(components["distro_series"], snap.distro_series)
        self.assertEqual(components["name"], snap.name)
        self.assertEqual(branch, snap.branch)
        self.assertIsNone(snap.git_repository)
        self.assertIsNone(snap.git_path)
        self.assertTrue(snap.require_virtualized)

    def test_creation_git(self):
        # The metadata entries supplied when a Snap is created for a Git
        # branch are present on the new object.
        [ref] = self.factory.makeGitRefs()
        components = self.makeSnapComponents(git_ref=ref)
        snap = getUtility(ISnapSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], snap.registrant)
        self.assertEqual(components["owner"], snap.owner)
        self.assertEqual(components["distro_series"], snap.distro_series)
        self.assertEqual(components["name"], snap.name)
        self.assertIsNone(snap.branch)
        self.assertEqual(ref.repository, snap.git_repository)
        self.assertEqual(ref.path, snap.git_path)
        self.assertTrue(snap.require_virtualized)

    def test_exists(self):
        # ISnapSet.exists checks for matching Snaps.
        snap = self.factory.makeSnap()
        self.assertTrue(getUtility(ISnapSet).exists(snap.owner, snap.name))
        self.assertFalse(
            getUtility(ISnapSet).exists(self.factory.makePerson(), snap.name))
        self.assertFalse(getUtility(ISnapSet).exists(snap.owner, u"different"))

    def test_findByPerson(self):
        # ISnapSet.findByPerson returns all Snaps with the given owner.
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for owner in owners:
            for i in range(2):
                snaps.append(self.factory.makeSnap(
                    registrant=owner, owner=owner))
        self.assertContentEqual(
            snaps[:2], getUtility(ISnapSet).findByPerson(owners[0]))
        self.assertContentEqual(
            snaps[2:], getUtility(ISnapSet).findByPerson(owners[1]))


class TestSnapProcessors(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSnapProcessors, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.default_procs = [
            getUtility(IProcessorSet).getByName("386"),
            getUtility(IProcessorSet).getByName("amd64")]
        self.unrestricted_procs = (
            self.default_procs + [getUtility(IProcessorSet).getByName("hppa")])
        self.arm = self.factory.makeProcessor(
            name="arm", restricted=True, build_by_default=False)

    def test_new_default_processors(self):
        # SnapSet.new creates a SnapArch for each Processor with
        # build_by_default set.
        self.factory.makeProcessor(name="default", build_by_default=True)
        self.factory.makeProcessor(name="nondefault", build_by_default=False)
        owner = self.factory.makePerson()
        snap = getUtility(ISnapSet).new(
            registrant=owner, owner=owner,
            distro_series=self.factory.makeDistroSeries(), name=u"snap",
            branch=self.factory.makeAnyBranch())
        self.assertContentEqual(
            ["386", "amd64", "hppa", "default"],
            [processor.name for processor in snap.processors])

    def test_new_override_processors(self):
        # SnapSet.new can be given a custom set of processors.
        owner = self.factory.makePerson()
        snap = getUtility(ISnapSet).new(
            registrant=owner, owner=owner,
            distro_series=self.factory.makeDistroSeries(), name=u"snap",
            branch=self.factory.makeAnyBranch(), processors=[self.arm])
        self.assertContentEqual(
            ["arm"], [processor.name for processor in snap.processors])

    def test_set(self):
        # The property remembers its value correctly.
        snap = self.factory.makeSnap()
        snap.setProcessors([self.arm])
        self.assertContentEqual([self.arm], snap.processors)
        snap.setProcessors(self.unrestricted_procs + [self.arm])
        self.assertContentEqual(
            self.unrestricted_procs + [self.arm], snap.processors)
        snap.processors = []
        self.assertContentEqual([], snap.processors)
