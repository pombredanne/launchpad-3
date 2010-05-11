# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuildFarmJob',
    'PackageBuildFarmJobDerived',
    ]


from canonical.database.constants import UTC_NOW

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob, BuildFarmJobDerived)


class PackageBuildFarmJob(BuildFarmJob):
    """An implementation of `IBuildFarmJob` for package builds."""

    def __init__(self, build):
        """Store the build for this package build farm job.

        XXX 2010-04-12 michael.nelson bug=536700
        The build param will no longer be necessary once BuildFarmJob is
        itself a concrete class. This class (PackageBuildFarmJob)
        will also be renamed PackageBuild and turned into a concrete class.
        """
        super(PackageBuildFarmJob, self).__init__()
        self.build = build

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


class PackageBuildFarmJobDerived(BuildFarmJobDerived):
    """Override the base delegate.

    Ensure that we use a build farm job specific to packages.
    """
    def _set_build_farm_job(self):
        self._build_farm_job = PackageBuildFarmJob(self.build)
