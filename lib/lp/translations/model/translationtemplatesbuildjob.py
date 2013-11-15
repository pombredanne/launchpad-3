# Copyright 2010-2013 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildJob',
    ]

from storm.store import Store
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobOld
from lp.buildmaster.model.buildfarmjob import BuildFarmJobOld
from lp.code.model.branchjob import (
    BranchJob,
    BranchJobDerived,
    BranchJobType,
    )
from lp.services.database.bulk import load_related
from lp.services.database.interfaces import IStore
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuildSource,
    )
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )


class TranslationTemplatesBuildJob(BuildFarmJobOld, BranchJobDerived):
    """An `IBuildFarmJob` implementation that generates templates.

    Implementation-wise, this is actually a `BranchJob`.
    """
    implements(IBuildFarmJobOld)
    class_job_type = BranchJobType.TRANSLATION_TEMPLATES_BUILD

    classProvides(ITranslationTemplatesBuildJobSource)

    def cleanUp(self):
        """See `IBuildFarmJob`."""
        # This class is not itself database-backed.  But it delegates to
        # one that is.  We can't call its SQLObject destroySelf method
        # though, because then the BuildQueue and the BranchJob would
        # both try to delete the attached Job.
        Store.of(self.context).remove(self.context)

    @property
    def build(self):
        """Return a TranslationTemplateBuild for this build job."""
        build_id = self.context.metadata.get('build_id', None)
        if build_id is None:
            return None
        else:
            return getUtility(ITranslationTemplatesBuildSource).getByID(
                int(build_id))

    @classmethod
    def getByJob(cls, job):
        """See `IBuildFarmJob`.

        Overridden here to search via a BranchJob, rather than a Job.
        """
        store = IStore(BranchJob)
        branch_job = store.find(BranchJob, BranchJob.job == job).one()
        if branch_job is None:
            return None
        else:
            return cls(branch_job)

    @classmethod
    def getByJobs(cls, jobs):
        """See `IBuildFarmJob`.

        Overridden here to search via a BranchJob, rather than a Job.
        """
        store = IStore(BranchJob)
        job_ids = [job.id for job in jobs]
        branch_jobs = store.find(
            BranchJob, BranchJob.jobID.is_in(job_ids))
        return [cls(branch_job) for branch_job in branch_jobs]

    @classmethod
    def preloadJobsData(cls, jobs):
        # Circular imports.
        from lp.code.model.branch import Branch
        from lp.registry.model.product import Product
        from lp.code.model.branchcollection import GenericBranchCollection
        from lp.services.job.model.job import Job
        contexts = [job.context for job in jobs]
        load_related(Job, contexts, ['jobID'])
        branches = load_related(Branch, contexts, ['branchID'])
        GenericBranchCollection.preloadDataForBranches(branches)
        load_related(Product, branches, ['productID'])

    @classmethod
    def getByBranch(cls, branch):
        """See `ITranslationTemplatesBuildJobSource`."""
        store = IStore(BranchJob)
        branch_job = store.find(BranchJob, BranchJob.branch == branch).one()
        if branch_job is None:
            return None
        else:
            return cls(branch_job)
