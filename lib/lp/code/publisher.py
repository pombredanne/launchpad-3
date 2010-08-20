# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code's custom publication."""

__metaclass__ = type
__all__ = [
    'CodeBrowserRequest',
    'CodeLayer',
    'code_request_publication_factory',
    ]


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest,
    IDefaultBrowserLayer,
    )

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest,
    VHostWebServiceRequestPublicationFactory,
    )


class CodeLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Code layer."""


class CodeBrowserRequest(LaunchpadBrowserRequest):
    """Instances of CodeBrowserRequest provide `CodeLayer`."""
    implements(CodeLayer)


def code_request_publication_factory():
    return VHostWebServiceRequestPublicationFactory(
        'code', CodeBrowserRequest, LaunchpadBrowserPublication)
