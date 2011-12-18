# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bugs' custom publication."""

__metaclass__ = type
__all__ = [
    'BugsBrowserRequest',
    'BugsLayer',
    'bugs_request_publication_factory',
    'LaunchpadBugContainer',
    ]


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest,
    IDefaultBrowserLayer,
    )


from canonical.launchpad.webapp.interfaces import ILaunchpadContainer
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.publisher import LaunchpadContainer
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest,
    VHostWebServiceRequestPublicationFactory,
    )


class BugsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Bugs layer."""


class BugsBrowserRequest(LaunchpadBrowserRequest):
    """Instances of BugBrowserRequest provide `BugsLayer`."""
    implements(BugsLayer)


def bugs_request_publication_factory():
    return VHostWebServiceRequestPublicationFactory(
        'bugs', BugsBrowserRequest, LaunchpadBrowserPublication)


class LaunchpadBugContainer(LaunchpadContainer):

    def isWithin(self, scope):
        """Is this bug within the given scope?

        A bug is in the scope of any of its bugtasks' targets.
        """
        for bugtask in self.context.bugtasks:
            if ILaunchpadContainer(bugtask.target).isWithin(scope):
                return True
        return False
