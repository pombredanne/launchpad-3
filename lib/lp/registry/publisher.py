# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ILaunchpadContainer adapters."""

__metaclass__ = type
__all__ = [
    'LaunchpadProductContainer',
    ]


from lp.services.webapp.interfaces import ILaunchpadContainer
from lp.services.webapp.publisher import LaunchpadContainer


class LaunchpadProductContainer(LaunchpadContainer):

    def getParentContainers(self):
        """See `ILaunchpadContainer`."""
        # A project is within its project group.
        if self.context.projectgroup is not None:
            yield ILaunchpadContainer(self.context.projectgroup)
