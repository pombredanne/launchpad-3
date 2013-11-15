# Copyright 2010-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobOld
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.code.interfaces.branch import IBranchSet
from lp.code.interfaces.branchjob import IBranchJob
from lp.services.database.interfaces import IStore
from lp.services.job.model.job import Job
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )
from lp.translations.model.translationtemplatesbuildjob import (
    TranslationTemplatesBuildJob,
    )


def get_job_id(job):
    """Peek inside a `Job` and retrieve its id."""
    return removeSecurityProxy(job).id


class TestTranslationTemplatesBuildJob(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildJob`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationTemplatesBuildJob, self).setUp()
        self.jobset = getUtility(ITranslationTemplatesBuildJobSource)
        self.build = self.factory.makeTranslationTemplatesBuild()
        self.build.queueBuild()
        self.specific_job = self.jobset.getByBranch(self.build.branch)

    def test_new_TranslationTemplatesBuildJob(self):
        # TranslationTemplateBuildJob implements IBuildFarmJobOld,
        # and IBranchJob.
        verifyObject(IBranchJob, self.specific_job)
        verifyObject(IBuildFarmJobOld, self.specific_job)

        # Each of these jobs knows the branch it will operate on.
        self.assertEqual(self.build.branch, self.specific_job.branch)

    def test_has_Job(self):
        # Associated with each TranslationTemplateBuildJob is a Job.
        base_job = self.specific_job.job
        self.assertIsInstance(base_job, Job)

        # From a Job, the TranslationTemplatesBuildJobSource can find the
        # TranslationTemplatesBuildJob back for us.
        specific_job_for_base_job = removeSecurityProxy(
            TranslationTemplatesBuildJob.getByJob(base_job))
        self.assertEqual(self.specific_job, specific_job_for_base_job)

    def test_cleanUp(self):
        # TranslationTemplatesBuildJob has its own customized cleanup
        # behaviour, since it's actually a BranchJob.
        job = removeSecurityProxy(self.specific_job.job)
        buildqueue = IStore(BuildQueue).find(BuildQueue, job=job).one()

        job_id = job.id
        store = Store.of(job)
        branch_name = self.build.branch.unique_name

        buildqueue.destroySelf()

        # BuildQueue is gone.
        self.assertIs(
            None, store.find(BuildQueue, BuildQueue.job == job_id).one())
        # Job is gone.
        self.assertIs(None, store.find(Job, Job.id == job_id).one())
        # TranslationTemplatesBuildJob is gone.
        self.assertIs(None, TranslationTemplatesBuildJob.getByJob(job_id))
        # Branch is still here.
        branch_set = getUtility(IBranchSet)
        self.assertEqual(
            self.build.branch, branch_set.getByUniqueName(branch_name))


class TestTranslationTemplatesBuildJobSource(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildJobSource`."""

    layer = LaunchpadZopelessLayer

    def test_baseline(self):
        utility = getUtility(ITranslationTemplatesBuildJobSource)
        verifyObject(ITranslationTemplatesBuildJobSource, utility)

