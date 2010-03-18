# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__metaclass__ = type

__all__ = []

from lp.buildmaster.interfaces.buildbase import BuildStatus
from canonical.launchpad.webapp import (
    LaunchpadView)


class SourcePackageRecipeView(LaunchpadView):
    """Default view of a SourcePackageRecipe."""

    @property
    def title(self):
        return self.context.name

    label = title

    @property
    def builds(self):
        """A list of interesting builds.

        All pending builds are shown, as well as 1-5 recent builds.
        Recent builds are ordered by date completed.
        """
        builds = list(self.context.getBuilds(pending=True))
        for build in self.context.getBuilds():
            builds.append(build)
            if len(builds) >= 5:
                break
        builds.reverse()
        return builds


class SourcePackageRecipeBuildView(LaunchpadView):
    """Default view of a SourcePackageRecipeBuild."""

    @property
    def status(self):
        """A human-friendly status string."""
        description = {
            BuildStatus.NEEDSBUILD: 'Pending build',
            BuildStatus.FULLYBUILT: 'Successful build',
            BuildStatus.FAILEDTOBUILD: 'Failed to build',
            BuildStatus.MANUALDEPWAIT:
                'Could not build because of missing dependencies',
            BuildStatus.CHROOTWAIT:
                'Could not build because of chroot issues',
            BuildStatus.SUPERSEDED:
                'Could not build because source package was superseded',
            BuildStatus.BUILDING:
                'Currently building',
            BuildStatus.FAILEDTOUPLOAD:
                'Could not be uploaded correctly',
        }
        if self.context.buildstate == BuildStatus.NEEDSBUILD:
            if self.eta is None:
                return 'No suitable builders'
        return description[self.context.buildstate]

    @property
    def eta(self):
        """The datetime when the build job is estimated to begin."""
        if self.context.buildqueue_record is None:
            return None
        return self.context.buildqueue_record.getEstimatedJobStartTime()

    @property
    def date(self):
        """The date when the build complete or will begin."""
        if self.estimate:
            return self.eta
        return self.context.datebuilt

    @property
    def estimate(self):
        """If true, the date value is an estimate."""
        return (self.context.datebuilt is None and self.eta is not None)
