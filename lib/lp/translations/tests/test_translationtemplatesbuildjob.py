# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from unittest import TestLoader

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ILibraryFileAliasSet)
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import ZopelessDatabaseLayer

from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod

from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob, ISpecificBuildFarmJobClass)
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.code.interfaces.branchjob import IBranchJob
from lp.services.job.model.job import Job
from lp.soyuz.interfaces.buildqueue import IBuildQueueSet
from lp.soyuz.model.buildqueue import BuildQueue
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource)
from lp.translations.model.translationtemplatesbuildjob import (
    TranslationTemplatesBuildJob)


def get_job_id(job):
    """Peek inside a `Job` and retrieve its id."""
    return removeSecurityProxy(job).id


class TestTranslationTemplatesBuildJob(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildJob`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationTemplatesBuildJob, self).setUp()
        self.jobset = getUtility(ITranslationTemplatesBuildJobSource)
        self.branch = self.factory.makeBranch()
        self.specific_job = self.jobset.create(self.branch)

    def test_new_TranslationTemplatesBuildJob(self):
        # TranslationTemplateBuildJob implements IBuildFarmJob and
        # IBranchJob.
        verifyObject(IBranchJob, self.specific_job)
        verifyObject(IBuildFarmJob, self.specific_job)

        # The class also implements ISpecificBuildFarmJobClass.
        verifyObject(ISpecificBuildFarmJobClass, TranslationTemplatesBuildJob)

        # Each of these jobs knows the branch it will operate on.
        self.assertEqual(self.branch, self.specific_job.branch)

    def test_has_Job(self):
        # Associated with each TranslationTemplateBuildJob is a Job.
        base_job = self.specific_job.job
        self.assertIsInstance(base_job, Job)

        # From a Job, the TranslationTemplatesBuildJobSource can find the
        # TranslationTemplatesBuildJob back for us.
        specific_job_for_base_job = removeSecurityProxy(
            TranslationTemplatesBuildJob.getByJob(base_job))
        self.assertEqual(self.specific_job, specific_job_for_base_job)

    def test_has_BuildQueue(self):
        # There's also a BuildQueue item associated with the job.
        queueset = getUtility(IBuildQueueSet)
        job_id = get_job_id(self.specific_job.job)
        buildqueue = queueset.get(job_id)

        self.assertIsInstance(buildqueue, BuildQueue)
        self.assertEqual(job_id, get_job_id(buildqueue.job))

    def test_getName(self):
        # Each job gets a unique name.
        other_job = self.jobset.create(self.branch)
        self.assertNotEqual(self.specific_job.getName(), other_job.getName())

    def test_getTitle(self):
        other_job = self.jobset.create(self.branch)
        self.assertEqual(
            '%s translation templates build' % self.branch.bzr_identity,
            self.specific_job.getTitle())

    def test_getLogFileName(self):
        # Each job has a unique log file name.
        other_job = self.jobset.create(self.branch)
        self.assertNotEqual(
            self.specific_job.getLogFileName(), other_job.getLogFileName())

    def test_score(self):
        # For now, these jobs always score themselves at 1,000.  In the
        # future however the scoring system is to be revisited.
        self.assertEqual(1000, self.specific_job.score())


class TestTranslationTemplatesBuildJobSource(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildJobSource`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationTemplatesBuildJobSource, self).setUp()
        self.jobsource = getUtility(ITranslationTemplatesBuildJobSource)

    def _makeTranslationBranch(self):
        """Create a branch that provides translations for a productseries."""
        branch = self.factory.makeAnyBranch()
        product = removeSecurityProxy(branch.product)
        product.official_rosetta = True
        trunk = product.getSeries('trunk')
        trunk.translations_branch = branch
        trunk.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)

        return branch

    def test_baseline(self):
        verifyObject(ITranslationTemplatesBuildJobSource, self.jobsource)

    def test_generatesTemplates(self):
        # A branch "generates templates" if it is a translation branch
        # for a productseries that imports templates from it; is not
        # private; and has a pottery compatible setup.
        # For convenience we fake the pottery compatibility here.
        branch = self._makeTranslationBranch()
        self.jobsource._hasPotteryCompatibleSetup = FakeMethod(result=True)

        self.assertTrue(self.jobset.generatesTemplates(branch))

    def test_not_pottery_compatible(self):
        # If pottery does not see any files it can work with in the
        # branch, generatesTemplates returns False.
        branch = self._makeTranslationBranch()

        self.assertFalse(self.jobset.generatesTemplates(branch))
    
    def test_not_importing_templates(self):
        pass

    def test_not_translations_branch(self):
        pass

    def test_private_branch(self):
        pass


class TestTranslationTemplatesBuildBehavior(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildBehavior`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationTemplatesBuildBehavior, self).setUp()
        self.jobset = getUtility(ITranslationTemplatesBuildJobSource)
        self.branch = self.factory.makeBranch()
        self.specific_job = self.jobset.create(self.branch)
        self.behavior = IBuildFarmJobBehavior(self.specific_job)

    def test_getChroot(self):
        # _getChroot produces the current chroot for the current Ubuntu
        # release, on the nominated architecture for
        # architecture-independent builds.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        current_ubuntu = ubuntu.currentseries
        distroarchseries = current_ubuntu.nominatedarchindep

        # Set an arbitrary chroot file.
        fake_chroot_file = getUtility(ILibraryFileAliasSet)[1]
        distroarchseries.addOrUpdateChroot(fake_chroot_file)

        chroot = self.behavior._getChroot()

        self.assertNotEqual(None, chroot)
        self.assertEqual(fake_chroot_file, chroot)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
