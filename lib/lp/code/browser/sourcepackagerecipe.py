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
    def base_branch(self):
        return self.context.recipe_data.base_branch


class SourcePackageRecipeBuildView(LaunchpadView):

    @property
    def status(self):
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
        if self.context.buildqueue_record is None:
            return None
        self.context.buildqueue_record.getEstimatedJobStartTime()

    @property
    def estimate(self):
        return (self.context.datebuilt is None and self.eta is not None)

    @property
    def date(self):
        if self.estimate:
            return self.eta
        return self.context.datebuilt
