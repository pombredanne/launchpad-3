# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystem build views."""

__metaclass__ = type

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
from storm.locals import Store
from testtools.matchers import StartsWith
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.soyuz.interfaces.livefs import LIVEFS_FEATURE_FLAG
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    BrowserTestCase,
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.pages import (
    extract_text,
    find_main_content,
    find_tags_by_class,
    )
from lp.testing.views import create_initialized_view


class TestCanonicalUrlForLiveFSBuild(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestCanonicalUrlForLiveFSBuild, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_canonical_url(self):
        owner = self.factory.makePerson(name="person")
        distribution = self.factory.makeDistribution(
            name="distro", owner=owner)
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="unstable")
        livefs = self.factory.makeLiveFS(
            registrant=owner, owner=owner, distroseries=distroseries,
            name=u"livefs")
        build = self.factory.makeLiveFSBuild(requester=owner, livefs=livefs)
        self.assertThat(
            canonical_url(build),
            StartsWith(
                "http://launchpad.dev/~person/+livefs/distro/unstable/livefs/"
                "+build/"))


class TestLiveFSBuildView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestLiveFSBuildView, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_files(self):
        # LiveFSBuildView.files returns all the associated files.
        build = self.factory.makeLiveFSBuild(status=BuildStatus.FULLYBUILT)
        livefsfile = self.factory.makeLiveFSFile(livefsbuild=build)
        build_view = create_initialized_view(build, "+index")
        self.assertEqual(
            [livefsfile.libraryfile.filename],
            [lfa.filename for lfa in build_view.files])
        # Deleted files won't be included.
        self.assertFalse(livefsfile.libraryfile.deleted)
        removeSecurityProxy(livefsfile.libraryfile).content = None
        self.assertTrue(livefsfile.libraryfile.deleted)
        build_view = create_initialized_view(build, "+index")
        self.assertEqual([], build_view.files)

    def test_eta(self):
        # LiveFSBuildView.eta returns a non-None value when it should, or
        # None when there's no start time.
        build = self.factory.makeLiveFSBuild()
        build.queueBuild()
        self.assertIsNone(create_initialized_view(build, "+index").eta)
        self.factory.makeBuilder(processors=[build.processor])
        self.assertIsNotNone(create_initialized_view(build, "+index").eta)

    def test_estimate(self):
        # LiveFSBuildView.estimate returns True until the job is completed.
        build = self.factory.makeLiveFSBuild()
        build.queueBuild()
        self.factory.makeBuilder(processors=[build.processor])
        build.updateStatus(BuildStatus.BUILDING)
        self.assertTrue(create_initialized_view(build, "+index").estimate)
        build.updateStatus(BuildStatus.FULLYBUILT)
        self.assertFalse(create_initialized_view(build, "+index").estimate)


class TestLiveFSBuildOperations(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSBuildOperations, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.useFixture(FakeLogger())
        self.build = self.factory.makeLiveFSBuild()
        self.build_url = canonical_url(self.build)
        self.requester = self.build.requester
        self.buildd_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).buildd_admin])

    def test_cancel_build(self):
        # The requester of a build can cancel it.
        self.build.queueBuild()
        transaction.commit()
        browser = self.getViewBrowser(self.build, user=self.requester)
        browser.getLink("Cancel build").click()
        self.assertEqual(self.build_url, browser.getLink("Cancel").url)
        browser.getControl("Cancel build").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        self.assertEqual(BuildStatus.CANCELLED, self.build.status)

    def test_cancel_build_random_user(self):
        # An unrelated non-admin user cannot cancel a build.
        self.build.queueBuild()
        transaction.commit()
        user = self.factory.makePerson()
        browser = self.getViewBrowser(self.build, user=user)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Cancel build")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, self.build_url + "/+cancel",
            user=user)

    def test_cancel_build_wrong_state(self):
        # If the build isn't queued, you can't cancel it.
        browser = self.getViewBrowser(self.build, user=self.requester)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Cancel build")

    def test_rescore_build(self):
        # A buildd admin can rescore a build.
        self.build.queueBuild()
        transaction.commit()
        browser = self.getViewBrowser(self.build, user=self.buildd_admin)
        browser.getLink("Rescore build").click()
        self.assertEqual(self.build_url, browser.getLink("Cancel").url)
        browser.getControl("Priority").value = "1024"
        browser.getControl("Rescore build").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        self.assertEqual(1024, self.build.buildqueue_record.lastscore)

    def test_rescore_build_invalid_score(self):
        # Build scores can only take numbers.
        self.build.queueBuild()
        transaction.commit()
        browser = self.getViewBrowser(self.build, user=self.buildd_admin)
        browser.getLink("Rescore build").click()
        self.assertEqual(self.build_url, browser.getLink("Cancel").url)
        browser.getControl("Priority").value = "tentwentyfour"
        browser.getControl("Rescore build").click()
        self.assertEqual(
            "Invalid integer data",
            extract_text(find_tags_by_class(browser.contents, "message")[1]))

    def test_rescore_build_not_admin(self):
        # A non-admin user cannot cancel a build.
        self.build.queueBuild()
        transaction.commit()
        user = self.factory.makePerson()
        browser = self.getViewBrowser(self.build, user=user)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Rescore build")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, self.build_url + "/+rescore",
            user=user)

    def test_rescore_build_wrong_state(self):
        # If the build isn't NEEDSBUILD, you can't rescore it.
        self.build.queueBuild()
        with person_logged_in(self.requester):
            self.build.cancel()
        browser = self.getViewBrowser(self.build, user=self.buildd_admin)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Rescore build")

    def test_rescore_build_wrong_state_stale_link(self):
        # An attempt to rescore a non-queued build from a stale link shows a
        # sensible error message.
        self.build.queueBuild()
        with person_logged_in(self.requester):
            self.build.cancel()
        browser = self.getViewBrowser(
            self.build, "+rescore", user=self.buildd_admin)
        self.assertEqual(self.build_url, browser.url)
        self.assertIn(
            "Cannot rescore this build because it is not queued.",
            browser.contents)

    def test_builder_history(self):
        Store.of(self.build).flush()
        self.build.updateStatus(
            BuildStatus.FULLYBUILT, builder=self.factory.makeBuilder())
        title = self.build.title
        browser = self.getViewBrowser(self.build.builder, "+history")
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "Build history.*%s" % title,
            extract_text(find_main_content(browser.contents)))
        self.assertEqual(self.build_url, browser.getLink(title).url)

    def makeBuildingLiveFS(self, archive=None):
        builder = self.factory.makeBuilder()
        build = self.factory.makeLiveFSBuild(archive=archive)
        build.updateStatus(BuildStatus.BUILDING, builder=builder)
        build.queueBuild()
        build.buildqueue_record.builder = builder
        build.buildqueue_record.logtail = "tail of the log"
        return build

    def test_builder_index_public(self):
        build = self.makeBuildingLiveFS()
        builder_url = canonical_url(build.builder)
        logout()
        browser = self.getNonRedirectingBrowser(
            url=builder_url, user=ANONYMOUS)
        self.assertIn("tail of the log", browser.contents)

    def test_builder_index_private(self):
        archive = self.factory.makeArchive(private=True)
        with admin_logged_in():
            build = self.makeBuildingLiveFS(archive=archive)
            builder_url = canonical_url(build.builder)
        logout()

        # An unrelated user can't see the logtail of a private build.
        browser = self.getNonRedirectingBrowser(url=builder_url)
        self.assertNotIn("tail of the log", browser.contents)

        # But someone who can see the archive can.
        browser = self.getNonRedirectingBrowser(
            url=builder_url, user=archive.owner)
        self.assertIn("tail of the log", browser.contents)
