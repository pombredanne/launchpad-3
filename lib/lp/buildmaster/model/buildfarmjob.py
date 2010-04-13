# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BuildFarmJob']


import hashlib

from zope.component import getUtility
from zope.interface import classProvides, implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob, IBuildFarmCandidateJobSelection,
    ISpecificBuildFarmJobClass)
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet


class BuildFarmJob:
    """Mix-in class for `IBuildFarmJob` implementations."""
    implements(IBuildFarmJob)
    classProvides(
        IBuildFarmCandidateJobSelection, ISpecificBuildFarmJobClass)

    def generateSlaveBuildCookie(self):
        """See `IBuildFarmJob`."""
        buildqueue = getUtility(IBuildQueueSet).getByJob(self.job)

        if buildqueue.processor is None:
            processor = '*'
        else:
            processor = repr(buildqueue.processor.id)

        contents = ';'.join([
            repr(removeSecurityProxy(self.job).id),
            self.job.date_created.isoformat(),
            repr(buildqueue.id),
            buildqueue.job_type.name,
            processor,
            self.getName(),
            ])

        return hashlib.sha1(contents).hexdigest()

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

    @classmethod
    def getByJob(cls, job):
        """See `ISpecificBuildFarmJobClass`.
        This base implementation should work for most build farm job
        types, but some need to override it.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(cls, cls.job == job).one()

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmCandidateJobSelection`."""
        return True

