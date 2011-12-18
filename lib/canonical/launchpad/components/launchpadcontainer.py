# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ILaunchpadContainer adapters."""

__metaclass__ = type
__all__ = [
    'LaunchpadBugContainer',
    'LaunchpadProductContainer',
    'LaunchpadDistributionSourcePackageContainer',
    ]


from canonical.launchpad.webapp.interfaces import ILaunchpadContainer
from canonical.launchpad.webapp.publisher import LaunchpadContainer


class LaunchpadBugContainer(LaunchpadContainer):

    def isWithin(self, scope):
        """Is this bug within the given scope?

        A bug is in the scope of any of its bugtasks' targets.
        """
        for bugtask in self.context.bugtasks:
            if ILaunchpadContainer(bugtask.target).isWithin(scope):
                return True
        return False


class LaunchpadProductContainer(LaunchpadContainer):

    def isWithin(self, scope):
        """Is this product within the given scope?

        A product is within itself or its project.
        """

        return scope == self.context or scope == self.context.project


class LaunchpadDistributionSourcePackageContainer(LaunchpadContainer):

    def isWithin(self, scope):
        """Is this distribution source package within the given scope?

        A distribution source package is within its distribution.
        """
        return scope == self.context or scope == self.context.distribution
