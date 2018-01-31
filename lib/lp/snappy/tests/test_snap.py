# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap packages."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import json
from urlparse import urlsplit

from httmock import (
    all_requests,
    HTTMock,
    )
from lazr.lifecycle.event import ObjectModifiedEvent
from pymacaroons import Macaroon
import pytz
from storm.exceptions import LostObjectError
from storm.locals import Store
from testtools.matchers import (
    ContainsDict,
    Equals,
    Is,
    MatchesDict,
    MatchesSetwise,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import (
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.enums import PersonVisibility
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.config import config
from lp.services.database.constants import (
    ONE_DAY_AGO,
    UTC_NOW,
    )
from lp.services.database.sqlbase import flush_database_caches
from lp.services.features.testing import (
    FeatureFixture,
    MemoryFeatureFixture,
    )
from lp.services.log.logger import BufferLogger
from lp.services.propertycache import clear_property_cache
from lp.services.webapp.interfaces import OAuthPermission
from lp.snappy.interfaces.snap import (
    BadSnapSearchContext,
    CannotModifySnapProcessor,
    ISnap,
    ISnapSet,
    ISnapView,
    NoSourceForSnap,
    SNAP_TESTING_FLAGS,
    SnapBuildAlreadyPending,
    SnapBuildDisallowedArchitecture,
    SnapPrivacyMismatch,
    SnapPrivateFeatureDisabled,
    )
from lp.snappy.interfaces.snapbuild import (
    ISnapBuild,
    ISnapBuildSet,
    )
from lp.snappy.interfaces.snapbuildjob import ISnapStoreUploadJobSource
from lp.snappy.interfaces.snapstoreclient import ISnapStoreClient
from lp.snappy.model.snap import SnapSet
from lp.snappy.model.snapbuild import SnapFile
from lp.snappy.model.snapbuildjob import SnapBuildJob
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    api_url,
    login,
    logout,
    person_logged_in,
    record_two_runs,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.matchers import (
    DoesNotSnapshot,
    HasQueryCount,
    )
from lp.testing.pages import (
    LaunchpadWebServiceCaller,
    webservice_for_person,
    )


class TestSnapFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_private_feature_flag_disabled(self):
        # Without a private feature flag, we will not create new private Snaps.
        person = self.factory.makePerson()
        self.assertRaises(
            SnapPrivateFeatureDisabled, getUtility(ISnapSet).new,
            person, person, None, None,
            branch=self.factory.makeAnyBranch(), private=True)


class TestSnap(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnap, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_implements_interfaces(self):
        # Snap implements ISnap.
        snap = self.factory.makeSnap()
        with admin_logged_in():
            self.assertProvides(snap, ISnap)

    def test___repr__(self):
        # `Snap` objects have an informative __repr__.
        snap = self.factory.makeSnap()
        self.assertEqual(
            "<Snap ~%s/+snap/%s>" % (snap.owner.name, snap.name), repr(snap))

    def test_avoids_problematic_snapshots(self):
        self.assertThat(
            self.factory.makeSnap(),
            DoesNotSnapshot(
                ["builds", "completed_builds", "pending_builds"], ISnapView))

    def test_initial_date_last_modified(self):
        # The initial value of date_last_modified is date_created.
        snap = self.factory.makeSnap(date_created=ONE_DAY_AGO)
        self.assertEqual(snap.date_created, snap.date_last_modified)

    def test_modifiedevent_sets_date_last_modified(self):
        # When a Snap receives an object modified event, the last modified
        # date is set to UTC_NOW.
        snap = self.factory.makeSnap(date_created=ONE_DAY_AGO)
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
            PackagePublishingPocket.UPDATES)
        self.assertTrue(ISnapBuild.providedBy(build))
        self.assertEqual(snap.owner, build.requester)
        self.assertEqual(snap.distro_series.main_archive, build.archive)
        self.assertEqual(distroarchseries, build.distro_arch_series)
        self.assertEqual(PackagePublishingPocket.UPDATES, build.pocket)
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
        # Build requests have a relatively low queue score (2510).
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            processor=processor)
        snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor])
        build = snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.UPDATES)
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2510, queue_record.lastscore)

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
            PackagePublishingPocket.UPDATES)
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2610, queue_record.lastscore)

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
            PackagePublishingPocket.UPDATES)
        self.assertRaises(
            SnapBuildAlreadyPending, snap.requestBuild,
            snap.owner, snap.distro_series.main_archive, arches[0],
            PackagePublishingPocket.UPDATES)
        # We can build for a different archive.
        snap.requestBuild(
            snap.owner, self.factory.makeArchive(owner=snap.owner), arches[0],
            PackagePublishingPocket.UPDATES)
        # We can build for a different distroarchseries.
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, arches[1],
            PackagePublishingPocket.UPDATES)
        # Changing the status of the old build allows a new build.
        old_build.updateStatus(BuildStatus.BUILDING)
        old_build.updateStatus(BuildStatus.FULLYBUILT)
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, arches[0],
            PackagePublishingPocket.UPDATES)

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
            PackagePublishingPocket.UPDATES)
        self.assertRaises(
            SnapBuildDisallowedArchitecture, snap.requestBuild,
            snap.owner, snap.distro_series.main_archive, arches[1],
            PackagePublishingPocket.UPDATES)

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
                PackagePublishingPocket.UPDATES)
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
            PackagePublishingPocket.UPDATES)
        with admin_logged_in():
            snap.require_virtualized = False
        snap.requestBuild(
            snap.owner, snap.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.UPDATES)

    def test_requestAutoBuilds(self):
        # requestAutoBuilds creates new builds for all configured
        # architectures with appropriate parameters.
        distroseries = self.factory.makeDistroSeries()
        dases = []
        for _ in range(3):
            processor = self.factory.makeProcessor(supports_virtualized=True)
            dases.append(self.makeBuildableDistroArchSeries(
                distroseries=distroseries, processor=processor))
        archive = self.factory.makeArchive()
        snap = self.factory.makeSnap(
            distroseries=distroseries,
            processors=[das.processor for das in dases[:2]],
            auto_build_archive=archive,
            auto_build_pocket=PackagePublishingPocket.PROPOSED)
        with person_logged_in(snap.owner):
            builds = snap.requestAutoBuilds()
        self.assertThat(builds, MatchesSetwise(
            *(MatchesStructure.byEquality(
                requester=snap.owner, snap=snap, archive=archive,
                distro_arch_series=das,
                pocket=PackagePublishingPocket.PROPOSED)
              for das in dases[:2])))

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
            name="condemned")
        self.assertTrue(getUtility(ISnapSet).exists(owner, "condemned"))
        with person_logged_in(snap.owner):
            snap.destroySelf()
        self.assertFalse(getUtility(ISnapSet).exists(owner, "condemned"))

    def test_getBuildSummariesForSnapBuildIds(self):
        snap1 = self.factory.makeSnap()
        snap2 = self.factory.makeSnap()
        build11 = self.factory.makeSnapBuild(snap=snap1)
        build12 = self.factory.makeSnapBuild(snap=snap1)
        build2 = self.factory.makeSnapBuild(snap=snap2)
        self.factory.makeSnapBuild()
        summary1 = snap1.getBuildSummariesForSnapBuildIds(
            [build11.id, build12.id])
        summary2 = snap2.getBuildSummariesForSnapBuildIds([build2.id])
        summary_matcher = MatchesDict({
            "status": Equals("NEEDSBUILD"),
            "buildstate": Equals("Needs building"),
            "when_complete": Is(None),
            "when_complete_estimate": Is(False),
            "build_log_url": Is(None),
            "build_log_size": Is(None),
            })
        self.assertThat(summary1, MatchesDict({
            build11.id: summary_matcher,
            build12.id: summary_matcher,
            }))
        self.assertThat(summary2, MatchesDict({build2.id: summary_matcher}))

    def test_getBuildSummariesForSnapBuildIds_empty_input(self):
        snap = self.factory.makeSnap()
        self.factory.makeSnapBuild(snap=snap)
        self.assertEqual({}, snap.getBuildSummariesForSnapBuildIds(None))
        self.assertEqual({}, snap.getBuildSummariesForSnapBuildIds([]))
        self.assertEqual({}, snap.getBuildSummariesForSnapBuildIds(()))
        self.assertEqual({}, snap.getBuildSummariesForSnapBuildIds([None]))

    def test_getBuildSummariesForSnapBuildIds_not_matching_snap(self):
        # Should not return build summaries of other snaps.
        snap1 = self.factory.makeSnap()
        snap2 = self.factory.makeSnap()
        self.factory.makeSnapBuild(snap=snap1)
        build2 = self.factory.makeSnapBuild(snap=snap2)
        summary1 = snap1.getBuildSummariesForSnapBuildIds([build2.id])
        self.assertEqual({}, summary1)

    def test_getBuildSummariesForSnapBuildIds_when_complete_field(self):
        # Summary "when_complete" should be None unless estimate date or
        # finish date is available.
        snap = self.factory.makeSnap()
        build = self.factory.makeSnapBuild(snap=snap)
        self.assertIsNone(build.date)
        summary = snap.getBuildSummariesForSnapBuildIds([build.id])
        self.assertIsNone(summary[build.id]["when_complete"])
        removeSecurityProxy(build).date_finished = UTC_NOW
        summary = snap.getBuildSummariesForSnapBuildIds([build.id])
        self.assertEqual("a moment ago", summary[build.id]["when_complete"])

    def test_getBuildSummariesForSnapBuildIds_log_size_field(self):
        # Summary "build_log_size" should be None unless the build has a log.
        snap = self.factory.makeSnap()
        build = self.factory.makeSnapBuild(snap=snap)
        self.assertIsNone(build.log)
        summary = snap.getBuildSummariesForSnapBuildIds([build.id])
        self.assertIsNone(summary[build.id]["build_log_size"])
        removeSecurityProxy(build).log = self.factory.makeLibraryFileAlias(
            content=b'x' * 12345, db_only=True)
        summary = snap.getBuildSummariesForSnapBuildIds([build.id])
        self.assertEqual(12345, summary[build.id]["build_log_size"])

    def test_getBuildSummariesForSnapBuildIds_query_count(self):
        # DB query count should remain constant regardless of number of builds.
        def snap_build_creator(snap):
            build = self.factory.makeSnapBuild(snap=snap)
            removeSecurityProxy(build).log = self.factory.makeLibraryFileAlias(
                db_only=True)
            return build

        snap = self.factory.makeSnap()
        # Use an in-memory feature controller to avoid feature flag queries.
        with MemoryFeatureFixture({}):
            recorder1, recorder2 = record_two_runs(
                lambda: snap.getBuildSummariesForSnapBuildIds(
                    build.id for build in snap.builds),
                lambda: snap_build_creator(snap),
                1, 5)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))


class TestSnapDeleteWithBuilds(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapDeleteWithBuilds, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_delete_with_builds(self):
        # A snap package with builds can be deleted.  Doing so deletes all
        # its builds, their files, and any associated build jobs too.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, distroseries=distroseries,
            name="condemned")
        build = self.factory.makeSnapBuild(snap=snap)
        build_queue = build.queueBuild()
        snapfile = self.factory.makeSnapFile(snapbuild=build)
        snap_build_job = getUtility(ISnapStoreUploadJobSource).create(build)
        self.assertTrue(getUtility(ISnapSet).exists(owner, "condemned"))
        other_build = self.factory.makeSnapBuild()
        other_build.queueBuild()
        store = Store.of(build)
        store.flush()
        build_id = build.id
        build_queue_id = build_queue.id
        build_farm_job_id = removeSecurityProxy(build).build_farm_job_id
        snap_build_job_id = snap_build_job.job.job_id
        snapfile_id = removeSecurityProxy(snapfile).id
        with person_logged_in(snap.owner):
            snap.destroySelf()
        flush_database_caches()
        # The deleted snap and its builds are gone.
        self.assertFalse(getUtility(ISnapSet).exists(owner, "condemned"))
        self.assertIsNone(getUtility(ISnapBuildSet).getByID(build_id))
        self.assertIsNone(store.get(BuildQueue, build_queue_id))
        self.assertIsNone(store.get(BuildFarmJob, build_farm_job_id))
        self.assertIsNone(store.get(SnapFile, snapfile_id))
        self.assertIsNone(store.get(SnapBuildJob, snap_build_job_id))
        # Unrelated builds are still present.
        clear_property_cache(other_build)
        self.assertEqual(
            other_build, getUtility(ISnapBuildSet).getByID(other_build.id))
        self.assertIsNotNone(other_build.buildqueue_record)

    def test_related_webhooks_deleted(self):
        owner = self.factory.makePerson()
        snap = self.factory.makeSnap(registrant=owner, owner=owner)
        webhook = self.factory.makeWebhook(target=snap)
        with person_logged_in(snap.owner):
            webhook.ping()
            snap.destroySelf()
            transaction.commit()
            self.assertRaises(LostObjectError, getattr, webhook, "target")


class TestSnapSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapSet, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

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
            name=self.factory.getUniqueUnicode("snap-name"))
        if branch is None and git_ref is None:
            branch = self.factory.makeAnyBranch()
        if branch is not None:
            components["branch"] = branch
        else:
            components["git_ref"] = git_ref
        return components

    def test_creation_bzr(self):
        # The metadata entries supplied when a Snap is created for a Bazaar
        # branch are present on the new object.
        branch = self.factory.makeAnyBranch()
        components = self.makeSnapComponents(branch=branch)
        snap = getUtility(ISnapSet).new(**components)
        self.assertEqual(components["registrant"], snap.registrant)
        self.assertEqual(components["owner"], snap.owner)
        self.assertEqual(components["distro_series"], snap.distro_series)
        self.assertEqual(components["name"], snap.name)
        self.assertEqual(branch, snap.branch)
        self.assertIsNone(snap.git_repository)
        self.assertIsNone(snap.git_path)
        self.assertIsNone(snap.git_ref)
        self.assertFalse(snap.auto_build)
        self.assertIsNone(snap.auto_build_archive)
        self.assertIsNone(snap.auto_build_pocket)
        self.assertTrue(snap.require_virtualized)
        self.assertFalse(snap.private)
        self.assertTrue(snap.allow_network)

    def test_creation_git(self):
        # The metadata entries supplied when a Snap is created for a Git
        # branch are present on the new object.
        [ref] = self.factory.makeGitRefs()
        components = self.makeSnapComponents(git_ref=ref)
        snap = getUtility(ISnapSet).new(**components)
        self.assertEqual(components["registrant"], snap.registrant)
        self.assertEqual(components["owner"], snap.owner)
        self.assertEqual(components["distro_series"], snap.distro_series)
        self.assertEqual(components["name"], snap.name)
        self.assertIsNone(snap.branch)
        self.assertEqual(ref.repository, snap.git_repository)
        self.assertEqual(ref.path, snap.git_path)
        self.assertEqual(ref, snap.git_ref)
        self.assertFalse(snap.auto_build)
        self.assertIsNone(snap.auto_build_archive)
        self.assertIsNone(snap.auto_build_pocket)
        self.assertTrue(snap.require_virtualized)
        self.assertFalse(snap.private)
        self.assertTrue(snap.allow_network)

    def test_creation_git_url(self):
        # A Snap can be backed directly by a URL for an external Git
        # repository, rather than a Git repository hosted in Launchpad.
        ref = self.factory.makeGitRefRemote()
        components = self.makeSnapComponents(git_ref=ref)
        snap = getUtility(ISnapSet).new(**components)
        self.assertIsNone(snap.branch)
        self.assertIsNone(snap.git_repository)
        self.assertEqual(ref.repository_url, snap.git_repository_url)
        self.assertEqual(ref.path, snap.git_path)
        self.assertEqual(ref, snap.git_ref)

    def test_private_snap_for_public_sources(self):
        # Creating private snaps for public sources is allowed.
        [ref] = self.factory.makeGitRefs()
        components = self.makeSnapComponents(git_ref=ref)
        components['private'] = True
        snap = getUtility(ISnapSet).new(**components)
        with person_logged_in(components['owner']):
            self.assertTrue(snap.private)

    def test_private_git_requires_private_snap(self):
        # Snaps for a private Git branch cannot be public.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            [git_ref] = self.factory.makeGitRefs(
                owner=owner, information_type=InformationType.PRIVATESECURITY)
            components = dict(
                registrant=owner,
                owner=owner,
                git_ref=git_ref,
                distro_series=self.factory.makeDistroSeries(),
                name=self.factory.getUniqueUnicode("snap-name"),
            )
            self.assertRaises(
                SnapPrivacyMismatch, getUtility(ISnapSet).new, **components)

    def test_private_bzr_requires_private_snap(self):
        # Snaps for a private Bzr branch cannot be public.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            branch = self.factory.makeAnyBranch(
                owner=owner, information_type=InformationType.PRIVATESECURITY)
            components = dict(
                registrant=owner,
                owner=owner,
                branch=branch,
                distro_series=self.factory.makeDistroSeries(),
                name=self.factory.getUniqueUnicode("snap-name"),
            )
            self.assertRaises(
                SnapPrivacyMismatch, getUtility(ISnapSet).new, **components)

    def test_private_team_requires_private_snap(self):
        # Snaps owned by private teams cannot be public.
        registrant = self.factory.makePerson()
        with person_logged_in(registrant):
            private_team = self.factory.makeTeam(
                owner=registrant, visibility=PersonVisibility.PRIVATE)
            [git_ref] = self.factory.makeGitRefs()
            components = dict(
                registrant=registrant,
                owner=private_team,
                git_ref=git_ref,
                distro_series=self.factory.makeDistroSeries(),
                name=self.factory.getUniqueUnicode("snap-name"),
            )
            self.assertRaises(
                SnapPrivacyMismatch, getUtility(ISnapSet).new, **components)

    def test_creation_no_source(self):
        # Attempting to create a Snap with neither a Bazaar branch nor a Git
        # repository fails.
        registrant = self.factory.makePerson()
        self.assertRaises(
            NoSourceForSnap, getUtility(ISnapSet).new,
            registrant, registrant, self.factory.makeDistroSeries(),
            self.factory.getUniqueUnicode("snap-name"))

    def test_exists(self):
        # ISnapSet.exists checks for matching Snaps.
        snap = self.factory.makeSnap()
        self.assertTrue(getUtility(ISnapSet).exists(snap.owner, snap.name))
        self.assertFalse(
            getUtility(ISnapSet).exists(self.factory.makePerson(), snap.name))
        self.assertFalse(getUtility(ISnapSet).exists(snap.owner, "different"))

    def test_findByOwner(self):
        # ISnapSet.findByOwner returns all Snaps with the given owner.
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for owner in owners:
            for i in range(2):
                snaps.append(self.factory.makeSnap(
                    registrant=owner, owner=owner))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(snaps[:2], snap_set.findByOwner(owners[0]))
        self.assertContentEqual(snaps[2:], snap_set.findByOwner(owners[1]))

    def test_findByPerson(self):
        # ISnapSet.findByPerson returns all Snaps with the given owner or
        # based on branches or repositories with the given owner.
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for owner in owners:
            snaps.append(self.factory.makeSnap(registrant=owner, owner=owner))
            snaps.append(self.factory.makeSnap(
                branch=self.factory.makeAnyBranch(owner=owner)))
            [ref] = self.factory.makeGitRefs(owner=owner)
            snaps.append(self.factory.makeSnap(git_ref=ref))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(snaps[:3], snap_set.findByPerson(owners[0]))
        self.assertContentEqual(snaps[3:], snap_set.findByPerson(owners[1]))

    def test_findByProject(self):
        # ISnapSet.findByProject returns all Snaps based on branches or
        # repositories for the given project.
        projects = [self.factory.makeProduct() for i in range(2)]
        snaps = []
        for project in projects:
            snaps.append(self.factory.makeSnap(
                branch=self.factory.makeProductBranch(product=project)))
            [ref] = self.factory.makeGitRefs(target=project)
            snaps.append(self.factory.makeSnap(git_ref=ref))
        snaps.append(self.factory.makeSnap(
            branch=self.factory.makePersonalBranch()))
        [ref] = self.factory.makeGitRefs(target=None)
        snaps.append(self.factory.makeSnap(git_ref=ref))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(snaps[:2], snap_set.findByProject(projects[0]))
        self.assertContentEqual(
            snaps[2:4], snap_set.findByProject(projects[1]))

    def test_findByBranch(self):
        # ISnapSet.findByBranch returns all Snaps with the given Bazaar branch.
        branches = [self.factory.makeAnyBranch() for i in range(2)]
        snaps = []
        for branch in branches:
            for i in range(2):
                snaps.append(self.factory.makeSnap(branch=branch))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(snaps[:2], snap_set.findByBranch(branches[0]))
        self.assertContentEqual(snaps[2:], snap_set.findByBranch(branches[1]))

    def test_findByGitRepository(self):
        # ISnapSet.findByGitRepository returns all Snaps with the given Git
        # repository.
        repositories = [self.factory.makeGitRepository() for i in range(2)]
        snaps = []
        for repository in repositories:
            for i in range(2):
                [ref] = self.factory.makeGitRefs(repository=repository)
                snaps.append(self.factory.makeSnap(git_ref=ref))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(
            snaps[:2], snap_set.findByGitRepository(repositories[0]))
        self.assertContentEqual(
            snaps[2:], snap_set.findByGitRepository(repositories[1]))

    def test_findByGitRepository_paths(self):
        # ISnapSet.findByGitRepository can restrict by reference paths.
        repositories = [self.factory.makeGitRepository() for i in range(2)]
        snaps = []
        for repository in repositories:
            for i in range(3):
                [ref] = self.factory.makeGitRefs(repository=repository)
                snaps.append(self.factory.makeSnap(git_ref=ref))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(
            [], snap_set.findByGitRepository(repositories[0], paths=[]))
        self.assertContentEqual(
            [snaps[0]],
            snap_set.findByGitRepository(
                repositories[0], paths=[snaps[0].git_ref.path]))
        self.assertContentEqual(
            snaps[:2],
            snap_set.findByGitRepository(
                repositories[0],
                paths=[snaps[0].git_ref.path, snaps[1].git_ref.path]))

    def test_findByGitRef(self):
        # ISnapSet.findByGitRef returns all Snaps with the given Git
        # reference.
        repositories = [self.factory.makeGitRepository() for i in range(2)]
        refs = []
        snaps = []
        for repository in repositories:
            refs.extend(self.factory.makeGitRefs(
                paths=["refs/heads/master", "refs/heads/other"]))
            snaps.append(self.factory.makeSnap(git_ref=refs[-2]))
            snaps.append(self.factory.makeSnap(git_ref=refs[-1]))
        snap_set = getUtility(ISnapSet)
        for ref, snap in zip(refs, snaps):
            self.assertContentEqual([snap], snap_set.findByGitRef(ref))

    def test_findByContext(self):
        # ISnapSet.findByContext returns all Snaps with the given context.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        branch = self.factory.makeProductBranch(owner=person, product=project)
        other_branch = self.factory.makeProductBranch()
        repository = self.factory.makeGitRepository(target=project)
        refs = self.factory.makeGitRefs(
            repository=repository,
            paths=["refs/heads/master", "refs/heads/other"])
        snaps = []
        snaps.append(self.factory.makeSnap(branch=branch))
        snaps.append(self.factory.makeSnap(branch=other_branch))
        snaps.append(
            self.factory.makeSnap(
                registrant=person, owner=person, git_ref=refs[0]))
        snaps.append(self.factory.makeSnap(git_ref=refs[1]))
        snap_set = getUtility(ISnapSet)
        self.assertContentEqual(
            [snaps[0], snaps[2]], snap_set.findByContext(person))
        self.assertContentEqual(
            [snaps[0], snaps[2], snaps[3]], snap_set.findByContext(project))
        self.assertContentEqual([snaps[0]], snap_set.findByContext(branch))
        self.assertContentEqual(snaps[2:], snap_set.findByContext(repository))
        self.assertContentEqual([snaps[2]], snap_set.findByContext(refs[0]))
        self.assertRaises(
            BadSnapSearchContext, snap_set.findByContext,
            self.factory.makeDistribution())

    def test_findByURL(self):
        # ISnapSet.findByURL returns visible Snaps with the given URL.
        urls = ["https://git.example.org/foo", "https://git.example.org/bar"]
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for url in urls:
            for owner in owners:
                snaps.append(self.factory.makeSnap(
                    registrant=owner, owner=owner,
                    git_ref=self.factory.makeGitRefRemote(repository_url=url)))
        snaps.append(
            self.factory.makeSnap(branch=self.factory.makeAnyBranch()))
        snaps.append(
            self.factory.makeSnap(git_ref=self.factory.makeGitRefs()[0]))
        self.assertContentEqual(
            snaps[:2], getUtility(ISnapSet).findByURL(urls[0]))
        self.assertContentEqual(
            [snaps[0]],
            getUtility(ISnapSet).findByURL(urls[0], owner=owners[0]))

    def test_findByURLPrefix(self):
        # ISnapSet.findByURLPrefix returns visible Snaps with the given URL
        # prefix.
        urls = [
            "https://git.example.org/foo/a",
            "https://git.example.org/foo/b",
            "https://git.example.org/bar",
            ]
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for url in urls:
            for owner in owners:
                snaps.append(self.factory.makeSnap(
                    registrant=owner, owner=owner,
                    git_ref=self.factory.makeGitRefRemote(repository_url=url)))
        snaps.append(
            self.factory.makeSnap(branch=self.factory.makeAnyBranch()))
        snaps.append(
            self.factory.makeSnap(git_ref=self.factory.makeGitRefs()[0]))
        prefix = "https://git.example.org/foo/"
        self.assertContentEqual(
            snaps[:4], getUtility(ISnapSet).findByURLPrefix(prefix))
        self.assertContentEqual(
            [snaps[0], snaps[2]],
            getUtility(ISnapSet).findByURLPrefix(prefix, owner=owners[0]))

    def test_findByURLPrefixes(self):
        # ISnapSet.findByURLPrefixes returns visible Snaps with any of the
        # given URL prefixes.
        urls = [
            "https://git.example.org/foo/a",
            "https://git.example.org/foo/b",
            "https://git.example.org/bar/a",
            "https://git.example.org/bar/b",
            "https://git.example.org/baz",
            ]
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for url in urls:
            for owner in owners:
                snaps.append(self.factory.makeSnap(
                    registrant=owner, owner=owner,
                    git_ref=self.factory.makeGitRefRemote(repository_url=url)))
        snaps.append(
            self.factory.makeSnap(branch=self.factory.makeAnyBranch()))
        snaps.append(
            self.factory.makeSnap(git_ref=self.factory.makeGitRefs()[0]))
        prefixes = [
            "https://git.example.org/foo/", "https://git.example.org/bar/"]
        self.assertContentEqual(
            snaps[:8], getUtility(ISnapSet).findByURLPrefixes(prefixes))
        self.assertContentEqual(
            [snaps[0], snaps[2], snaps[4], snaps[6]],
            getUtility(ISnapSet).findByURLPrefixes(prefixes, owner=owners[0]))

    def test__findStaleSnaps(self):
        # Stale; not built automatically.
        self.factory.makeSnap(is_stale=True)
        # Not stale; built automatically.
        self.factory.makeSnap(auto_build=True, is_stale=False)
        # Stale; built automatically.
        stale_daily = self.factory.makeSnap(auto_build=True, is_stale=True)
        self.assertContentEqual([stale_daily], SnapSet._findStaleSnaps())

    def test__findStaleSnapsDistinct(self):
        # If a snap package has two builds due to two architectures, it only
        # returns one recipe.
        distroseries = self.factory.makeDistroSeries()
        dases = [
            self.factory.makeDistroArchSeries(distroseries=distroseries)
            for _ in range(2)]
        snap = self.factory.makeSnap(
            distroseries=distroseries,
            processors=[das.processor for das in dases],
            auto_build=True, is_stale=True)
        for das in dases:
            self.factory.makeSnapBuild(
                requester=snap.owner, snap=snap,
                archive=snap.auto_build_archive, distroarchseries=das,
                pocket=snap.auto_build_pocket,
                date_created=(datetime.now(pytz.UTC) - timedelta(days=2)))
        self.assertContentEqual([snap], SnapSet._findStaleSnaps())

    def makeBuildableDistroArchSeries(self, **kwargs):
        das = self.factory.makeDistroArchSeries(**kwargs)
        fake_chroot = self.factory.makeLibraryFileAlias(
            filename="fake_chroot.tar.gz", db_only=True)
        das.addOrUpdateChroot(fake_chroot)
        return das

    def makeAutoBuildableSnap(self, **kwargs):
        processor = self.factory.makeProcessor(supports_virtualized=True)
        das = self.makeBuildableDistroArchSeries(processor=processor)
        snap = self.factory.makeSnap(
            distroseries=das.distroseries, processors=[das.processor],
            auto_build=True, **kwargs)
        return das, snap

    def test_makeAutoBuilds(self):
        # ISnapSet.makeAutoBuilds requests builds of
        # appropriately-configured Snaps where possible.
        self.assertEqual([], getUtility(ISnapSet).makeAutoBuilds())
        das, snap = self.makeAutoBuildableSnap(is_stale=True)
        logger = BufferLogger()
        [build] = getUtility(ISnapSet).makeAutoBuilds(logger=logger)
        self.assertThat(build, MatchesStructure.byEquality(
            requester=snap.owner, snap=snap, distro_arch_series=das,
            status=BuildStatus.NEEDSBUILD,
            ))
        expected_log_entries = [
            "DEBUG Scheduling builds of snap package %s/%s" % (
                snap.owner.name, snap.name),
            "DEBUG  - %s/%s/%s: Build requested." % (
                snap.owner.name, snap.name, das.architecturetag),
            ]
        self.assertEqual(
            expected_log_entries, logger.getLogBuffer().splitlines())
        self.assertFalse(snap.is_stale)

    def test_makeAutoBuilds_skips_if_built_recently(self):
        # ISnapSet.makeAutoBuilds skips snap packages that have been built
        # recently.
        das, snap = self.makeAutoBuildableSnap(is_stale=True)
        self.factory.makeSnapBuild(
            requester=snap.owner, snap=snap, archive=snap.auto_build_archive,
            distroarchseries=das)
        logger = BufferLogger()
        builds = getUtility(ISnapSet).makeAutoBuilds(logger=logger)
        self.assertEqual([], builds)
        self.assertEqual([], logger.getLogBuffer().splitlines())

    def test_makeAutoBuilds_skips_non_stale_snaps(self):
        # ISnapSet.makeAutoBuilds skips snap packages that are not stale.
        das, snap = self.makeAutoBuildableSnap(is_stale=False)
        self.assertEqual([], getUtility(ISnapSet).makeAutoBuilds())

    def test_makeAutoBuilds_skips_pending(self):
        # ISnapSet.makeAutoBuilds skips snap packages that already have
        # pending builds.
        das, snap = self.makeAutoBuildableSnap(is_stale=True)
        # Simulate very long build farm queues so that this case isn't
        # filtered out earlier.
        self.factory.makeSnapBuild(
            requester=snap.owner, snap=snap, archive=snap.auto_build_archive,
            distroarchseries=das,
            date_created=datetime.now(pytz.UTC) - timedelta(days=1))
        logger = BufferLogger()
        builds = getUtility(ISnapSet).makeAutoBuilds(logger=logger)
        self.assertEqual([], builds)
        expected_log_entries = [
            "DEBUG Scheduling builds of snap package %s/%s" % (
                snap.owner.name, snap.name),
            "WARNING  - %s/%s/%s: An identical build of this snap package "
            "is already pending." % (
                snap.owner.name, snap.name, das.architecturetag),
            ]
        self.assertEqual(
            expected_log_entries, logger.getLogBuffer().splitlines())

    def test_makeAutoBuilds_with_older_build(self):
        # If a previous build is not recent and the snap package is stale,
        # ISnapSet.makeAutoBuilds requests builds.
        das, snap = self.makeAutoBuildableSnap(is_stale=True)
        self.factory.makeSnapBuild(
            requester=snap.owner, snap=snap, archive=snap.auto_build_archive,
            distroarchseries=das,
            date_created=datetime.now(pytz.UTC) - timedelta(days=1),
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=1))
        builds = getUtility(ISnapSet).makeAutoBuilds()
        self.assertEqual(1, len(builds))

    def test_makeAutoBuilds_with_older_and_newer_builds(self):
        # If a snap package has been built twice, and the most recent build
        # is too recent, ISnapSet.makeAutoBuilds does not request builds.
        das, snap = self.makeAutoBuildableSnap(is_stale=True)
        for timediff in timedelta(days=1), timedelta(minutes=30):
            self.factory.makeSnapBuild(
                requester=snap.owner, snap=snap,
                archive=snap.auto_build_archive, distroarchseries=das,
                date_created=datetime.now(pytz.UTC) - timediff,
                status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=1))
        self.assertEqual([], getUtility(ISnapSet).makeAutoBuilds())

    def test_makeAutoBuilds_with_recent_build_from_different_archive(self):
        # If a snap package has been built recently but from an archive
        # other than the auto_build_archive, ISnapSet.makeAutoBuilds
        # requests builds.
        das, snap = self.makeAutoBuildableSnap(is_stale=True)
        self.factory.makeSnapBuild(
            requester=snap.owner, snap=snap, distroarchseries=das,
            date_created=datetime.now(pytz.UTC) - timedelta(minutes=30),
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=1))
        builds = getUtility(ISnapSet).makeAutoBuilds()
        self.assertEqual(1, len(builds))

    def test_detachFromBranch(self):
        # ISnapSet.detachFromBranch clears the given Bazaar branch from all
        # Snaps.
        branches = [self.factory.makeAnyBranch() for i in range(2)]
        snaps = []
        for branch in branches:
            for i in range(2):
                snaps.append(self.factory.makeSnap(
                    branch=branch, date_created=ONE_DAY_AGO))
        getUtility(ISnapSet).detachFromBranch(branches[0])
        self.assertEqual(
            [None, None, branches[1], branches[1]],
            [snap.branch for snap in snaps])
        for snap in snaps[:2]:
            self.assertSqlAttributeEqualsDate(
                snap, "date_last_modified", UTC_NOW)

    def test_detachFromGitRepository(self):
        # ISnapSet.detachFromGitRepository clears the given Git repository
        # from all Snaps.
        repositories = [self.factory.makeGitRepository() for i in range(2)]
        snaps = []
        paths = []
        refs = []
        for repository in repositories:
            for i in range(2):
                [ref] = self.factory.makeGitRefs(repository=repository)
                paths.append(ref.path)
                refs.append(ref)
                snaps.append(self.factory.makeSnap(
                    git_ref=ref, date_created=ONE_DAY_AGO))
        getUtility(ISnapSet).detachFromGitRepository(repositories[0])
        self.assertEqual(
            [None, None, repositories[1], repositories[1]],
            [snap.git_repository for snap in snaps])
        self.assertEqual(
            [None, None, paths[2], paths[3]],
            [snap.git_path for snap in snaps])
        self.assertEqual(
            [None, None, refs[2], refs[3]], [snap.git_ref for snap in snaps])
        for snap in snaps[:2]:
            self.assertSqlAttributeEqualsDate(
                snap, "date_last_modified", UTC_NOW)


class TestSnapProcessors(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapProcessors, self).setUp(user="foo.bar@canonical.com")
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
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
            distro_series=self.factory.makeDistroSeries(), name="snap",
            branch=self.factory.makeAnyBranch())
        self.assertContentEqual(
            ["386", "amd64", "hppa", "default"],
            [processor.name for processor in snap.processors])

    def test_new_override_processors(self):
        # SnapSet.new can be given a custom set of processors.
        owner = self.factory.makePerson()
        snap = getUtility(ISnapSet).new(
            registrant=owner, owner=owner,
            distro_series=self.factory.makeDistroSeries(), name="snap",
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
        snap.setProcessors([])
        self.assertContentEqual([], snap.processors)

    def test_set_non_admin(self):
        """Non-admins can only enable or disable unrestricted processors."""
        snap = self.factory.makeSnap()
        snap.setProcessors(self.default_procs)
        self.assertContentEqual(self.default_procs, snap.processors)
        with person_logged_in(snap.owner) as owner:
            # Adding arm is forbidden ...
            self.assertRaises(
                CannotModifySnapProcessor, snap.setProcessors,
                [self.default_procs[0], self.arm],
                check_permissions=True, user=owner)
            # ... but removing amd64 is OK.
            snap.setProcessors(
                [self.default_procs[0]], check_permissions=True, user=owner)
            self.assertContentEqual([self.default_procs[0]], snap.processors)
        with admin_logged_in() as admin:
            snap.setProcessors(
                [self.default_procs[0], self.arm],
                check_permissions=True, user=admin)
            self.assertContentEqual(
                [self.default_procs[0], self.arm], snap.processors)
        with person_logged_in(snap.owner) as owner:
            hppa = getUtility(IProcessorSet).getByName("hppa")
            self.assertFalse(hppa.restricted)
            # Adding hppa while removing arm is forbidden ...
            self.assertRaises(
                CannotModifySnapProcessor, snap.setProcessors,
                [self.default_procs[0], hppa],
                check_permissions=True, user=owner)
            # ... but adding hppa while retaining arm is OK.
            snap.setProcessors(
                [self.default_procs[0], self.arm, hppa],
                check_permissions=True, user=owner)
            self.assertContentEqual(
                [self.default_procs[0], self.arm, hppa], snap.processors)


class TestSnapWebservice(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapWebservice, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
        self.snap_store_client = FakeMethod()
        self.snap_store_client.listChannels = FakeMethod(result=[
            {"name": "stable", "display_name": "Stable"},
            {"name": "edge", "display_name": "Edge"},
            ])
        self.snap_store_client.requestPackageUploadPermission = (
            getUtility(ISnapStoreClient).requestPackageUploadPermission)
        self.useFixture(
            ZopeUtilityFixture(self.snap_store_client, ISnapStoreClient))
        self.person = self.factory.makePerson(displayname="Test Person")
        self.webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PUBLIC)
        self.webservice.default_api_version = "devel"
        login(ANONYMOUS)

    def getURL(self, obj):
        return self.webservice.getAbsoluteUrl(api_url(obj))

    def makeSnap(self, owner=None, distroseries=None, branch=None,
                 git_ref=None, processors=None, webservice=None,
                 private=False, auto_build_archive=None,
                 auto_build_pocket=None, **kwargs):
        if owner is None:
            owner = self.person
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries(registrant=owner)
        if branch is None and git_ref is None:
            branch = self.factory.makeAnyBranch()
        if webservice is None:
            webservice = self.webservice
        transaction.commit()
        distroseries_url = api_url(distroseries)
        owner_url = api_url(owner)
        if branch is not None:
            kwargs["branch"] = api_url(branch)
        if git_ref is not None:
            kwargs["git_ref"] = api_url(git_ref)
        if processors is not None:
            kwargs["processors"] = [
                api_url(processor) for processor in processors]
        if auto_build_archive is not None:
            kwargs["auto_build_archive"] = api_url(auto_build_archive)
        if auto_build_pocket is not None:
            kwargs["auto_build_pocket"] = auto_build_pocket.title
        logout()
        response = webservice.named_post(
            "/+snaps", "new", owner=owner_url, distro_series=distroseries_url,
            name="mir", private=private, **kwargs)
        self.assertEqual(201, response.status)
        return webservice.get(response.getHeader("Location")).jsonBody()

    def getCollectionLinks(self, entry, member):
        """Return a list of self_link attributes of entries in a collection."""
        collection = self.webservice.get(
            entry["%s_collection_link" % member]).jsonBody()
        return [entry["self_link"] for entry in collection["entries"]]

    def test_new_bzr(self):
        # Ensure Snap creation based on a Bazaar branch works.
        team = self.factory.makeTeam(owner=self.person)
        distroseries = self.factory.makeDistroSeries(registrant=team)
        branch = self.factory.makeAnyBranch()
        snap = self.makeSnap(
            owner=team, distroseries=distroseries, branch=branch)
        with person_logged_in(self.person):
            self.assertEqual(self.getURL(self.person), snap["registrant_link"])
            self.assertEqual(self.getURL(team), snap["owner_link"])
            self.assertEqual(
                self.getURL(distroseries), snap["distro_series_link"])
            self.assertEqual("mir", snap["name"])
            self.assertEqual(self.getURL(branch), snap["branch_link"])
            self.assertIsNone(snap["git_repository_link"])
            self.assertIsNone(snap["git_path"])
            self.assertIsNone(snap["git_ref_link"])
            self.assertTrue(snap["require_virtualized"])
            self.assertTrue(snap["allow_network"])

    def test_new_git(self):
        # Ensure Snap creation based on a Git branch works.
        team = self.factory.makeTeam(owner=self.person)
        distroseries = self.factory.makeDistroSeries(registrant=team)
        [ref] = self.factory.makeGitRefs()
        snap = self.makeSnap(
            owner=team, distroseries=distroseries, git_ref=ref)
        with person_logged_in(self.person):
            self.assertEqual(self.getURL(self.person), snap["registrant_link"])
            self.assertEqual(self.getURL(team), snap["owner_link"])
            self.assertEqual(
                self.getURL(distroseries), snap["distro_series_link"])
            self.assertEqual("mir", snap["name"])
            self.assertIsNone(snap["branch_link"])
            self.assertEqual(
                self.getURL(ref.repository), snap["git_repository_link"])
            self.assertEqual(ref.path, snap["git_path"])
            self.assertEqual(self.getURL(ref), snap["git_ref_link"])
            self.assertTrue(snap["require_virtualized"])
            self.assertTrue(snap["allow_network"])

    def test_new_private(self):
        # Ensure private Snap creation works.
        team = self.factory.makeTeam(owner=self.person)
        distroseries = self.factory.makeDistroSeries(registrant=team)
        [ref] = self.factory.makeGitRefs()
        private_webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PRIVATE)
        private_webservice.default_api_version = "devel"
        login(ANONYMOUS)
        snap = self.makeSnap(
            owner=team, distroseries=distroseries, git_ref=ref,
            webservice=private_webservice, private=True)
        with person_logged_in(self.person):
            self.assertTrue(snap["private"])

    def test_new_store_options(self):
        # Ensure store-related options in Snap.new work.
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        store_name = self.factory.getUniqueUnicode()
        snap = self.makeSnap(
            store_upload=True, store_series=api_url(snappy_series),
            store_name=store_name, store_channels=["edge"])
        with person_logged_in(self.person):
            self.assertTrue(snap["store_upload"])
            self.assertEqual(
                self.getURL(snappy_series), snap["store_series_link"])
            self.assertEqual(store_name, snap["store_name"])
            self.assertEqual(["edge"], snap["store_channels"])

    def test_duplicate(self):
        # An attempt to create a duplicate Snap fails.
        team = self.factory.makeTeam(owner=self.person)
        branch = self.factory.makeAnyBranch()
        branch_url = api_url(branch)
        self.makeSnap(owner=team)
        with person_logged_in(self.person):
            owner_url = api_url(team)
            distroseries_url = api_url(self.factory.makeDistroSeries())
        response = self.webservice.named_post(
            "/+snaps", "new", owner=owner_url, distro_series=distroseries_url,
            name="mir", branch=branch_url)
        self.assertEqual(400, response.status)
        self.assertEqual(
            "There is already a snap package with the same name and owner.",
            response.body)

    def test_not_owner(self):
        # If the registrant is not the owner or a member of the owner team,
        # Snap creation fails.
        other_person = self.factory.makePerson(displayname="Other Person")
        other_team = self.factory.makeTeam(
            owner=other_person, displayname="Other Team")
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        branch = self.factory.makeAnyBranch()
        transaction.commit()
        other_person_url = api_url(other_person)
        other_team_url = api_url(other_team)
        distroseries_url = api_url(distroseries)
        branch_url = api_url(branch)
        logout()
        response = self.webservice.named_post(
            "/+snaps", "new", owner=other_person_url,
            distro_series=distroseries_url, name="dummy", branch=branch_url)
        self.assertEqual(401, response.status)
        self.assertEqual(
            "Test Person cannot create snap packages owned by Other Person.",
            response.body)
        response = self.webservice.named_post(
            "/+snaps", "new", owner=other_team_url,
            distro_series=distroseries_url, name="dummy", branch=branch_url)
        self.assertEqual(401, response.status)
        self.assertEqual(
            "Test Person is not a member of Other Team.", response.body)

    def test_cannot_set_git_path_for_bzr(self):
        # Setting git_path on a Bazaar-based Snap fails.
        snap = self.makeSnap(branch=self.factory.makeAnyBranch())
        response = self.webservice.patch(
            snap["self_link"], "application/json",
            json.dumps({"git_path": "HEAD"}))
        self.assertEqual(400, response.status)

    def test_cannot_set_git_path_to_None(self):
        # Setting git_path to None fails.
        snap = self.makeSnap(git_ref=self.factory.makeGitRefs()[0])
        response = self.webservice.patch(
            snap["self_link"], "application/json",
            json.dumps({"git_path": None}))
        self.assertEqual(400, response.status)

    def test_set_git_path(self):
        # Setting git_path on a Git-based Snap works.
        ref_master, ref_next = self.factory.makeGitRefs(
            paths=["refs/heads/master", "refs/heads/next"])
        snap = self.makeSnap(git_ref=ref_master)
        response = self.webservice.patch(
            snap["self_link"], "application/json",
            json.dumps({"git_path": ref_next.path}))
        self.assertEqual(209, response.status)
        self.assertThat(response.jsonBody(), ContainsDict({
            "git_repository_link": Equals(snap["git_repository_link"]),
            "git_path": Equals(ref_next.path),
            }))

    def test_set_git_path_external(self):
        # Setting git_path on a Snap backed by an external Git repository
        # works.
        ref = self.factory.makeGitRefRemote()
        repository_url = ref.repository_url
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person, git_ref=ref)
        snap_url = api_url(snap)
        logout()
        response = self.webservice.patch(
            snap_url, "application/json", json.dumps({"git_path": "HEAD"}))
        self.assertEqual(209, response.status)
        self.assertThat(response.jsonBody(), ContainsDict({
            "git_repository_url": Equals(repository_url),
            "git_path": Equals("HEAD"),
            }))

    def test_getByName(self):
        # lp.snaps.getByName returns a matching Snap.
        snap = self.makeSnap()
        with person_logged_in(self.person):
            owner_url = api_url(self.person)
        response = self.webservice.named_get(
            "/+snaps", "getByName", owner=owner_url, name="mir")
        self.assertEqual(200, response.status)
        self.assertEqual(snap, response.jsonBody())

    def test_getByName_missing(self):
        # lp.snaps.getByName returns 404 for a non-existent Snap.
        logout()
        with person_logged_in(self.person):
            owner_url = api_url(self.person)
        response = self.webservice.named_get(
            "/+snaps", "getByName", owner=owner_url, name="nonexistent")
        self.assertEqual(404, response.status)
        self.assertEqual(
            "No such snap package with this owner: 'nonexistent'.",
            response.body)

    def test_findByURL(self):
        # lp.snaps.findByURL returns visible Snaps with the given URL.
        persons = [self.factory.makePerson(), self.factory.makePerson()]
        urls = ["https://git.example.org/foo", "https://git.example.org/bar"]
        snaps = []
        for url in urls:
            for person in persons:
                for private in (False, True):
                    ref = self.factory.makeGitRefRemote(repository_url=url)
                    snaps.append(self.factory.makeSnap(
                        registrant=person, owner=person, git_ref=ref,
                        private=private))
        with admin_logged_in():
            person_urls = [api_url(person) for person in persons]
            ws_snaps = [
                self.webservice.getAbsoluteUrl(api_url(snap))
                for snap in snaps]
        commercial_admin = (
            getUtility(ILaunchpadCelebrities).commercial_admin.teamowner)
        logout()
        # Anonymous requests can only see public snaps.
        anon_webservice = LaunchpadWebServiceCaller("test", "")
        response = anon_webservice.named_get(
            "/+snaps", "findByURL", url=urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[0], ws_snaps[2]],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = anon_webservice.named_get(
            "/+snaps", "findByURL", url=urls[0], owner=person_urls[0],
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[0]],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        # persons[0] can see both public snaps with this URL, as well as
        # their own private snap.
        webservice = webservice_for_person(
            persons[0], permission=OAuthPermission.READ_PRIVATE)
        response = webservice.named_get(
            "/+snaps", "findByURL", url=urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ws_snaps[:3],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = webservice.named_get(
            "/+snaps", "findByURL", url=urls[0], owner=person_urls[0],
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ws_snaps[:2],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        # Admins can see all snaps with this URL.
        commercial_admin_webservice = webservice_for_person(
            commercial_admin, permission=OAuthPermission.READ_PRIVATE)
        response = commercial_admin_webservice.named_get(
            "/+snaps", "findByURL", url=urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ws_snaps[:4],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = commercial_admin_webservice.named_get(
            "/+snaps", "findByURL", url=urls[0], owner=person_urls[0],
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ws_snaps[:2],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])

    def test_findByURLPrefix(self):
        # lp.snaps.findByURLPrefix returns visible Snaps with the given URL
        # prefix.
        self.pushConfig("launchpad", default_batch_size=10)
        persons = [self.factory.makePerson(), self.factory.makePerson()]
        urls = [
            "https://git.example.org/foo/a",
            "https://git.example.org/foo/b",
            "https://git.example.org/bar",
            ]
        snaps = []
        for url in urls:
            for person in persons:
                for private in (False, True):
                    ref = self.factory.makeGitRefRemote(repository_url=url)
                    snaps.append(self.factory.makeSnap(
                        registrant=person, owner=person, git_ref=ref,
                        private=private))
        with admin_logged_in():
            person_urls = [api_url(person) for person in persons]
            ws_snaps = [
                self.webservice.getAbsoluteUrl(api_url(snap))
                for snap in snaps]
        commercial_admin = (
            getUtility(ILaunchpadCelebrities).commercial_admin.teamowner)
        logout()
        prefix = "https://git.example.org/foo/"
        # Anonymous requests can only see public snaps.
        anon_webservice = LaunchpadWebServiceCaller("test", "")
        response = anon_webservice.named_get(
            "/+snaps", "findByURLPrefix", url_prefix=prefix,
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 2, 4, 6)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = anon_webservice.named_get(
            "/+snaps", "findByURLPrefix", url_prefix=prefix,
            owner=person_urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 4)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        # persons[0] can see all public snaps with this URL prefix, as well
        # as their own matching private snaps.
        webservice = webservice_for_person(
            persons[0], permission=OAuthPermission.READ_PRIVATE)
        response = webservice.named_get(
            "/+snaps", "findByURLPrefix", url_prefix=prefix,
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 1, 2, 4, 5, 6)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = webservice.named_get(
            "/+snaps", "findByURLPrefix", url_prefix=prefix,
            owner=person_urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 1, 4, 5)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        # Admins can see all snaps with this URL prefix.
        commercial_admin_webservice = webservice_for_person(
            commercial_admin, permission=OAuthPermission.READ_PRIVATE)
        response = commercial_admin_webservice.named_get(
            "/+snaps", "findByURLPrefix", url_prefix=prefix,
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ws_snaps[:8],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = commercial_admin_webservice.named_get(
            "/+snaps", "findByURLPrefix", url_prefix=prefix,
            owner=person_urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 1, 4, 5)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])

    def test_findByURLPrefixes(self):
        # lp.snaps.findByURLPrefixes returns visible Snaps with any of the
        # given URL prefixes.
        self.pushConfig("launchpad", default_batch_size=20)
        persons = [self.factory.makePerson(), self.factory.makePerson()]
        urls = [
            "https://git.example.org/foo/a",
            "https://git.example.org/foo/b",
            "https://git.example.org/bar/a",
            "https://git.example.org/bar/b",
            "https://git.example.org/baz",
            ]
        snaps = []
        for url in urls:
            for person in persons:
                for private in (False, True):
                    ref = self.factory.makeGitRefRemote(repository_url=url)
                    snaps.append(self.factory.makeSnap(
                        registrant=person, owner=person, git_ref=ref,
                        private=private))
        with admin_logged_in():
            person_urls = [api_url(person) for person in persons]
            ws_snaps = [
                self.webservice.getAbsoluteUrl(api_url(snap))
                for snap in snaps]
        commercial_admin = (
            getUtility(ILaunchpadCelebrities).commercial_admin.teamowner)
        logout()
        prefixes = [
            "https://git.example.org/foo/", "https://git.example.org/bar/"]
        # Anonymous requests can only see public snaps.
        anon_webservice = LaunchpadWebServiceCaller("test", "")
        response = anon_webservice.named_get(
            "/+snaps", "findByURLPrefixes", url_prefixes=prefixes,
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 2, 4, 6, 8, 10, 12, 14)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = anon_webservice.named_get(
            "/+snaps", "findByURLPrefixes", url_prefixes=prefixes,
            owner=person_urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 4, 8, 12)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        # persons[0] can see all public snaps with any of these URL
        # prefixes, as well as their own matching private snaps.
        webservice = webservice_for_person(
            persons[0], permission=OAuthPermission.READ_PRIVATE)
        response = webservice.named_get(
            "/+snaps", "findByURLPrefixes", url_prefixes=prefixes,
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = webservice.named_get(
            "/+snaps", "findByURLPrefixes", url_prefixes=prefixes,
            owner=person_urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 1, 4, 5, 8, 9, 12, 13)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        # Admins can see all snaps with any of these URL prefixes.
        commercial_admin_webservice = webservice_for_person(
            commercial_admin, permission=OAuthPermission.READ_PRIVATE)
        response = commercial_admin_webservice.named_get(
            "/+snaps", "findByURLPrefixes", url_prefixes=prefixes,
            api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ws_snaps[:16],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])
        response = commercial_admin_webservice.named_get(
            "/+snaps", "findByURLPrefixes", url_prefixes=prefixes,
            owner=person_urls[0], api_version="devel")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [ws_snaps[i] for i in (0, 1, 4, 5, 8, 9, 12, 13)],
            [entry["self_link"] for entry in response.jsonBody()["entries"]])

    def setProcessors(self, user, snap, names):
        ws = webservice_for_person(
            user, permission=OAuthPermission.WRITE_PUBLIC)
        return ws.named_post(
            snap["self_link"], "setProcessors",
            processors=["/+processors/%s" % name for name in names],
            api_version="devel")

    def assertProcessors(self, user, snap, names):
        body = webservice_for_person(user).get(
            snap["self_link"] + "/processors", api_version="devel").jsonBody()
        self.assertContentEqual(
            names, [entry["name"] for entry in body["entries"]])

    def test_setProcessors_admin(self):
        """An admin can add a new processor to the enabled restricted set."""
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        self.factory.makeProcessor(
            "arm", "ARM", "ARM", restricted=True, build_by_default=False)
        snap = self.makeSnap()
        self.assertProcessors(ppa_admin, snap, ["386", "hppa", "amd64"])

        response = self.setProcessors(ppa_admin, snap, ["386", "arm"])
        self.assertEqual(200, response.status)
        self.assertProcessors(ppa_admin, snap, ["386", "arm"])

    def test_setProcessors_non_owner_forbidden(self):
        """Only PPA admins and snap owners can call setProcessors."""
        self.factory.makeProcessor(
            "unrestricted", "Unrestricted", "Unrestricted", restricted=False,
            build_by_default=False)
        non_owner = self.factory.makePerson()
        snap = self.makeSnap()

        response = self.setProcessors(non_owner, snap, ["386", "unrestricted"])
        self.assertEqual(401, response.status)

    def test_setProcessors_owner(self):
        """The snap owner can enable/disable unrestricted processors."""
        snap = self.makeSnap()
        self.assertProcessors(self.person, snap, ["386", "hppa", "amd64"])

        response = self.setProcessors(self.person, snap, ["386"])
        self.assertEqual(200, response.status)
        self.assertProcessors(self.person, snap, ["386"])

        response = self.setProcessors(self.person, snap, ["386", "amd64"])
        self.assertEqual(200, response.status)
        self.assertProcessors(self.person, snap, ["386", "amd64"])

    def test_setProcessors_owner_restricted_forbidden(self):
        """The snap owner cannot enable/disable restricted processors."""
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        self.factory.makeProcessor(
            "arm", "ARM", "ARM", restricted=True, build_by_default=False)
        snap = self.makeSnap()

        response = self.setProcessors(self.person, snap, ["386", "arm"])
        self.assertEqual(403, response.status)

        # If a PPA admin enables arm, the owner cannot disable it.
        response = self.setProcessors(ppa_admin, snap, ["386", "arm"])
        self.assertEqual(200, response.status)
        self.assertProcessors(self.person, snap, ["386", "arm"])

        response = self.setProcessors(self.person, snap, ["386"])
        self.assertEqual(403, response.status)

    def assertBeginsAuthorization(self, snap, **kwargs):
        snap_url = api_url(snap)
        root_macaroon = Macaroon()
        root_macaroon.add_third_party_caveat(
            urlsplit(config.launchpad.openid_provider_root).netloc, '',
            'dummy')
        root_macaroon_raw = root_macaroon.serialize()

        @all_requests
        def handler(url, request):
            self.request = request
            return {
                "status_code": 200,
                "content": {"macaroon": root_macaroon_raw},
                }

        self.pushConfig("snappy", store_url="http://sca.example/")
        logout()
        with HTTMock(handler):
            response = self.webservice.named_post(
                snap_url, "beginAuthorization", **kwargs)
        self.assertThat(self.request, MatchesStructure.byEquality(
            url="http://sca.example/dev/api/acl/", method="POST"))
        with person_logged_in(self.person):
            expected_body = {
                "packages": [{
                    "name": snap.store_name,
                    "series": snap.store_series.name,
                    }],
                "permissions": ["package_upload"],
                }
            self.assertEqual(expected_body, json.loads(self.request.body))
            self.assertEqual({"root": root_macaroon_raw}, snap.store_secrets)
        return response, root_macaroon.third_party_caveats()[0]

    def test_beginAuthorization(self):
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode())
        response, sso_caveat = self.assertBeginsAuthorization(snap)
        self.assertEqual(sso_caveat.caveat_id, response.jsonBody())

    def test_beginAuthorization_unauthorized(self):
        # A user without edit access cannot authorize snap package uploads.
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode())
        snap_url = api_url(snap)
        other_person = self.factory.makePerson()
        other_webservice = webservice_for_person(
            other_person, permission=OAuthPermission.WRITE_PUBLIC)
        other_webservice.default_api_version = "devel"
        response = other_webservice.named_post(snap_url, "beginAuthorization")
        self.assertEqual(401, response.status)

    def test_completeAuthorization(self):
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode(),
            store_secrets={"root": "dummy-root"})
        snap_url = api_url(snap)
        logout()
        response = self.webservice.named_post(
            snap_url, "completeAuthorization",
            discharge_macaroon="dummy-discharge")
        self.assertEqual(200, response.status)
        with person_logged_in(self.person):
            self.assertEqual(
                {"root": "dummy-root", "discharge": "dummy-discharge"},
                snap.store_secrets)

    def test_completeAuthorization_without_beginAuthorization(self):
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode())
        snap_url = api_url(snap)
        logout()
        response = self.webservice.named_post(
            snap_url, "completeAuthorization",
            discharge_macaroon="dummy-discharge")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "beginAuthorization must be called before completeAuthorization.",
            response.body)

    def test_completeAuthorization_unauthorized(self):
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode(),
            store_secrets={"root": "dummy-root"})
        snap_url = api_url(snap)
        other_person = self.factory.makePerson()
        other_webservice = webservice_for_person(
            other_person, permission=OAuthPermission.WRITE_PUBLIC)
        other_webservice.default_api_version = "devel"
        response = other_webservice.named_post(
            snap_url, "completeAuthorization",
            discharge_macaroon="dummy-discharge")
        self.assertEqual(401, response.status)

    def test_completeAuthorization_both_macaroons(self):
        # It is possible to do the authorization work entirely externally
        # and send both root and discharge macaroons in one go.
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode())
        snap_url = api_url(snap)
        logout()
        response = self.webservice.named_post(
            snap_url, "completeAuthorization",
            root_macaroon="dummy-root", discharge_macaroon="dummy-discharge")
        self.assertEqual(200, response.status)
        with person_logged_in(self.person):
            self.assertEqual(
                {"root": "dummy-root", "discharge": "dummy-discharge"},
                snap.store_secrets)

    def test_completeAuthorization_only_root_macaroon(self):
        # It is possible to store only a root macaroon.  This may make sense
        # if the store has some other way to determine that user consent has
        # been acquired and thus has not added a third-party caveat.
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries()
        snap = self.factory.makeSnap(
            registrant=self.person, store_upload=True,
            store_series=snappy_series,
            store_name=self.factory.getUniqueUnicode())
        snap_url = api_url(snap)
        logout()
        response = self.webservice.named_post(
            snap_url, "completeAuthorization", root_macaroon="dummy-root")
        self.assertEqual(200, response.status)
        with person_logged_in(self.person):
            self.assertEqual({"root": "dummy-root"}, snap.store_secrets)

    def makeBuildableDistroArchSeries(self, **kwargs):
        das = self.factory.makeDistroArchSeries(**kwargs)
        fake_chroot = self.factory.makeLibraryFileAlias(
            filename="fake_chroot.tar.gz", db_only=True)
        das.addOrUpdateChroot(fake_chroot)
        return das

    def test_requestBuild(self):
        # Build requests can be performed and end up in snap.builds and
        # snap.pending_builds.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        snap = self.makeSnap(distroseries=distroseries, processors=[processor])
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(201, response.status)
        build = self.webservice.get(response.getHeader("Location")).jsonBody()
        self.assertEqual(
            [build["self_link"]], self.getCollectionLinks(snap, "builds"))
        self.assertEqual([], self.getCollectionLinks(snap, "completed_builds"))
        self.assertEqual(
            [build["self_link"]],
            self.getCollectionLinks(snap, "pending_builds"))

    def test_requestBuild_rejects_repeats(self):
        # Build requests are rejected if already pending.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        snap = self.makeSnap(distroseries=distroseries, processors=[processor])
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(201, response.status)
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "An identical build of this snap package is already pending.",
            response.body)

    def test_requestBuild_not_owner(self):
        # If the requester is not the owner or a member of the owner team,
        # build requests are rejected.
        other_team = self.factory.makeTeam(displayname="Other Team")
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        other_webservice = webservice_for_person(
            other_team.teamowner, permission=OAuthPermission.WRITE_PUBLIC)
        other_webservice.default_api_version = "devel"
        login(ANONYMOUS)
        snap = self.makeSnap(
            owner=other_team, distroseries=distroseries,
            processors=[processor], webservice=other_webservice)
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(401, response.status)
        self.assertEqual(
            "Test Person cannot create snap package builds owned by Other "
            "Team.", response.body)

    def test_requestBuild_archive_disabled(self):
        # Build requests against a disabled archive are rejected.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)['ubuntu'],
            registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, owner=self.person,
            enabled=False, displayname="Disabled Archive")
        archive_url = api_url(archive)
        snap = self.makeSnap(distroseries=distroseries, processors=[processor])
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(403, response.status)
        self.assertEqual("Disabled Archive is disabled.", response.body)

    def test_requestBuild_archive_private_owners_match(self):
        # Build requests against a private archive are allowed if the Snap
        # and Archive owners match exactly.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)['ubuntu'],
            registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, owner=self.person,
            private=True)
        archive_url = api_url(archive)
        snap = self.makeSnap(distroseries=distroseries, processors=[processor])
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(201, response.status)

    def test_requestBuild_archive_private_owners_mismatch(self):
        # Build requests against a private archive are rejected if the Snap
        # and Archive owners do not match exactly.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)['ubuntu'],
            registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, private=True)
        archive_url = api_url(archive)
        snap = self.makeSnap(distroseries=distroseries, processors=[processor])
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Updates")
        self.assertEqual(403, response.status)
        self.assertEqual(
            "Snap package builds against private archives are only allowed "
            "if the snap package owner and the archive owner are equal.",
            response.body)

    def test_requestAutoBuilds(self):
        # requestAutoBuilds can be performed over the webservice.
        distroseries = self.factory.makeDistroSeries()
        dases = []
        for _ in range(3):
            processor = self.factory.makeProcessor(supports_virtualized=True)
            dases.append(self.makeBuildableDistroArchSeries(
                distroseries=distroseries, processor=processor))
        archive = self.factory.makeArchive()
        snap = self.makeSnap(
            distroseries=distroseries,
            processors=[das.processor for das in dases[:2]],
            auto_build_archive=archive,
            auto_build_pocket=PackagePublishingPocket.PROPOSED)
        response = self.webservice.named_post(
            snap["self_link"], "requestAutoBuilds")
        self.assertEqual(200, response.status)
        builds = response.jsonBody()
        self.assertContentEqual(
            [self.getURL(das) for das in dases[:2]],
            [build["distro_arch_series_link"] for build in builds])

    def test_requestAutoBuilds_requires_auto_build_archive(self):
        # requestAutoBuilds fails if auto_build_archive is not set.
        snap = self.makeSnap()
        response = self.webservice.named_post(
            snap["self_link"], "requestAutoBuilds")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "This snap package cannot have automatic builds created for it "
            "because auto_build_archive is not set.",
            response.body)

    def test_requestAutoBuilds_requires_auto_build_pocket(self):
        # requestAutoBuilds fails if auto_build_pocket is not set.
        snap = self.makeSnap(auto_build_archive=self.factory.makeArchive())
        response = self.webservice.named_post(
            snap["self_link"], "requestAutoBuilds")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "This snap package cannot have automatic builds created for it "
            "because auto_build_pocket is not set.",
            response.body)

    def test_requestAutoBuilds_requires_all_requests_to_succeed(self):
        # requestAutoBuilds fails if any one of its build requests fail.
        distroseries = self.factory.makeDistroSeries()
        dases = []
        for _ in range(2):
            processor = self.factory.makeProcessor(supports_virtualized=True)
            dases.append(self.makeBuildableDistroArchSeries(
                distroseries=distroseries, processor=processor))
        archive = self.factory.makeArchive(enabled=False)
        snap = self.makeSnap(
            distroseries=distroseries,
            processors=[das.processor for das in dases[:2]],
            auto_build_archive=archive,
            auto_build_pocket=PackagePublishingPocket.PROPOSED)
        response = self.webservice.named_post(
            snap["self_link"], "requestAutoBuilds")
        self.assertEqual(403, response.status)
        self.assertEqual(
            "%s is disabled." % archive.displayname, response.body)
        response = self.webservice.get(snap["builds_collection_link"])
        self.assertEqual([], response.jsonBody()["entries"])

    def test_requestAutoBuilds_allows_already_pending(self):
        # requestAutoBuilds succeeds if some of its build requests are
        # already pending.
        distroseries = self.factory.makeDistroSeries()
        dases = []
        das_urls = []
        for _ in range(3):
            processor = self.factory.makeProcessor(supports_virtualized=True)
            dases.append(self.makeBuildableDistroArchSeries(
                distroseries=distroseries, processor=processor))
            das_urls.append(api_url(dases[-1]))
        archive = self.factory.makeArchive()
        archive_url = api_url(archive)
        snap = self.makeSnap(
            distroseries=distroseries,
            processors=[das.processor for das in dases[:2]],
            auto_build_archive=archive,
            auto_build_pocket=PackagePublishingPocket.PROPOSED)
        response = self.webservice.named_post(
            snap["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=das_urls[0], pocket="Proposed")
        self.assertEqual(201, response.status)
        response = self.webservice.named_post(
            snap["self_link"], "requestAutoBuilds")
        self.assertEqual(200, response.status)
        builds = response.jsonBody()
        self.assertContentEqual(
            [self.getURL(dases[1])],
            [build["distro_arch_series_link"] for build in builds])

    def test_getBuilds(self):
        # The builds, completed_builds, and pending_builds properties are as
        # expected.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)['ubuntu'],
            registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archives = [
            self.factory.makeArchive(
                distribution=distroseries.distribution, owner=self.person)
            for x in range(4)]
        archive_urls = [api_url(archive) for archive in archives]
        snap = self.makeSnap(distroseries=distroseries, processors=[processor])
        builds = []
        for archive_url in archive_urls:
            response = self.webservice.named_post(
                snap["self_link"], "requestBuild", archive=archive_url,
                distro_arch_series=distroarchseries_url, pocket="Proposed")
            self.assertEqual(201, response.status)
            build = self.webservice.get(
                response.getHeader("Location")).jsonBody()
            builds.insert(0, build["self_link"])
        self.assertEqual(builds, self.getCollectionLinks(snap, "builds"))
        self.assertEqual([], self.getCollectionLinks(snap, "completed_builds"))
        self.assertEqual(
            builds, self.getCollectionLinks(snap, "pending_builds"))
        snap = self.webservice.get(snap["self_link"]).jsonBody()

        with person_logged_in(self.person):
            db_snap = getUtility(ISnapSet).getByName(self.person, snap["name"])
            db_builds = list(db_snap.builds)
            db_builds[0].updateStatus(
                BuildStatus.BUILDING, date_started=db_snap.date_created)
            db_builds[0].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_snap.date_created + timedelta(minutes=10))
        snap = self.webservice.get(snap["self_link"]).jsonBody()
        # Builds that have not yet been started are listed last.  This does
        # mean that pending builds that have never been started are sorted
        # to the end, but means that builds that were cancelled before
        # starting don't pollute the start of the collection forever.
        self.assertEqual(builds, self.getCollectionLinks(snap, "builds"))
        self.assertEqual(
            builds[:1], self.getCollectionLinks(snap, "completed_builds"))
        self.assertEqual(
            builds[1:], self.getCollectionLinks(snap, "pending_builds"))

        with person_logged_in(self.person):
            db_builds[1].updateStatus(
                BuildStatus.BUILDING, date_started=db_snap.date_created)
            db_builds[1].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_snap.date_created + timedelta(minutes=20))
        snap = self.webservice.get(snap["self_link"]).jsonBody()
        self.assertEqual(
            [builds[1], builds[0], builds[2], builds[3]],
            self.getCollectionLinks(snap, "builds"))
        self.assertEqual(
            [builds[1], builds[0]],
            self.getCollectionLinks(snap, "completed_builds"))
        self.assertEqual(
            builds[2:], self.getCollectionLinks(snap, "pending_builds"))

    def test_query_count(self):
        # Snap has a reasonable query count.
        snap = self.factory.makeSnap(registrant=self.person, owner=self.person)
        url = api_url(snap)
        logout()
        store = Store.of(snap)
        store.flush()
        store.invalidate()
        with StormStatementRecorder() as recorder:
            self.webservice.get(url)
        self.assertThat(recorder, HasQueryCount(Equals(15)))

    def test_builds_query_count(self):
        # The query count of Snap.builds is constant in the number of
        # builds, even if they have store upload jobs.
        self.pushConfig(
            "snappy", store_url="http://sca.example/",
            store_upload_url="http://updown.example/")
        with admin_logged_in():
            snappyseries = self.factory.makeSnappySeries()
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)['ubuntu'],
            registrant=self.person)
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.makeBuildableDistroArchSeries(
            distroseries=distroseries, processor=processor, owner=self.person)
        with person_logged_in(self.person):
            snap = self.factory.makeSnap(
                registrant=self.person, owner=self.person,
                distroseries=distroseries, processors=[processor])
            snap.store_series = snappyseries
            snap.store_name = self.factory.getUniqueUnicode()
            snap.store_upload = True
            snap.store_secrets = {"root": Macaroon().serialize()}
        builds_url = "%s/builds" % api_url(snap)
        logout()

        def make_build():
            with person_logged_in(self.person):
                build = snap.requestBuild(
                    self.person, distroseries.main_archive, distroarchseries,
                    PackagePublishingPocket.PROPOSED)
                with dbuser(config.builddmaster.dbuser):
                    build.updateStatus(
                        BuildStatus.BUILDING, date_started=snap.date_created)
                    build.updateStatus(
                        BuildStatus.FULLYBUILT,
                        date_finished=(
                            snap.date_created + timedelta(minutes=10)))
                return build

        def get_builds():
            response = self.webservice.get(builds_url)
            self.assertEqual(200, response.status)
            return response

        recorder1, recorder2 = record_two_runs(get_builds, make_build, 2)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))
