# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildPackageJob',
    ]


from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.component import getUtility
from zope.interface import implements

from lp.buildmaster.model.buildfarmjob import BuildFarmJobOld
from lp.services.database.bulk import load_related
from lp.services.database.interfaces import IStore
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.buildpackagejob import IBuildPackageJob


class BuildPackageJob(BuildFarmJobOld, Storm):
    """See `IBuildPackageJob`."""
    implements(IBuildPackageJob)

    __storm_table__ = 'buildpackagejob'
    id = Int(primary=True)

    job_id = Int(name='job', allow_none=False)
    job = Reference(job_id, 'Job.id')

    build_id = Int(name='build', allow_none=False)
    build = Reference(build_id, 'BinaryPackageBuild.id')

    def __init__(self, build, job):
        self.build, self.job = build, job
        super(BuildPackageJob, self).__init__()

    @staticmethod
    def preloadBuildFarmJobs(jobs):
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        return list(IStore(BinaryPackageBuild).find(
            BinaryPackageBuild,
            [BuildPackageJob.job_id.is_in([job.id for job in jobs]),
             BuildPackageJob.build_id == BinaryPackageBuild.id]))

    @classmethod
    def preloadJobsData(cls, jobs):
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.services.job.model.job import Job
        load_related(Job, jobs, ['job_id'])
        builds = load_related(BinaryPackageBuild, jobs, ['build_id'])
        getUtility(IBinaryPackageBuildSet).preloadBuildsData(list(builds))
