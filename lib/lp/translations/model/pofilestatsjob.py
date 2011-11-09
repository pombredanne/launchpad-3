# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job for merging translations."""


__metaclass__ = type


__all__ = [
    'POFileStatsJob',
    ]

import logging
from zope.component import getUtility

from storm.locals import (
    And,
    Int,
    Reference,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.services.database.stormbase import StormBase
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.translations.interfaces.pofilestatsjob import IPOFileStatsJobSource
from lp.translations.model.pofile import POFile


class POFileStatsJob(StormBase, BaseRunnableJob):
    """The details for a POFile status update job."""

    __storm_table__ = 'POFileStatsJob'

    # Instances of this class are runnable jobs.
    implements(IRunnableJob)

    # Oddly, BaseRunnableJob inherits from BaseRunnableJobSource so this class
    # is both the factory for jobs (the "implements", above) and the source
    # for runnable jobs (not the constructor of the job source, the class
    # provides the IJobSource interface itself).
    classProvides(IPOFileStatsJobSource)

    id = Int(primary=True)

    # The Job table contains core job details.
    job_id = Int('job')
    job = Reference(job_id, Job.id)

    # This is the POFile which needs its statistics updated.
    pofile_id = Int('pofile')
    pofile = Reference(pofile_id, POFile.id)

    def __init__(self, pofile):
        self.job = Job()
        self.pofile = pofile
        super(POFileStatsJob, self).__init__()

    def getOperationDescription(self):
        """See `IRunnableJob`."""
        return 'updating POFile statistics'

    def run(self):
        """See `IRunnableJob`."""
        logger = logging.getLogger()
        logger.info('Updating statistics for %s' % self.pofile.title)
        self.pofile.updateStatistics()

    @staticmethod
    def iterReady():
        """See `IJobSource`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find((POFileStatsJob),
            And(POFileStatsJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs)))


def schedule(pofile):
    """Schedule a job to update a POFile's stats (if not scheduled).

    If a new job is scheduled, it is returned.  If not, None is returned.
    """
    # If there's already two jobs for the pofile, don't create a new one.
    # This is to reduce the number of jobs run if several edits are quickly
    # made to the same POFile.  Why two jobs and not one?  If only one were
    # allowed then there would be a race condition in which one process checks
    # to see if a job is needed, finds that one already exists and doesn't
    # create a new one.  At the same time the processing for that job has
    # already started and the new changes are missed.  We could have avoided
    # the second job by making the job runner script smarter, but since the
    # job processing isn't resource intensive, we accept the duplicate work as
    # not worth the extra effort to avoid.  This way we can use the stock job
    # runner script.
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    jobs = store.find(
        POFileStatsJob,
        POFileStatsJob.pofile == pofile,
        POFileStatsJob.job == Job.id,
        Job.id.is_in(Job.ready_jobs)
        ).all()

    if len(jobs) in (0, 1):
        job = POFileStatsJob(pofile)
    else:
        job = None

    return job
