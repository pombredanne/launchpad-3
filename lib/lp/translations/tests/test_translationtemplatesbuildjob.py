# Copyright 2010-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobOld
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
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
        self.branch = self.factory.makeBranch()
        self.specific_job = self.jobset.create(self.branch)

    def test_new_TranslationTemplatesBuildJob(self):
        # TranslationTemplateBuildJob implements IBuildFarmJobOld,
        # and IBranchJob.
        verifyObject(IBranchJob, self.specific_job)
        verifyObject(IBuildFarmJobOld, self.specific_job)

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

    def test_BuildQueue_for_arch(self):
        # BuildQueue entry is for i386 (default Ubuntu) architecture.
        queueset = getUtility(IBuildQueueSet)
        job_id = get_job_id(self.specific_job.job)
        buildqueue = queueset.get(job_id)

        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertEquals(
            ubuntu.currentseries.nominatedarchindep.processor,
            buildqueue.processor)

    def test_cleanUp(self):
        # TranslationTemplatesBuildJob has its own customized cleanup
        # behaviour, since it's actually a BranchJob.
        job = removeSecurityProxy(self.specific_job.job)
        buildqueue = IStore(BuildQueue).find(BuildQueue, job=job).one()

        job_id = job.id
        store = Store.of(job)
        branch_name = self.branch.unique_name

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
        self.assertEqual(self.branch, branch_set.getByUniqueName(branch_name))


class TestTranslationTemplatesBuildJobSource(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildJobSource`."""

    layer = LaunchpadZopelessLayer

    def test_baseline(self):
        utility = getUtility(ITranslationTemplatesBuildJobSource)
        verifyObject(ITranslationTemplatesBuildJobSource, utility)

    def test_create(self):
        branch = self.factory.makeAnyBranch()
        specific_job = getUtility(ITranslationTemplatesBuildJobSource).create(
            branch)

        # A job is created with the branch URL in its metadata.
        metadata = specific_job.metadata
        self.assertIn('branch_url', metadata)
        url = metadata['branch_url']
        head = 'http://'
        self.assertEqual(head, url[:len(head)])
        tail = branch.name
        self.assertEqual(tail, url[-len(tail):])

    def test_create_with_build(self):
        branch = self.factory.makeAnyBranch()
        specific_job = getUtility(ITranslationTemplatesBuildJobSource).create(
            branch, testing=True)
        naked_job = removeSecurityProxy(specific_job)
        self.assertEquals(naked_job._constructed_build, specific_job.build)
