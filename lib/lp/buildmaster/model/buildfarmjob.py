# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BuildFarmJob']


from zope.interface import implements

from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob


class BuildFarmJob:
    """Mix-in class for `IBuildFarmJob` implementations."""
    implements(IBuildFarmJob)

    def score(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def getLogFileName(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def getName(self):
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

    @staticmethod
    def getPendingJobsQuery(min_score, processor, virtualized):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    @property
    def processor(self):
        """See `IBuildFarmJob`."""
        return None

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return None

