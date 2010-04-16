# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BuildFarmJob']


from zope.interface import classProvides, implements

from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob, IBuildFarmCandidateJobSelection)


class BuildFarmJob:
    """A base implementation for `IBuildFarmJob` classes."""
    implements(IBuildFarmJob)
    classProvides(IBuildFarmCandidateJobSelection)

    def score(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def getLogFileName(self):
        """See `IBuildFarmJob`."""
        return 'buildlog.txt'

    def getName(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def getTitle(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def jobStarted(self):
        """See `IBuildFarmJob`."""
        pass

    def jobReset(self):
        """See `IBuildFarmJob`."""
        pass

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        pass

    @property
    def processor(self):
        """See `IBuildFarmJob`."""
        return None

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return None

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `IBuildFarmCandidateJobSelection`."""
        return ('')

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmCandidateJobSelection`."""
        return True


class BuildFarmJobDelegate:
    """Common functionality required by classes delegating IBuildFarmJob.

    This mainly involves ensuring that the instance to which we delegate
    is created.
    """


