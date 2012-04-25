# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the lp.soyuz.browser.builder module."""

__metaclass__ = type

from testtools.matchers import Equals
from zope.component import getUtility

from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.services.job.model.job import Job
from lp.services.webapp import canonical_url
from lp.soyuz.browser.tests.test_builder_views import BuildCreationMixin
from lp.testing import (
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.publication import test_traverse
from lp.testing.views import create_initialized_view
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )


class TestBuildersNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_buildjob_redirects_for_recipe_build(self):
        # /builders/+buildjob/<job id> redirects to the build page.
        build = self.factory.makeSourcePackageRecipeBuild()
        url = 'http://launchpad.dev/builders/+buildjob/%s' % (
            build.build_farm_job.id)
        context, view, request = test_traverse(url)
        view()
        self.assertEqual(301, request.response.getStatus())
        self.assertEqual(
            canonical_url(build),
            request.response.getHeader('location'))

    def test_buildjob_redirects_for_binary_build(self):
        # /builders/+buildjob/<job id> redirects to the build page.
        build = self.factory.makeBinaryPackageBuild()
        url = 'http://launchpad.dev/builders/+buildjob/%s' % (
            build.build_farm_job.id)
        context, view, request = test_traverse(url)
        view()
        self.assertEqual(301, request.response.getStatus())
        self.assertEqual(
            canonical_url(build),
            request.response.getHeader('location'))


def builders_homepage_render():
    builders = getUtility(IBuilderSet)
    create_initialized_view(builders, "+index").render()


class TestBuildersHomepage(TestCaseWithFactory, BuildCreationMixin):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuildersHomepage, self).setUp()
        # Create a non-buildfarm job to ensure that the BuildQueue and
        # Job IDs differ, detecting bug #919116.
        Job()
        # And create BuildFarmJobs of the various types to throw IDs off
        # even further, detecting more preloading issues.
        self.factory.makeBinaryPackageBuild().queueBuild()
        self.factory.makeSourcePackageRecipeBuildJob()
        self.factory.makeTranslationTemplatesBuildJob()

    def test_builders_binary_package_build_query_count(self):
        def create_build():
            build = self.createBinaryPackageBuild()
            queue = build.queueBuild()
            queue.markAsBuilding(build.builder)

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_build, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_builders_recipe_build_query_count(self):
        def create_build():
            build = self.createRecipeBuildWithBuilder()
            queue = build.queueBuild()
            queue.markAsBuilding(build.builder)

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_build, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_builders_translation_template_build_query_count(self):
        def create_build():
            jobset = getUtility(ITranslationTemplatesBuildJobSource)
            branch = self.factory.makeBranch()
            specific_job = jobset.create(branch)
            queueset = getUtility(IBuildQueueSet)
            queue = queueset.getByJob(specific_job.job)
            queue.markAsBuilding(self.factory.makeBuilder())

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_build, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))
