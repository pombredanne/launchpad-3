# Copyright 2010-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the lp.soyuz.browser.builder module."""

__metaclass__ = type

from testtools.matchers import Equals
from zope.component import getUtility

from lp.buildmaster.browser.tests.test_builder_views import BuildCreationMixin
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.services.job.model.job import Job
from lp.testing import (
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.views import create_initialized_view


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
        self.factory.makeSourcePackageRecipeBuild().queueBuild()
        self.factory.makeTranslationTemplatesBuild().queueBuild()

    def test_builders_binary_package_build_query_count(self):
        def create_build():
            build = self.createBinaryPackageBuild()
            build.updateStatus(
                BuildStatus.NEEDSBUILD, force_invalid_transition=True)
            queue = build.queueBuild()
            queue.markAsBuilding(build.builder)

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_build, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_builders_recipe_build_query_count(self):
        def create_build():
            build = self.createRecipeBuildWithBuilder()
            build.updateStatus(
                BuildStatus.NEEDSBUILD, force_invalid_transition=True)
            queue = build.queueBuild()
            queue.markAsBuilding(build.builder)

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_build, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_builders_translation_template_build_query_count(self):
        def create_build():
            queue = self.factory.makeTranslationTemplatesBuild().queueBuild()
            queue.markAsBuilding(self.factory.makeBuilder())

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_build, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_builders_variety_query_count(self):
        def create_builds():
            bqs = [
                self.factory.makeBinaryPackageBuild().queueBuild(),
                self.factory.makeSourcePackageRecipeBuild().queueBuild(),
                self.factory.makeTranslationTemplatesBuild().queueBuild(),
                ]
            for bq in bqs:
                bq.markAsBuilding(self.factory.makeBuilder())

        nb_objects = 2
        recorder1, recorder2 = record_two_runs(
            builders_homepage_render, create_builds, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))
