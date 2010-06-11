#!/usr/bin/python -S
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = []

import _pythonpath

import transaction
from storm.expr import In
from storm.locals import Int, Storm

from canonical.database.sqlbase import sqlvalues
from lp.services.job.model.job import Job
from lp.services.scripts.base import LaunchpadScript
from canonical.launchpad.interfaces import IMasterStore
from canonical.launchpad.utilities.looptuner import TunableLoop


class BugJobPruner(TunableLoop):
    _is_done = False
    maximum_chunk_size = 20000
    minimum_chunk_size = 1

    def isDone(self):
        return self._is_done

    def __call__(self, chunksize):
        from lp.bugs.model.bugjob import BugJob
        store = IMasterStore(Job)

        ids = list(store.find(
            Job.id,
            Job.id == BugJob.job_id)[:int(chunksize)])

        if len(ids) == 0:
            self._is_done = True
            return
        store.find(BugJob, In(BugJob.job_id, ids)).remove()
        store.find(Job, In(Job.id, ids))
        transaction.commit()


class JobsToDelete(Storm):
    __storm_table__ = 'JobsToDelete'
    id = Int(primary=True)


class UnownedJobPruner(TunableLoop):

    _is_done = False
    maximum_chunk_size = 20000

    def __init__(self, *args, **kw):
        super(UnownedJobPruner, self).__init__(*args, **kw)
        self.store = IMasterStore(Job)
        self.store.execute("""
            CREATE TEMPORARY TABLE JobsToDelete AS
            SELECT Job.id AS id
            FROM Job
            EXCEPT SELECT job AS id FROM ApportJob
            EXCEPT SELECT job AS id FROM BranchJob
            EXCEPT SELECT job AS id FROM BranchMergeProposalJob
            EXCEPT SELECT job AS id FROM BugJob
            EXCEPT SELECT job AS id FROM BuildPackageJob
            EXCEPT SELECT job AS id FROM BuildQueue
            EXCEPT SELECT job AS id FROM MergeDirectiveJob
            EXCEPT SELECT job AS id FROM SourcePackageRecipeBuildJob
            """)
        self.store.execute("""
            CREATE UNIQUE INDEX jobstodelete__id__key
            ON JobsToDelete(id)
            """)
        self.store.execute("ANALYZE JobsToDelete")

    def isDone(self):
        return self._is_done

    def __call__(self, chunksize):
        ids = list(self.store.find(JobsToDelete.id)[:int(chunksize)])
        if len(ids) == 0:
            self._is_done = True
            return
        self.store.find(Job, In(Job.id, ids)).remove()
        self.store.find(JobsToDelete, In(JobsToDelete.id, ids)).remove()
        transaction.commit()


class UnownedJobsScript(LaunchpadScript):
    def main(self):
        loop = BugJobPruner(self.logger)
        loop.run()
        loop = UnownedJobPruner(self.logger)
        loop.run()

if __name__ == '__main__':
    script = UnownedJobsScript('unownedjobs', dbuser='postgres')
    script.lock_and_run()
