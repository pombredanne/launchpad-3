# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['PackageBuildFarmJob']


from canonical.database.constants import UTC_NOW

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob


class PackageBuildFarmJob(BuildFarmJob):
    """Mix-in class for `IBuildFarmJob` implementations for package builds."""

    def getTitle(self):
        """See `IBuildFarmJob`."""
        return self.build.title

    def jobStarted(self):
        """See `IBuildFarmJob`."""
        self.build.buildstate = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        if self.build.date_first_dispatched is None:
            self.build.date_first_dispatched = UTC_NOW

    def jobReset(self):
        """See `IBuildFarmJob`."""
        self.build.buildstate = BuildStatus.NEEDSBUILD

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        self.build.buildstate = BuildStatus.NEEDSBUILD
