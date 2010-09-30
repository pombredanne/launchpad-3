# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BuildFarmJobBehaviorBase."""

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import CorruptBuildCookie
from lp.buildmaster.model.buildfarmjobbehavior import BuildFarmJobBehaviorBase
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.processor import IProcessorFamilySet
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class FakeBuildFarmJob:
    """Dummy BuildFarmJob."""
    pass


class TestBuildFarmJobBehaviorBase(TestCaseWithFactory):
    """Test very small, basic bits of BuildFarmJobBehaviorBase."""

    layer = ZopelessDatabaseLayer

    def _makeBehavior(self, buildfarmjob=None):
        """Create a `BuildFarmJobBehaviorBase`."""
        if buildfarmjob is None:
            buildfarmjob = FakeBuildFarmJob()
        else:
            buildfarmjob = removeSecurityProxy(buildfarmjob)
        return BuildFarmJobBehaviorBase(buildfarmjob)

    def _changeBuildFarmJobName(self, buildfarmjob):
        """Manipulate `buildfarmjob` so that its `getName` changes."""
        name = buildfarmjob.getName() + 'x'
        removeSecurityProxy(buildfarmjob).getName = FakeMethod(result=name)

    def _makeBuild(self):
        """Create a `Build` object."""
        x86 = getUtility(IProcessorFamilySet).getByName('x86')
        distroarchseries = self.factory.makeDistroArchSeries(
            architecturetag='x86', processorfamily=x86)
        distroseries = distroarchseries.distroseries
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution)
        pocket = PackagePublishingPocket.RELEASE
        spr = self.factory.makeSourcePackageRelease(
            distroseries=distroseries, archive=archive)

        return spr.createBuild(
            distroarchseries=distroarchseries, pocket=pocket, archive=archive)

    def _makeBuildQueue(self):
        """Create a `BuildQueue` object."""
        return self.factory.makeSourcePackageRecipeBuildJob()

    def test_extractBuildStatus_baseline(self):
        # extractBuildStatus picks the name of the build status out of a
        # dict describing the slave's status.
        slave_status = {'build_status': 'BuildStatus.BUILDING'}
        behavior = self._makeBehavior()
        self.assertEqual(
            BuildStatus.BUILDING.name,
            behavior.extractBuildStatus(slave_status))

    def test_extractBuildStatus_malformed(self):
        # extractBuildStatus errors out when the status string is not
        # of the form it expects.
        slave_status = {'build_status': 'BUILDING'}
        behavior = self._makeBehavior()
        self.assertRaises(
            AssertionError, behavior.extractBuildStatus, slave_status)

    def test_cookie_baseline(self):
        buildfarmjob = self.factory.makeTranslationTemplatesBuildJob()

        cookie = buildfarmjob.generateSlaveBuildCookie()

        self.assertNotEqual(None, cookie)
        self.assertNotEqual(0, len(cookie))
        self.assertTrue(len(cookie) > 10)

        self.assertEqual(cookie, buildfarmjob.generateSlaveBuildCookie())

    def test_verifySlaveBuildCookie_good(self):
        buildfarmjob = self.factory.makeTranslationTemplatesBuildJob()
        behavior = self._makeBehavior(buildfarmjob)

        cookie = buildfarmjob.generateSlaveBuildCookie()

        # The correct cookie validates successfully.
        behavior.verifySlaveBuildCookie(cookie)

    def test_verifySlaveBuildCookie_bad(self):
        buildfarmjob = self.factory.makeTranslationTemplatesBuildJob()
        behavior = self._makeBehavior(buildfarmjob)

        cookie = buildfarmjob.generateSlaveBuildCookie()

        self.assertRaises(
            CorruptBuildCookie,
            behavior.verifySlaveBuildCookie,
            cookie + 'x')

    def test_cookie_includes_job_name(self):
        # The cookie is a hash that includes the job's name.
        buildfarmjob = self.factory.makeTranslationTemplatesBuildJob()
        buildfarmjob = removeSecurityProxy(buildfarmjob)
        behavior = self._makeBehavior(buildfarmjob)
        cookie = buildfarmjob.generateSlaveBuildCookie()

        self._changeBuildFarmJobName(buildfarmjob)

        self.assertRaises(
            CorruptBuildCookie,
            behavior.verifySlaveBuildCookie,
            cookie)

        # However, the name is not included in plaintext so as not to
        # provide a compromised slave a starting point for guessing
        # another slave's cookie.
        self.assertNotIn(buildfarmjob.getName(), cookie)

    def test_cookie_includes_more_than_name(self):
        # Two build jobs with the same name still get different cookies.
        buildfarmjob1 = self.factory.makeTranslationTemplatesBuildJob()
        buildfarmjob1 = removeSecurityProxy(buildfarmjob1)
        buildfarmjob2 = self.factory.makeTranslationTemplatesBuildJob(
            branch=buildfarmjob1.branch)
        buildfarmjob2 = removeSecurityProxy(buildfarmjob2)

        name_factory = FakeMethod(result="same-name")
        buildfarmjob1.getName = name_factory
        buildfarmjob2.getName = name_factory

        self.assertEqual(buildfarmjob1.getName(), buildfarmjob2.getName())
        self.assertNotEqual(
            buildfarmjob1.generateSlaveBuildCookie(),
            buildfarmjob2.generateSlaveBuildCookie())
