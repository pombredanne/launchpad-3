# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystems."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from lazr.lifecycle.event import ObjectModifiedEvent
import pytz
from storm.locals import Store
from testtools.matchers import Equals
import transaction
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.constants import UTC_NOW
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
        person = self.factory.makePerson()
        self.assertRaises(
            LiveFSFeatureDisabled, getUtility(ILiveFSSet).new,
            person, person, None, None, None)


class TestLiveFS(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFS, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_implements_interfaces(self):
        # LiveFS implements ILiveFS.
        livefs = self.factory.makeLiveFS()
        self.assertProvides(livefs, ILiveFS)

    def test_avoids_problematic_snapshots(self):
        self.assertThat(
            self.factory.makeLiveFS(),
            DoesNotSnapshot(
                ["builds", "completed_builds", "pending_builds"], ILiveFSView))

    def test_initial_date_last_modified(self):
        # The initial value of date_last_modified is date_created.
        livefs = self.factory.makeLiveFS(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC))
        self.assertEqual(livefs.date_created, livefs.date_last_modified)

    def test_modifiedevent_sets_date_last_modified(self):
        # When a LiveFS receives an object modified event, the last modified
        # date is set to UTC_NOW.
        livefs = self.factory.makeLiveFS(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC))
        notify(ObjectModifiedEvent(
            removeSecurityProxy(livefs), livefs, [ILiveFS["name"]]))
        self.assertSqlAttributeEqualsDate(
            livefs, "date_last_modified", UTC_NOW)

    def test_requestBuild(self):
        # requestBuild creates a new LiveFSBuild.
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series)
        build = livefs.requestBuild(
            livefs.owner, livefs.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        self.assertTrue(ILiveFSBuild.providedBy(build))
        self.assertEqual(livefs.owner, build.requester)
        self.assertEqual(livefs.distro_series.main_archive, build.archive)
        self.assertEqual(distroarchseries, build.distro_arch_series)
        self.assertEqual(PackagePublishingPocket.RELEASE, build.pocket)
        self.assertIsNone(build.unique_key)
        self.assertIsNone(build.metadata_override)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)
        store = Store.of(build)
        store.flush()
        build_queue = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id ==
                removeSecurityProxy(build).build_farm_job_id).one()
        self.assertProvides(build_queue, IBuildQueue)
        self.assertEqual(
            livefs.distro_series.main_archive.require_virtualized,
            build_queue.virtualized)
        self.assertEqual(BuildQueueStatus.WAITING, build_queue.status)

    def test_requestBuild_score(self):
        # Build requests have a relatively low queue score (2505).
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series)
        build = livefs.requestBuild(
            livefs.owner, livefs.distro_series.main_archive, distroarchseries,
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
            distroseries=livefs.distro_series)
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
            distroseries=livefs.distro_series)
        old_build = livefs.requestBuild(
            livefs.owner, livefs.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        self.assertRaises(
            LiveFSBuildAlreadyPending, livefs.requestBuild,
            livefs.owner, livefs.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)
        # We can build for a different archive.
        livefs.requestBuild(
            livefs.owner, self.factory.makeArchive(owner=livefs.owner),
            distroarchseries, PackagePublishingPocket.RELEASE)
        # We can build for a different distroarchseries.
        livefs.requestBuild(
            livefs.owner, livefs.distro_series.main_archive,
            self.factory.makeDistroArchSeries(
                distroseries=livefs.distro_series),
            PackagePublishingPocket.RELEASE)
        # Changing the status of the old build allows a new build.
        old_build.updateStatus(BuildStatus.BUILDING)
        old_build.updateStatus(BuildStatus.FULLYBUILT)
        livefs.requestBuild(
            livefs.owner, livefs.distro_series.main_archive, distroarchseries,
            PackagePublishingPocket.RELEASE)

    def test_getBuilds(self):
        # Test the various getBuilds methods.
        livefs = self.factory.makeLiveFS()
        builds = [
            self.factory.makeLiveFSBuild(livefs=livefs) for x in range(3)]
        # We want the latest builds first.
        builds.reverse()

        self.assertEqual(builds, list(livefs.builds))
        self.assertEqual([], list(livefs.completed_builds))
        self.assertEqual(builds, list(livefs.pending_builds))

        # Change the status of one of the builds and retest.
        builds[0].updateStatus(BuildStatus.BUILDING)
        builds[0].updateStatus(BuildStatus.FULLYBUILT)
        self.assertEqual(builds[1:] + builds[:1], list(livefs.builds))
        self.assertEqual(builds[:1], list(livefs.completed_builds))
        self.assertEqual(builds[1:], list(livefs.pending_builds))

    def test_getBuilds_privacy(self):
        # The various getBuilds methods exclude builds against invisible
        # archives.
        livefs = self.factory.makeLiveFS()
        archive = self.factory.makeArchive(
            distribution=livefs.distro_series.distribution, owner=livefs.owner,
            private=True)
        with person_logged_in(livefs.owner):
            build = self.factory.makeLiveFSBuild(
                livefs=livefs, archive=archive)
            self.assertEqual([build], list(livefs.builds))
            self.assertEqual([build], list(livefs.pending_builds))
        self.assertEqual([], list(livefs.builds))
        self.assertEqual([], list(livefs.pending_builds))


class TestLiveFSSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSSet, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_class_implements_interfaces(self):
        # The LiveFSSet class implements ILiveFSSet.
        self.assertProvides(getUtility(ILiveFSSet), ILiveFSSet)

    def makeLiveFSComponents(self, metadata={}):
        """Return a dict of values that can be used to make a LiveFS.

        Suggested use: provide as kwargs to ILiveFSSet.new.

        :param metadata: A dict to set as LiveFS.metadata.
        """
        registrant = self.factory.makePerson()
        return dict(
            registrant=registrant,
            owner=self.factory.makeTeam(owner=registrant),
            distro_series=self.factory.makeDistroSeries(),
            name=self.factory.getUniqueString(u"livefs-name"),
            metadata=metadata)

    def test_creation(self):
        # The metadata entries supplied when a LiveFS is created are present
        # on the new object.
        components = self.makeLiveFSComponents(metadata={"project": "foo"})
        livefs = getUtility(ILiveFSSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], livefs.registrant)
        self.assertEqual(components["owner"], livefs.owner)
        self.assertEqual(components["distro_series"], livefs.distro_series)
        self.assertEqual(components["name"], livefs.name)
        self.assertEqual(components["metadata"], livefs.metadata)

    def test_exists(self):
        # ILiveFSSet.exists checks for matching LiveFSes.
        livefs = self.factory.makeLiveFS()
        self.assertTrue(
            getUtility(ILiveFSSet).exists(
                livefs.owner, livefs.distro_series, livefs.name))
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                self.factory.makePerson(), livefs.distro_series, livefs.name))
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                livefs.owner, self.factory.makeDistroSeries(), livefs.name))
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                livefs.owner, livefs.distro_series, u"different"))


class TestLiveFSWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSWebservice, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.person = self.factory.makePerson(displayname="Test Person")
        self.webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PUBLIC)
        self.webservice.default_api_version = "devel"
        login(ANONYMOUS)

    def getURL(self, obj):
        return self.webservice.getAbsoluteUrl(api_url(obj))

    def makeLiveFS(self, owner=None, distroseries=None, metadata=None,
                   webservice=None):
        if owner is None:
            owner = self.person
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries(registrant=owner)
        if metadata is None:
            metadata = {"project": "flavour"}
        if webservice is None:
            webservice = self.webservice
        transaction.commit()
        distroseries_url = api_url(distroseries)
        owner_url = api_url(owner)
        logout()
        response = webservice.named_post(
            "/livefses", "new", owner=owner_url,
            distro_series=distroseries_url, name="flavour-desktop",
            metadata=metadata)
        self.assertEqual(201, response.status)
        livefs = webservice.get(response.getHeader("Location")).jsonBody()
        return livefs, distroseries_url

    def getCollectionLinks(self, entry, member):
        """Return a list of self_link attributes of entries in a collection."""
        collection = self.webservice.get(
            entry["%s_collection_link" % member]).jsonBody()
        return [entry["self_link"] for entry in collection["entries"]]

    def test_new(self):
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
                livefs["distro_series_link"])
            self.assertEqual({"project": "flavour"}, livefs["metadata"])

    def test_duplicate(self):
        # An attempt to create a duplicate LiveFS fails.
        team = self.factory.makeTeam(owner=self.person)
        _, distroseries_url = self.makeLiveFS(owner=team)
        with person_logged_in(self.person):
            owner_url = api_url(team)
        response = self.webservice.named_post(
            "/livefses", "new", owner=owner_url,
            distro_series=distroseries_url, name="flavour-desktop",
            metadata={})
        self.assertEqual(400, response.status)
        self.assertEqual(
            "There is already a live filesystem with the same name, owner, "
            "and distroseries.", response.body)

    def test_not_owner(self):
        # If the registrant is not the owner or a member of the owner team,
        # LiveFS creation fails.
        other_person = self.factory.makePerson(displayname="Other Person")
        other_team = self.factory.makeTeam(
            owner=other_person, displayname="Other Team")
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        transaction.commit()
        other_person_url = api_url(other_person)
        other_team_url = api_url(other_team)
        distroseries_url = api_url(distroseries)
        logout()
        response = self.webservice.named_post(
            "/livefses", "new", owner=other_person_url,
            distro_series=distroseries_url, name="dummy", metadata={})
        self.assertEqual(401, response.status)
        self.assertEqual(
            "Test Person cannot create live filesystems owned by Other "
            "Person.", response.body)
        response = self.webservice.named_post(
            "/livefses", "new", owner=other_team_url,
            distro_series=distroseries_url, name="dummy", metadata={})
        self.assertEqual(401, response.status)
        self.assertEqual(
            "Test Person is not a member of Other Team.", response.body)

    def test_getByName(self):
        # lp.livefses.getByName returns a matching LiveFS.
        livefs, distroseries_url = self.makeLiveFS()
        with person_logged_in(self.person):
            owner_url = api_url(self.person)
        response = self.webservice.named_get(
            "/livefses", "getByName", owner=owner_url,
            distro_series=distroseries_url, name="flavour-desktop")
        self.assertEqual(200, response.status)
        self.assertEqual(livefs, response.jsonBody())

    def test_getByName_missing(self):
        # lp.livefses.getByName returns 404 for a non-existent LiveFS.
        livefs, distroseries_url = self.makeLiveFS()
        with person_logged_in(self.person):
            owner_url = api_url(self.person)
        response = self.webservice.named_get(
            "/livefses", "getByName", owner=owner_url,
            distro_series=distroseries_url, name="nonexistent")
        self.assertEqual(404, response.status)
        self.assertEqual(
            "No such live filesystem with this owner/distroseries: "
            "'nonexistent'.", response.body)

    def test_requestBuild(self):
        # Build requests can be performed and end up in livefs.builds and
        # livefs.pending_builds.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Release")
        self.assertEqual(201, response.status)
        build = self.webservice.get(response.getHeader("Location")).jsonBody()
        self.assertEqual(
            [build["self_link"]], self.getCollectionLinks(livefs, "builds"))
        self.assertEqual(
            [], self.getCollectionLinks(livefs, "completed_builds"))
        self.assertEqual(
            [build["self_link"]],
            self.getCollectionLinks(livefs, "pending_builds"))

    def test_requestBuild_rejects_repeats(self):
        # Build requests are rejected if already pending.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Release")
        self.assertEqual(201, response.status)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Release")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "An identical build of this live filesystem image is already "
            "pending.", response.body)

    def test_requestBuild_not_owner(self):
        # If the requester is not the owner or a member of the owner team,
        # build requests are rejected.
        other_team = self.factory.makeTeam(displayname="Other Team")
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        other_webservice = webservice_for_person(
            other_team.teamowner, permission=OAuthPermission.WRITE_PUBLIC)
        other_webservice.default_api_version = "devel"
        login(ANONYMOUS)
        livefs, _ = self.makeLiveFS(
            owner=other_team, distroseries=distroseries,
            webservice=other_webservice)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Release")
        self.assertEqual(401, response.status)
        self.assertEqual(
            "Test Person cannot create live filesystem builds owned by Other "
            "Team.", response.body)

    def test_requestBuild_archive_disabled(self):
        # Build requests against a disabled archive are rejected.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, owner=self.person,
            enabled=False, displayname="Disabled Archive")
        archive_url = api_url(archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Release")
        self.assertEqual(403, response.status)
        self.assertEqual("Disabled Archive is disabled.", response.body)

    def test_requestBuild_archive_private(self):
        # Build requests against a private archive are (currently) rejected.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, owner=self.person,
            private=True)
        archive_url = api_url(archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"], "requestBuild", archive=archive_url,
            distro_arch_series=distroarchseries_url, pocket="Release")
        self.assertEqual(403, response.status)
        self.assertEqual(
            "Live filesystem builds against private archives are not "
            "currently allowed.", response.body)

    def test_getBuilds(self):
        # The builds, completed_builds, and pending_builds properties are as
        # expected.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person)
        distroarchseries_url = api_url(distroarchseries)
        archives = [
            self.factory.makeArchive(
                distribution=distroseries.distribution, owner=self.person)
            for x in range(4)]
        archive_urls = [api_url(archive) for archive in archives]
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        builds = []
        for archive_url in archive_urls:
            response = self.webservice.named_post(
                livefs["self_link"], "requestBuild", archive=archive_url,
                distro_arch_series=distroarchseries_url, pocket="Proposed")
            self.assertEqual(201, response.status)
            build = self.webservice.get(
                response.getHeader("Location")).jsonBody()
            builds.insert(0, build["self_link"])
        self.assertEqual(builds, self.getCollectionLinks(livefs, "builds"))
        self.assertEqual(
            [], self.getCollectionLinks(livefs, "completed_builds"))
        self.assertEqual(
            builds, self.getCollectionLinks(livefs, "pending_builds"))
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()

        with person_logged_in(self.person):
            db_livefs = getUtility(ILiveFSSet).getByName(
                self.person, distroseries, livefs["name"])
            db_builds = list(db_livefs.builds)
            db_builds[0].updateStatus(
                BuildStatus.BUILDING, date_started=db_livefs.date_created)
            db_builds[0].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_livefs.date_created + timedelta(minutes=10))
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        # Builds that have not yet been started are listed first (since DESC
        # defaults to NULLS FIRST).
        self.assertEqual(
            builds[1:] + builds[:1], self.getCollectionLinks(livefs, "builds"))
        self.assertEqual(
            builds[:1], self.getCollectionLinks(livefs, "completed_builds"))
        self.assertEqual(
            builds[1:], self.getCollectionLinks(livefs, "pending_builds"))

        with person_logged_in(self.person):
            db_builds[1].updateStatus(
                BuildStatus.BUILDING, date_started=db_livefs.date_created)
            db_builds[1].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_livefs.date_created + timedelta(minutes=20))
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        self.assertEqual(
            [builds[2], builds[3], builds[1], builds[0]],
            self.getCollectionLinks(livefs, "builds"))
        self.assertEqual(
            [builds[1], builds[0]],
            self.getCollectionLinks(livefs, "completed_builds"))
        self.assertEqual(
            builds[2:], self.getCollectionLinks(livefs, "pending_builds"))

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
        self.assertThat(recorder, HasQueryCount(Equals(21)))
