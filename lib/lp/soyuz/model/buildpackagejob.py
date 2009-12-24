# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BuildPackageJob']


from datetime import datetime
import pytz

from storm.locals import Int, Reference, Storm

from zope.interface import classProvides, implements

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues

from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob, IBuildFarmJobDispatchEstimation)
from lp.registry.interfaces.sourcepackage import SourcePackageUrgency
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.buildpackagejob import IBuildPackageJob


class BuildPackageJob(Storm):
    """See `IBuildPackageJob`."""
    implements(IBuildFarmJob, IBuildPackageJob)
    classProvides(IBuildFarmJobDispatchEstimation)

    __storm_table__ = 'buildpackagejob'
    id = Int(primary=True)

    job_id = Int(name='job', allow_none=False)
    job = Reference(job_id, 'Job.id')

    build_id = Int(name='build', allow_none=False)
    build = Reference(build_id, 'Build.id')

    def score(self):
        """See `IBuildPackageJob`."""
        score_pocketname = {
            PackagePublishingPocket.BACKPORTS: 0,
            PackagePublishingPocket.RELEASE: 1500,
            PackagePublishingPocket.PROPOSED: 3000,
            PackagePublishingPocket.UPDATES: 3000,
            PackagePublishingPocket.SECURITY: 4500,
            }

        score_componentname = {
            'multiverse': 0,
            'universe': 250,
            'restricted': 750,
            'main': 1000,
            'partner' : 1250,
            }

        score_urgency = {
            SourcePackageUrgency.LOW: 5,
            SourcePackageUrgency.MEDIUM: 10,
            SourcePackageUrgency.HIGH: 15,
            SourcePackageUrgency.EMERGENCY: 20,
            }

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

        private_archive_increment = 10000

        # For build jobs in rebuild archives a score value of -1
        # was chosen because their priority is lower than build retries
        # or language-packs. They should be built only when there is
        # nothing else to build.
        rebuild_archive_score = -10

        score = 0

        # Please note: the score for language packs is to be zero because
        # they unduly delay the building of packages in the main component
        # otherwise.
        if self.build.sourcepackagerelease.section.name == 'translations':
            pass
        elif self.build.archive.purpose == ArchivePurpose.COPY:
            score = rebuild_archive_score
        else:
            # Calculates the urgency-related part of the score.
            urgency = score_urgency[self.build.sourcepackagerelease.urgency]
            score += urgency

            # Calculates the pocket-related part of the score.
            score_pocket = score_pocketname[self.build.pocket]
            score += score_pocket

            # Calculates the component-related part of the score.
            score_component = score_componentname[
                self.build.current_component.name]
            score += score_component

            # Calculates the build queue time component of the score.
            right_now = datetime.now(pytz.timezone('UTC'))
            eta = right_now - self.job.date_created
            for limit, dep_score in queue_time_scores:
                if eta.seconds > limit:
                    score += dep_score
                    break

            # Private builds get uber score.
            if self.build.archive.private:
                score += private_archive_increment

            # Lastly, apply the archive score delta.  This is to boost
            # or retard build scores for any build in a particular
            # archive.
            score += self.build.archive.relative_build_score

        return score

    def getLogFileName(self):
        """See `IBuildPackageJob`."""
        sourcename = self.build.sourcepackagerelease.name
        version = self.build.sourcepackagerelease.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = self.build.buildstate.name

        dar = self.build.distroarchseries
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
            distroname, distroseriesname, archname, sourcename, version, state
            ))

    def getName(self):
        """See `IBuildPackageJob`."""
        return self.build.sourcepackagerelease.name

    def jobStarted(self):
        """See `IBuildPackageJob`."""
        self.build.buildstate = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        if self.build.date_first_dispatched is None:
            self.build.date_first_dispatched = UTC_NOW

    def jobReset(self):
        """See `IBuildPackageJob`."""
        self.build.buildstate = BuildStatus.NEEDSBUILD

    def jobAborted(self):
        """See `IBuildPackageJob`."""
        # XXX, al-maisan, Thu, 12 Nov 2009 16:38:52 +0100
        # The setting below was "inherited" from the previous code. We
        # need to investigate whether and why this is really needed and
        # fix it.
        self.build.buildstate = BuildStatus.BUILDING

    @staticmethod
    def getPendingJobsQuery(min_score, processor, virtualized):
        """See `IBuildFarmJob`."""
        return """
            SELECT 
                BuildQueue.job,
                BuildQueue.lastscore,
                BuildQueue.estimated_duration,
                Build.processor AS processor,
                Archive.require_virtualized AS virtualized
            FROM
                BuildQueue, Build, BuildPackageJob, Archive, Job
            WHERE
                BuildQueue.job_type = %s
                AND BuildPackageJob.job = BuildQueue.job
                AND BuildPackageJob.job = Job.id
                AND Job.status = %s
                AND BuildPackageJob.build = Build.id
                AND Build.buildstate = %s
                AND Build.archive = Archive.id
                AND Archive.enabled = TRUE
                AND BuildQueue.lastscore >= %s
                AND Build.processor = %s
                AND Archive.require_virtualized = %s
        """ % sqlvalues(
            BuildFarmJobType.PACKAGEBUILD, JobStatus.WAITING,
            BuildStatus.NEEDSBUILD, min_score, processor, virtualized)

    @property
    def processor(self):
        """See `IBuildFarmJob`."""
        return self.build.processor

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return self.build.is_virtualized

