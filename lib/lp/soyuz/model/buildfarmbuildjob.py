# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildFarmBuildJob',
    ]


from zope.interface import implements

from canonical.database.constants import UTC_NOW
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
        """See `IBuildFarmJob`."""
        self.build.status = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        self.build.date_started = UTC_NOW
        if self.build.date_first_dispatched is None:
            self.build.date_first_dispatched = UTC_NOW

    def jobReset(self):
        """See `IBuildFarmJob`."""
        self.build.status = BuildStatus.NEEDSBUILD

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        self.build.status = BuildStatus.NEEDSBUILD

    def jobCancel(self):
        """See `IBuildFarmJob`."""
        self.build.status = BuildStatus.CANCELLED
