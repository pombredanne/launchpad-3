# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from functools import partial

from storm.locals import Store
from testtools.matchers import Equals
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.soyuz.browser.builder import BuilderEditView
from lp.testing import (
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import ADMIN_EMAIL
from lp.testing.views import create_initialized_view
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuildSource,
    )


class TestBuilderEditView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuilderEditView, self).setUp()
        # Login as an admin to ensure access to the view's context
        # object.
        login(ADMIN_EMAIL)
        self.builder = removeSecurityProxy(self.factory.makeBuilder())

    def initialize_view(self):
        form = {
            "field.manual": "on",
            "field.actions.update": "Change",
            }
        request = LaunchpadTestRequest(method="POST", form=form)
        view = BuilderEditView(self.builder, request)
        return view

    def test_posting_form_doesnt_call_slave_xmlrpc(self):
        # Posting the +edit for should not call isAvailable, which
        # would do xmlrpc to a slave builder and is explicitly forbidden
        # in a webapp process.
        view = self.initialize_view()

        # Stub out the slaveStatusSentence() method with a fake one that
        # records if it's been called.
        view.context.slaveStatusSentence = FakeMethod(result=[0])

        view.initialize()

        # If the dummy slaveStatusSentence() was called the call count
        # would not be zero.
        self.assertTrue(view.context.slaveStatusSentence.call_count == 0)


class TestBuilderHistoryView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    nb_objects = 2

    def setUp(self):
        super(TestBuilderHistoryView, self).setUp()
        self.builder = self.factory.makeBuilder()

    def createTranslationTemplateBuildWithBuilder(self):
        build_farm_job_source = getUtility(IBuildFarmJobSource)
        build_farm_job = build_farm_job_source.new(
            BuildFarmJobType.TRANSLATIONTEMPLATESBUILD)
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        build = source.create(build_farm_job, branch)
        removeSecurityProxy(build).builder = self.builder
        self.addFakeBuildLog(build)
        return build

    def createRecipeBuildWithBuilder(self):
        branch1 = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=self.factory.makeSourcePackageRecipe(
                branches=[branch1, branch2]))
        Store.of(build).flush()
        removeSecurityProxy(build).builder = self.builder
        self.addFakeBuildLog(build)
        return build

    def addFakeBuildLog(self, build):
        lfa = self.factory.makeLibraryFileAlias('mybuildlog.txt')
        removeSecurityProxy(build).log = lfa
        import transaction
        transaction.commit()

    def createBinaryPackageBuild(self, in_ppa=False):
        archive = None
        if in_ppa:
            archive = self.factory.makeArchive()
        build = self.factory.makeBinaryPackageBuild(
            archive=archive, status=BuildStatus.FULLYBUILT)
        naked_build = removeSecurityProxy(build)
        naked_build.builder = self.builder
        naked_build.date_started = self.factory.getUniqueDate()
        naked_build.date_finished = self.factory.getUniqueDate()
        self.addFakeBuildLog(build)
        return build

    def test_build_history_queries_count_view_recipe_builds(self):
        # The builder's history view creation (i.e. the call to
        # view.setupBuildList) issues a constant number of queries
        # when recipe builds are displayed.
        def builder_history_render():
            create_initialized_view(self.builder, '+history').render()
        recorder1, recorder2 = record_two_runs(
            builder_history_render, self.createRecipeBuildWithBuilder,
            self.nb_objects)

        # XXX: rvb 2011-11-14 bug=890326: The only query remaining is the
        # one that results from a call to
        # sourcepackagerecipebuild.buildqueue_record for each recipe build.
        self.assertThat(
            recorder2,
            HasQueryCount(Equals(recorder1.count + 1 * self.nb_objects)))

    def test_build_history_queries_count_binary_package_builds(self):
        # Rendering to builder's history issues a constant number of queries
        # when binary builds are displayed.
        def builder_history_render():
            create_initialized_view(self.builder, '+history').render()
        recorder1, recorder2 = record_two_runs(
            builder_history_render, self.createBinaryPackageBuild,
            self.nb_objects)

        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_build_history_queries_count_binary_package_builds_in_ppa(self):
        # Rendering to builder's history issues a constant number of queries
        # when ppa binary builds are displayed.
        def builder_history_render():
            create_initialized_view(self.builder, '+history').render()
        createBinaryPackageBuildInPPA = partial(
            self.createBinaryPackageBuild, in_ppa=True)
        recorder1, recorder2 = record_two_runs(
            builder_history_render, createBinaryPackageBuildInPPA,
            self.nb_objects)

        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_build_history_queries_count_translation_template_builds(self):
        # Rendering to builder's history issues a constant number of queries
        # when translation template builds are displayed.
        def builder_history_render():
            create_initialized_view(self.builder, '+history').render()
        recorder1, recorder2 = record_two_runs(
            builder_history_render,
            self.createTranslationTemplateBuildWithBuilder, self.nb_objects)

        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))
