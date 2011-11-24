# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildPackageJob',
    ]


from datetime import datetime

import pytz
from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJobOldDerived
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.buildpackagejob import (
    COPY_ARCHIVE_SCORE_PENALTY,
    IBuildPackageJob,
    PRIVATE_ARCHIVE_SCORE_BONUS,
    SCORE_BY_COMPONENT,
    SCORE_BY_POCKET,
    SCORE_BY_URGENCY,
    )

from lp.soyuz.model.buildfarmbuildjob import BuildFarmBuildJob


class BuildPackageJob(BuildFarmJobOldDerived, Storm):
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

    def _set_build_farm_job(self):
        """Setup the IBuildFarmJob delegate.

        We override this to provide a delegate specific to package builds."""
        self.build_farm_job = BuildFarmBuildJob(self.build)

    def score(self):
        """See `IBuildPackageJob`."""
        # Define a table we'll use to calculate the score based on the time
        # in the build queue.  The table is a sorted list of (upper time
        # limit in seconds, score) tuples.
        queue_time_scores = [
            (14400, 100),
            (7200, 50),
            (3600, 20),
            (1800, 15),
            (900, 10),
            (300, 5),
        ]

        # Please note: the score for language packs is to be zero because
        # they unduly delay the building of packages in the main component
        # otherwise.
        if self.build.source_package_release.section.name == 'translations':
            return 0

        score = 0

        # Calculates the urgency-related part of the score.
        urgency = SCORE_BY_URGENCY[
            self.build.source_package_release.urgency]
        score += urgency

        # Calculates the pocket-related part of the score.
        score_pocket = SCORE_BY_POCKET[self.build.pocket]
        score += score_pocket

        # Calculates the component-related part of the score.
        score += SCORE_BY_COMPONENT.get(
            self.build.current_component.name, 0)

        # Calculates the build queue time component of the score.
        right_now = datetime.now(pytz.timezone('UTC'))
        eta = right_now - self.job.date_created
        for limit, dep_score in queue_time_scores:
            if eta.seconds > limit:
                score += dep_score
                break

        # Private builds get uber score.
        if self.build.archive.private:
            score += PRIVATE_ARCHIVE_SCORE_BONUS

        if self.build.archive.is_copy:
            score -= COPY_ARCHIVE_SCORE_PENALTY

        # Lastly, apply the archive score delta.  This is to boost
        # or retard build scores for any build in a particular
        # archive.
        score += self.build.archive.relative_build_score

        return score

    def getLogFileName(self):
        """See `IBuildPackageJob`."""
        sourcename = self.build.source_package_release.name
        version = self.build.source_package_release.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = self.build.status.name

        dar = self.build.distro_arch_series
        distroname = dar.distroseries.distribution.name
        distroseriesname = dar.distroseries.name
        archname = dar.architecturetag

        # logfilename format:
        # buildlog_<DISTRIBUTION>_<DISTROSeries>_<ARCHITECTURE>_\
        # <SOURCENAME>_<SOURCEVERSION>_<BUILDSTATE>.txt
        # as:
        # buildlog_ubuntu_dapper_i386_foo_1.0-ubuntu0_FULLYBUILT.txt
        # it fix request from bug # 30617
        return ('buildlog_%s-%s-%s.%s_%s_%s.txt' % (
            distroname, distroseriesname, archname, sourcename, version,
            state))

    def getName(self):
        """See `IBuildPackageJob`."""
        return self.build.source_package_release.name

    @property
    def processor(self):
        """See `IBuildFarmJob`."""
        return self.build.processor

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return self.build.is_virtualized

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `IBuildFarmJob`."""
        private_statuses = (
            PackagePublishingStatus.PUBLISHED,
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.DELETED,
            )
        sub_query = """
            SELECT TRUE FROM Archive, BinaryPackageBuild, BuildPackageJob,
                             PackageBuild, BuildFarmJob, DistroArchSeries
            WHERE
            BuildPackageJob.job = Job.id AND
            BuildPackageJob.build = BinaryPackageBuild.id AND
            BinaryPackageBuild.distro_arch_series =
                DistroArchSeries.id AND
            BinaryPackageBuild.package_build = PackageBuild.id AND
            PackageBuild.archive = Archive.id AND
            ((Archive.private IS TRUE AND
              EXISTS (
                  SELECT SourcePackagePublishingHistory.id
                  FROM SourcePackagePublishingHistory
                  WHERE
                      SourcePackagePublishingHistory.distroseries =
                         DistroArchSeries.distroseries AND
                      SourcePackagePublishingHistory.sourcepackagerelease =
                         BinaryPackageBuild.source_package_release AND
                      SourcePackagePublishingHistory.archive = Archive.id AND
                      SourcePackagePublishingHistory.status IN %s))
              OR
              archive.private IS FALSE) AND
            PackageBuild.build_farm_job = BuildFarmJob.id AND
            BuildFarmJob.status = %s
        """ % sqlvalues(private_statuses, BuildStatus.NEEDSBUILD)

        # Ensure that if BUILDING builds exist for the same
        # public ppa archive and architecture and another would not
        # leave at least 20% of them free, then we don't consider
        # another as a candidate.
        #
        # This clause selects the count of currently building builds on
        # the arch in question, then adds one to that total before
        # deriving a percentage of the total available builders on that
        # arch.  It then makes sure that percentage is under 80.
        #
        # The extra clause is only used if the number of available
        # builders is greater than one, or nothing would get dispatched
        # at all.
        num_arch_builders = getUtility(IBuilderSet).getBuildersForQueue(
            processor, virtualized).count()
        if num_arch_builders > 1:
            sub_query += """
            AND Archive.id NOT IN (
                SELECT Archive.id
                FROM PackageBuild, BuildFarmJob, Archive,
                    BinaryPackageBuild, DistroArchSeries
                WHERE
                    PackageBuild.build_farm_job = BuildFarmJob.id
                    AND BinaryPackageBuild.package_build = PackageBuild.id
                    AND BinaryPackageBuild.distro_arch_series
                        = DistroArchSeries.id
                    AND DistroArchSeries.processorfamily = %s
                    AND BuildFarmJob.status = %s
                    AND PackageBuild.archive = Archive.id
                    AND Archive.purpose = %s
                    AND Archive.private IS FALSE
                GROUP BY Archive.id
                HAVING (
                    (count(*)+1) * 100.0 / %s
                    ) >= 80
                )
            """ % sqlvalues(
                processor.family, BuildStatus.BUILDING,
                ArchivePurpose.PPA, num_arch_builders)

        return sub_query

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmJob`."""
        # Mark build records targeted to old source versions as SUPERSEDED
        # and build records target to SECURITY pocket as FAILEDTOBUILD.
        # Builds in those situation should not be built because they will
        # be wasting build-time, the former case already has a newer source
        # and the latter could not be built in DAK.
        build_set = getUtility(IBinaryPackageBuildSet)

        build = build_set.getByQueueEntry(job)
        if build.pocket == PackagePublishingPocket.SECURITY:
            # We never build anything in the security pocket.
            logger.debug(
                "Build %s FAILEDTOBUILD, queue item %s REMOVED"
                % (build.id, job.id))
            build.status = BuildStatus.FAILEDTOBUILD
            job.destroySelf()
            return False

        publication = build.current_source_publication
        if publication is None:
            # The build should be superseded if it no longer has a
            # current publishing record.
            logger.debug(
                "Build %s SUPERSEDED, queue item %s REMOVED"
                % (build.id, job.id))
            build.status = BuildStatus.SUPERSEDED
            job.destroySelf()
            return False

        return True
