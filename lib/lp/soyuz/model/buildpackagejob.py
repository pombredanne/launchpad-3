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
from lp.soyuz.interfaces.buildpackagejob import (
    COPY_ARCHIVE_SCORE_PENALTY,
    IBuildPackageJob,
    PRIVATE_ARCHIVE_SCORE_BONUS,
    SCORE_BY_COMPONENT,
    SCORE_BY_POCKET,
    SCORE_BY_URGENCY,
    )
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.model.packageset import Packageset


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

    def score(self):
        """See `IBuildPackageJob`."""
        score = 0

        # Private builds get uber score.
        if self.build.archive.private:
            score += PRIVATE_ARCHIVE_SCORE_BONUS

        if self.build.archive.is_copy:
            score -= COPY_ARCHIVE_SCORE_PENALTY

        score += self.build.archive.relative_build_score

        # Language packs don't get any of the usual package-specific
        # score bumps, as they unduly delay the building of packages in
        # the main component otherwise.
        if self.build.source_package_release.section.name == 'translations':
            return score

        # Calculates the urgency-related part of the score.
        score += SCORE_BY_URGENCY[self.build.source_package_release.urgency]

        # Calculates the pocket-related part of the score.
        score += SCORE_BY_POCKET[self.build.pocket]

        # Calculates the component-related part of the score.
        score += SCORE_BY_COMPONENT.get(
            self.build.current_component.name, 0)

        # Calculates the package-set-related part of the score.
        package_sets = getUtility(IPackagesetSet).setsIncludingSource(
            self.build.source_package_release.name,
            distroseries=self.build.distro_series)
        if not self.build.archive.is_ppa and not package_sets.is_empty():
            score += package_sets.max(Packageset.relative_build_score)

        return score

    @property
    def processor(self):
        """See `IBuildFarmJob`."""
        return self.build.processor

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return self.build.is_virtualized

    @classmethod
    def preloadJobsData(cls, jobs):
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.services.job.model.job import Job
        load_related(Job, jobs, ['job_id'])
        builds = load_related(BinaryPackageBuild, jobs, ['build_id'])
        getUtility(IBinaryPackageBuildSet).preloadBuildsData(list(builds))
