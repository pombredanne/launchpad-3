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

        # The class also implements a utility and
        # ISpecificBuildFarmJobClass.
        verifyObject(ITranslationTemplatesBuildJobSource, self.jobset)
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

    def test_getLogFileName(self):
        # Each job has a unique log file name.
        other_job = self.jobset.create(self.branch)
        self.assertNotEqual(
            self.specific_job.getLogFileName(), other_job.getLogFileName())

    def test_score(self):
        # For now, these jobs always score themselves at 1,000.  In the
        # future however the scoring system is to be revisited.
        self.assertEqual(1000, self.specific_job.score())


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

    def test_findTranslationTemplatesBuildJob(self):
        job = self.specific_job.job
        job_id = removeSecurityProxy(job).id
        buildqueue = getUtility(IBuildQueueSet).get(job_id)
        specific_job_for_buildqueue = removeSecurityProxy(
            self.behavior._findTranslationTemplatesBuildJob(buildqueue))
        self.assertEqual(self.specific_job, specific_job_for_buildqueue)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
