# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`TranslationTemplatesBuild` tests."""

__metaclass__ = type

from storm.store import Store
from zope.component import getUtility
from zope.event import notify
from zope.interface.verify import verifyObject
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.code.model.directbranchcommit import DirectBranchCommit
from lp.codehosting.scanner import events
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import LaunchpadZopelessLayer
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode,
    )
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuild,
    ITranslationTemplatesBuildSource,
    )
from lp.translations.model.translationtemplatesbuild import (
    TranslationTemplatesBuild,
    )


class FakeTranslationTemplatesSource(TranslationTemplatesBuild):
    """Fake utility class.

    Allows overriding of _hasPotteryCompatibleSetup.

    How do you fake a utility that is implemented as a class, not a
    factory?  By inheriting from `TranslationTemplatesBuild`, this class
    "copies" the utility.  But you can make it fake the utility's
    behaviour by setting an attribute of the class (not an object!) at
    the beginning of every test.
    """
    # Fake _hasPotteryCompatibleSetup, and if so, make it give what
    # answer?
    fake_pottery_compatibility = None

    @classmethod
    def _hasPotteryCompatibleSetup(cls, branch):
        if cls.fake_pottery_compatibility is None:
            # No fake compatibility setting call the real method.
            return TranslationTemplatesBuild._hasPotteryCompatibleSetup(
                branch)
        else:
            # Fake pottery compatibility.
            return cls.fake_pottery_compatibility


class TestTranslationTemplatesBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestTranslationTemplatesBuild, self).setUp()
        self.jobsource = FakeTranslationTemplatesSource
        self.jobsource.fake_pottery_compabitility = None

    def tearDown(self):
        self._fakePotteryCompatibleSetup(compatible=None)
        super(TestTranslationTemplatesBuild, self).tearDown()

    def _makeTranslationBranch(self, fake_pottery_compatible=None):
        """Create a branch that provides translations for a productseries."""
        if fake_pottery_compatible is None:
            self.useBzrBranches(direct_database=True)
            branch, tree = self.create_branch_and_tree()
        else:
            branch = self.factory.makeAnyBranch()
        product = removeSecurityProxy(branch.product)
        trunk = product.getSeries('trunk')
        trunk.branch = branch
        trunk.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)

        self._fakePotteryCompatibleSetup(fake_pottery_compatible)

        return branch

    def _fakePotteryCompatibleSetup(self, compatible=True):
        """Mock up branch compatibility check.

        :param compatible: Whether the mock check should say that
            branches have a pottery-compatible setup, or that they
            don't.
        """
        self.jobsource.fake_pottery_compatibility = compatible

    def test_baseline(self):
        branch = self.factory.makeBranch()
        build = getUtility(ITranslationTemplatesBuildSource).create(branch)

        self.assertTrue(verifyObject(ITranslationTemplatesBuild, build))
        self.assertTrue(verifyObject(IBuildFarmJob, build))
        self.assertEqual(branch, build.branch)

    def test_permissions(self):
        # The branch scanner creates TranslationTemplatesBuilds.  It has
        # the database privileges it needs for that.
        branch = self.factory.makeBranch()
        switch_dbuser("branchscanner")
        build = getUtility(ITranslationTemplatesBuildSource).create(branch)

        # Writing the new objects to the database violates no access
        # restrictions.
        Store.of(build).flush()

    def test_queueBuild(self):
        build = self.factory.makeTranslationTemplatesBuild()
        bq = build.queueBuild()
        self.assertEqual(build, bq.specific_build)
        self.assertEqual(
            build.build_farm_job, removeSecurityProxy(bq)._build_farm_job)
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertEqual(
            ubuntu.currentseries.nominatedarchindep.processor, bq.processor)

    def test_score(self):
        # For now, these jobs always score themselves at 2515.  In the
        # future however the scoring system is to be revisited.
        build = self.factory.makeTranslationTemplatesBuild()
        self.assertEqual(2515, build.calculateScore())

    def test_build_cookie(self):
        build = self.factory.makeTranslationTemplatesBuild()
        self.assertEqual(
            'TRANSLATIONTEMPLATESBUILD-%d' % build.id, build.build_cookie)

    def test_generatesTemplates(self):
        # A branch "generates templates" if it is a translation branch
        # for a productseries that imports templates from it; is not
        # private; and has a pottery compatible setup.
        # For convenience we fake the pottery compatibility here.
        branch = self._makeTranslationBranch(fake_pottery_compatible=True)
        self.assertTrue(self.jobsource.generatesTemplates(branch))

    def test_not_pottery_compatible(self):
        # If pottery does not see any files it can work with in the
        # branch, generatesTemplates returns False.
        branch = self._makeTranslationBranch()
        self.assertFalse(self.jobsource.generatesTemplates(branch))

    def test_branch_not_used(self):
        # We don't generate templates branches not attached to series.
        branch = self._makeTranslationBranch(fake_pottery_compatible=True)

        trunk = branch.product.getSeries('trunk')
        removeSecurityProxy(trunk).branch = None

        self.assertFalse(self.jobsource.generatesTemplates(branch))

    def test_not_importing_templates(self):
        # We don't generate templates when imports are disabled.
        branch = self._makeTranslationBranch(fake_pottery_compatible=True)

        trunk = branch.product.getSeries('trunk')
        removeSecurityProxy(trunk).translations_autoimport_mode = (
            TranslationsBranchImportMode.NO_IMPORT)

        self.assertFalse(self.jobsource.generatesTemplates(branch))

    def test_private_branch(self):
        # We don't generate templates for private branches.
        branch = self._makeTranslationBranch(fake_pottery_compatible=True)
        removeSecurityProxy(branch).information_type = (
            InformationType.USERDATA)
        self.assertFalse(self.jobsource.generatesTemplates(branch))

    def test_scheduleTranslationTemplatesBuild_subscribed(self):
        # If the feature is enabled, a TipChanged event for a branch that
        # generates templates will schedule a templates build.
        branch = self._makeTranslationBranch()
        removeSecurityProxy(branch).last_scanned_id = 'null:'
        commit = DirectBranchCommit(branch)
        commit.writeFile('POTFILES.in', 'foo')
        commit.commit('message')
        notify(events.TipChanged(branch, commit.bzrbranch, False))
        self.assertEqual(
            1, TranslationTemplatesBuild.findByBranch(branch).count())

    def test_scheduleTranslationTemplatesBuild(self):
        # If the feature is enabled, scheduleTranslationTemplatesBuild
        # will schedule a templates build whenever a change is pushed to
        # a branch that generates templates.
        branch = self._makeTranslationBranch(fake_pottery_compatible=True)
        self.jobsource.scheduleTranslationTemplatesBuild(branch)
        self.assertEqual(
            1, TranslationTemplatesBuild.findByBranch(branch).count())

    def test_findByBranch(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()

        self.assertContentEqual([], source.findByBranch(branch))

        build = source.create(branch)

        by_branch = list(source.findByBranch(branch))
        self.assertEqual([build], by_branch)

    def test_get(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        build = source.create(branch)

        self.assertEqual(build, source.getByID(build.id))

    def test_get_returns_none_if_not_found(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        build = source.create(branch)

        self.assertIs(None, source.getByID(build.id + 999))

    def test_getByBuildFarmJob(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        build = source.create(branch)

        self.assertEqual(build, source.getByBuildFarmJob(build.build_farm_job))

    def test_getByBuildFarmJobs(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_jobs = []
        builds = []
        for i in range(10):
            branch = self.factory.makeBranch()
            build = source.create(branch)
            builds.append(build)
            build_farm_jobs.append(build.build_farm_job)

        self.assertContentEqual(
            builds,
            source.getByBuildFarmJobs(build_farm_jobs))

    def test_getByBuildFarmJob_returns_none_if_not_found(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        source.create(branch)

        another_job = self.factory.makeBinaryPackageBuild().build_farm_job
        self.assertIs(
            None,
            source.getByBuildFarmJob(another_job))
