# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code's custom publication."""

__metaclass__ = type
__all__ = [
    'BranchesFacet',
    'CodeBrowserRequest',
    'CodeLayer',
    'code_request_publication_factory',
    'LaunchpadBranchContainer',
    ]


from zope.component import queryAdapter
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
class BranchesFacet:

    name = "branches"
    rootsite = "code"
    text = "Code"
    default_view = "+branches"


class CodeLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Code layer."""


@implementer(CodeLayer)
class CodeBrowserRequest(LaunchpadBrowserRequest):
    """Instances of CodeBrowserRequest provide `CodeLayer`."""


def code_request_publication_factory():
    return VHostWebServiceRequestPublicationFactory(
        'code', CodeBrowserRequest, LaunchpadBrowserPublication)


class LaunchpadBranchContainer(LaunchpadContainer):

    def getParentContainers(self):
        """See `ILaunchpadContainer`."""
        # A branch is within its target.
        adapter = queryAdapter(
            self.context.target.context, ILaunchpadContainer)
        if adapter is not None:
            yield adapter


class LaunchpadGitRepositoryContainer(LaunchpadContainer):

    def getParentContainers(self):
        """See `ILaunchpadContainer`."""
        # A repository is within its target.
        adapter = queryAdapter(self.context.target, ILaunchpadContainer)
        if adapter is not None:
            yield adapter
