# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystems."""

__metaclass__ = type

from datetime import timedelta

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
from lp.services.webapp.interfaces import OAuthPermission
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
    api_url,
    login,
    logout,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
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

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSWebservice, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.person = self.factory.makePerson()
        self.webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PUBLIC)
        self.webservice.default_api_version = "devel"
        login(ANONYMOUS)

    def getURL(self, obj):
        return self.webservice.getAbsoluteUrl(api_url(obj))

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
        distroseries_url = api_url(distroseries)
        registrant_url = api_url(registrant)
        owner_url = api_url(owner)
        logout()
        response = self.webservice.named_post(
            registrant_url, "createLiveFS", owner=owner_url,
            distroseries=distroseries_url, name="flavour-desktop",
            metadata=metadata)
        self.assertEqual(201, response.status)
        livefs = self.webservice.get(response.getHeader("Location")).jsonBody()
        return livefs, distroseries_url

    def getCollectionLinks(self, entry, member):
        """Return a list of self_link attributes of entries in a collection."""
        collection = self.webservice.get(
            entry["%s_collection_link" % member]).jsonBody()
        return [entry["self_link"] for entry in collection["entries"]]

    def test_createLiveFS(self):
        # Ensure LiveFS creation works.
        team = self.factory.makeTeam(owner=self.person)
        livefs, distroseries_url = self.makeLiveFS(owner=team)
        with person_logged_in(self.person):
            self.assertEqual(
                self.getURL(self.person), livefs["registrant_link"])
            self.assertEqual(self.getURL(team), livefs["owner_link"])
            self.assertEqual("flavour-desktop", livefs["name"])
            self.assertEqual(
                self.webservice.getAbsoluteUrl(distroseries_url),
                livefs["distroseries_link"])
            self.assertEqual({"project": "flavour"}, livefs["metadata"])

    def test_requestBuild(self):
        # Build requests can be performed and end up in livefs.builds.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        livefs, distroseries_url = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distroarchseries=distroarchseries_url, pocket="Release")
        self.assertEqual(201, response.status)
        build = self.webservice.get(response.getHeader("Location")).jsonBody()
        self.assertEqual(
            [build["self_link"]], self.getCollectionLinks(livefs, "builds"))

    def test_requestBuild_rejects_repeats(self):
        # Build requests are rejected if already pending.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        livefs, ws_distroseries = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distroarchseries=distroarchseries_url, pocket="Release")
        self.assertEqual(201, response.status)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distroarchseries=distroarchseries_url, pocket="Release")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "An identical build of this live filesystem image is already "
            "pending.", response.body)

    def test_getBuilds(self):
        # builds and last_completed_build are as expected.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archives = [
            self.factory.makeArchive(
                distribution=distroseries.distribution, owner=self.person)
            for x in range(4)]
        archive_urls = [api_url(archive) for archive in archives]
        livefs, distroseries_url = self.makeLiveFS(distroseries=distroseries)
        builds = []
        for archive_url in archive_urls:
            response = self.webservice.named_post(
                livefs["self_link"], "requestBuild", archive=archive_url,
                distroarchseries = distroarchseries_url, pocket="Proposed")
            self.assertEqual(201, response.status)
            build = self.webservice.get(
                response.getHeader("Location")).jsonBody()
            builds.insert(0, build["self_link"])
        self.assertEqual(builds, self.getCollectionLinks(livefs, "builds"))
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        self.assertIsNone(livefs["last_completed_build_link"])

        with person_logged_in(self.person):
            db_livefs = getUtility(ILiveFSSet).get(
                self.person, distroseries, livefs["name"])
            db_builds = list(db_livefs.builds)
            db_builds[0].updateStatus(
                BuildStatus.BUILDING, date_started=db_livefs.date_created)
            db_builds[0].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_livefs.date_created + timedelta(minutes=10))
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        self.assertEqual(builds[0], livefs["last_completed_build_link"])

        with person_logged_in(self.person):
            db_builds[1].updateStatus(
                BuildStatus.BUILDING, date_started=db_livefs.date_created)
            db_builds[1].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_livefs.date_created + timedelta(minutes=20))
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        self.assertEqual(builds[1], livefs["last_completed_build_link"])

    def test_query_count(self):
        # LiveFS has a reasonable query count.
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person)
        url = api_url(livefs)
        logout()
        store = Store.of(livefs)
        store.flush()
        store.invalidate()
        with StormStatementRecorder() as recorder:
            self.webservice.get(url)
        self.assertThat(recorder, HasQueryCount(Equals(22)))
