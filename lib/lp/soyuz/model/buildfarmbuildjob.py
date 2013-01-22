# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildFarmBuildJob',
    ]


from zope.interface import implements

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJobOld
from lp.soyuz.interfaces.buildfarmbuildjob import IBuildFarmBuildJob


class BuildFarmBuildJob(BuildFarmJobOld):
    """See `IBuildFaramBuildJob`."""
    implements(IBuildFarmBuildJob)

    def __init__(self, build):
        """Store the build for this package build farm job.

        XXX 2010-04-12 michael.nelson bug=536700
        The build param will no longer be necessary once BuildFarmJob is
        itself a concrete class. This class (PackageBuildFarmJob)
        will also be renamed PackageBuild and turned into a concrete class.
        """
        super(BuildFarmBuildJob, self).__init__()
        self.build = build

    def getTitle(self):
        """See `IBuildFarmJob`."""
        return self.build.title

    def jobStarted(self):
        """See `IBuildFarmJobOld`."""
        # XXX wgrant: builder should be set here.
        self.build.updateStatus(BuildStatus.BUILDING)

    def jobReset(self):
        """See `IBuildFarmJob`."""
        self.build.updateStatus(BuildStatus.NEEDSBUILD)

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        self.build.updateStatus(BuildStatus.NEEDSBUILD)

    def jobCancel(self):
        """See `IBuildFarmJob`."""
        self.build.updateStatus(BuildStatus.CANCELLED)
