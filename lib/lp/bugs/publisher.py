# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bugs' custom publication."""

__metaclass__ = type
__all__ = [
    'BugsBrowserRequest',
    'BugsLayer',
    'bugs_request_publication_factory',
    'LaunchpadBugContainer',
    ]


from zope.interface import implementer
from zope.publisher.interfaces.browser import (
    IBrowserRequest,
    IDefaultBrowserLayer,
    )

from lp.services.webapp.interfaces import (
    IFacet,
    ILaunchpadContainer,
    )
from lp.services.webapp.publication import LaunchpadBrowserPublication
from lp.services.webapp.publisher import LaunchpadContainer
from lp.services.webapp.servers import (
    LaunchpadBrowserRequest,
    VHostWebServiceRequestPublicationFactory,
    )


@implementer(IFacet)
class BugsFacet:

    name = "bugs"
    rootsite = "bugs"
    text = "Bugs"
    default_view = "+bugs"


class BugsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Bugs layer."""


@implementer(BugsLayer)
class BugsBrowserRequest(LaunchpadBrowserRequest):
    """Instances of BugBrowserRequest provide `BugsLayer`."""


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
