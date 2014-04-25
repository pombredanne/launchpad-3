# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystems."""

__metaclass__ = type

from datetime import timedelta

from lazr.restfulclient.errors import BadRequest
from storm.locals import Store
from testtools.matchers import Equals
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.publisher import canonical_url
from lp.soyuz.interfaces.livefs import (
    ILiveFS,
    ILiveFSSet,
    ILiveFSView,
    LIVEFS_FEATURE_FLAG,
    LiveFSBuildAlreadyPending,
    LiveFSFeatureDisabled,
    )
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuild
from lp.testing import (
    ANONYMOUS,
    launchpadlib_for,
    login,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    ws_object,
    )
from lp.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.matchers import (
    DoesNotSnapshot,
    HasQueryCount,
    )
from lp.testing.pages import webservice_for_person


class TestLiveFSFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new LiveFSes.
        self.assertRaises(
            LiveFSFeatureDisabled, getUtility(ILiveFSSet).new,
            None, None, None, None, None)


class TestLiveFS(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFS, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_implements_interfaces(self):
        # LiveFS implements ILiveFS.
        livefs = self.factory.makeLiveFS()
        self.assertProvides(livefs, ILiveFS)

    def test_class_implements_interfaces(self):
        # The LiveFS class implements ILiveFSSet.
        self.assertProvides(getUtility(ILiveFSSet), ILiveFSSet)

    def test_avoids_problematic_snapshot(self):
        self.assertThat(
            self.factory.makeLiveFS(),
            DoesNotSnapshot(["builds"], ILiveFSView))

    def makeLiveFSComponents(self, metadata={}):
        """Return a dict of values that can be used to make a LiveFS.

        Suggested use: provide as kwargs to ILiveFSSet.new.

        :param metadata: A dict to set as LiveFS.metadata.
        """
        registrant = self.factory.makePerson()
        return dict(
            registrant=registrant,
            owner=self.factory.makeTeam(owner=registrant),
            distroseries=self.factory.makeDistroSeries(),
            name=self.factory.getUniqueString(u"recipe-name"),
            metadata=metadata)

    def test_creation(self):
        # The metadata entries supplied when a LiveFS is created are present
        # on the new object.
        components = self.makeLiveFSComponents(metadata={"project": "foo"})
        livefs = getUtility(ILiveFSSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], livefs.registrant)
        self.assertEqual(components["owner"], livefs.owner)
        self.assertEqual(components["distroseries"], livefs.distroseries)
        self.assertEqual(components["name"], livefs.name)
        self.assertEqual(components["metadata"], livefs.metadata)

    def test_exists(self):
        # ILiveFSSet.exists checks for matching LiveFSes.
        livefs = self.factory.makeLiveFS()
        self.assertTrue(
            getUtility(ILiveFSSet).exists(
                livefs.owner, livefs.distroseries, livefs.name))
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                self.factory.makePerson(), livefs.distroseries, livefs.name))
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                livefs.owner, self.factory.makeDistroSeries(), livefs.name))
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                livefs.owner, livefs.distroseries, u"different"))

    def test_requestBuild(self):
        # requestBuild creates a new LiveFSBuild.
        livefs = self.factory.makeLiveFS()
        requester = self.factory.makePerson()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distroseries)
        build = livefs.requestBuild(
            requester, livefs.distroseries.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        self.assertTrue(ILiveFSBuild.providedBy(build))
        self.assertEqual(requester, build.requester)
        self.assertEqual(livefs.distroseries.main_archive, build.archive)
        self.assertEqual(distroarchseries, build.distroarchseries)
        self.assertEqual(PackagePublishingPocket.RELEASE, build.pocket)
        self.assertIsNone(build.unique_key)
        self.assertEqual({}, build.metadata_override)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)
        store = Store.of(build)
        store.flush()
        build_queue = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id ==
                removeSecurityProxy(build).build_farm_job_id).one()
        self.assertProvides(build_queue, IBuildQueue)
        self.assertEqual(
            livefs.distroseries.main_archive.require_virtualized,
            build_queue.virtualized)
        self.assertEqual(BuildQueueStatus.WAITING, build_queue.status)

    def test_requestBuild_score(self):
        # Build requests have a relatively low queue score (2505).
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distroseries)
        build = livefs.requestBuild(
            livefs.owner, livefs.distroseries.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2505, queue_record.lastscore)

    def test_requestBuild_relative_build_score(self):
        # Offsets for archives are respected.
        livefs = self.factory.makeLiveFS()
        archive = self.factory.makeArchive(owner=livefs.owner)
        removeSecurityProxy(archive).relative_build_score = 100
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distroseries)
        build = livefs.requestBuild(
            livefs.owner, archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2605, queue_record.lastscore)

    def test_requestBuild_rejects_repeats(self):
        # requestBuild refuses if there is already a pending build.
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distroseries)
        old_build = livefs.requestBuild(
            livefs.owner, livefs.distroseries.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        self.assertRaises(
            LiveFSBuildAlreadyPending, livefs.requestBuild,
            livefs.owner, livefs.distroseries.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        # We can build for a different archive.
        livefs.requestBuild(
            livefs.owner, self.factory.makeArchive(owner=livefs.owner),
            distroarchseries, PackagePublishingPocket.RELEASE)
        # We can build for a different distroarchseries.
        livefs.requestBuild(
            livefs.owner, livefs.distroseries.main_archive,
            self.factory.makeDistroArchSeries(
                distroseries=livefs.distroseries),
            PackagePublishingPocket.RELEASE)
        # Changing the status of the old build allows a new build.
        old_build.updateStatus(BuildStatus.FULLYBUILT)
        livefs.requestBuild(
            livefs.owner, livefs.distroseries.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)

    def test_getBuilds(self):
        # Test the various getBuilds methods.
        livefs = self.factory.makeLiveFS()
        builds = [
            self.factory.makeLiveFSBuild(livefs=livefs) for x in range(3)]
        # We want the latest builds first.
        builds.reverse()

        self.assertEqual(builds, list(livefs.builds))
        self.assertIsNone(livefs.last_completed_build)

        # Change the status of one of the builds and retest.
        builds[0].updateStatus(BuildStatus.FULLYBUILT)
        self.assertEqual(builds, list(livefs.builds))
        self.assertEqual(builds[0], livefs.last_completed_build)


class TestLiveFSWebservice(TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestLiveFSWebservice, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.person = self.factory.makePerson()
        self.webservice = launchpadlib_for(
            "testing", self.person,
            service_root=self.layer.appserver_root_url("api"))
        login(ANONYMOUS)

    def makeLiveFS(self, registrant=None, owner=None, distroseries=None,
                   metadata=None):
        if registrant is None:
            registrant = self.person
        if owner is None:
            owner = registrant
        if metadata is None:
            metadata = {"project": "flavour"}
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries(registrant=registrant)
        transaction.commit()
        ws_distroseries = ws_object(self.webservice, distroseries)
        ws_registrant = ws_object(self.webservice, registrant)
        ws_owner = ws_object(self.webservice, owner)
        livefs = ws_registrant.createLiveFS(
            owner=ws_owner, distroseries=ws_distroseries,
            name="flavour-desktop", metadata=metadata)
        transaction.commit()
        return livefs, ws_distroseries

    def test_createLiveFS(self):
        # Ensure LiveFS creation works.
        team = self.factory.makeTeam(owner=self.person)
        livefs, ws_distroseries = self.makeLiveFS(owner=team)
        self.assertEqual(self.person.name, livefs.registrant.name)
        self.assertEqual(team.name, livefs.owner.name)
        self.assertEqual("flavour-desktop", livefs.name)
        self.assertEqual(ws_distroseries, livefs.distroseries)
        self.assertEqual({"project": "flavour"}, livefs.metadata)

    def test_requestBuild(self):
        # Build requests can be performed and end up in livefs.builds.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        livefs, ws_distroseries = self.makeLiveFS(
            registrant=self.person, distroseries=distroseries)
        build = livefs.requestBuild(
            archive=ws_distroseries.main_archive,
            distroarchseries=ws_object(self.webservice, distroarchseries),
            pocket="Release")
        self.assertEqual([build], list(livefs.builds))

    def test_requestBuild_rejects_repeats(self):
        # Build requests are rejected if already pending.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        livefs, ws_distroseries = self.makeLiveFS(
            registrant=self.person, distroseries=distroseries)
        ws_distroarchseries = ws_object(self.webservice, distroarchseries)
        livefs.requestBuild(
            archive=ws_distroseries.main_archive,
            distroarchseries=ws_distroarchseries, pocket="Release")
        e = self.assertRaises(
            BadRequest, livefs.requestBuild,
            archive=ws_distroseries.main_archive,
            distroarchseries=ws_distroarchseries, pocket="Release")
        self.assertIn(
            "An identical build of this live filesystem image is already "
            "pending.", str(e))

    def test_getBuilds(self):
        # builds and last_completed_build are as expected.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        archives = [
            self.factory.makeArchive(
                distribution=distroseries.distribution, owner=self.person)
            for x in range(4)]
        livefs, ws_distroseries = self.makeLiveFS(
            registrant=self.person, distroseries=distroseries)
        ws_distroarchseries = ws_object(self.webservice, distroarchseries)
        builds = []
        for archive in archives:
            ws_archive = ws_object(self.webservice, archive)
            builds.insert(0, livefs.requestBuild(
                archive=ws_archive, distroarchseries=ws_distroarchseries,
                pocket="Proposed"))
        self.assertEqual(builds, list(livefs.builds))
        self.assertIsNone(livefs.last_completed_build)
        transaction.commit()

        db_livefs = getUtility(ILiveFSSet).get(
            self.person, distroseries, livefs.name)
        db_builds = list(db_livefs.builds)
        db_builds[0].updateStatus(
            BuildStatus.BUILDING, date_started=db_livefs.date_created)
        db_builds[0].updateStatus(
            BuildStatus.FULLYBUILT,
            date_finished=db_livefs.date_created + timedelta(minutes=10))
        transaction.commit()
        livefs = ws_object(self.webservice, db_livefs)
        self.assertEqual(
            builds[0].self_link, livefs.last_completed_build.self_link)

        db_builds[1].updateStatus(
            BuildStatus.BUILDING, date_started=db_livefs.date_created)
        db_builds[1].updateStatus(
            BuildStatus.FULLYBUILT,
            date_finished=db_livefs.date_created + timedelta(minutes=20))
        transaction.commit()
        livefs = ws_object(self.webservice, db_livefs)
        self.assertEqual(
            builds[1].self_link, livefs.last_completed_build.self_link)

    def test_query_count(self):
        # LiveFS has a reasonable query count.
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person)
        webservice = webservice_for_person(self.person)
        with person_logged_in(self.person):
            url = canonical_url(livefs, force_local_path=True)
        store = Store.of(livefs)
        store.flush()
        store.invalidate()
        with StormStatementRecorder() as recorder:
            webservice.get(url)
        self.assertThat(recorder, HasQueryCount(Equals(19)))
