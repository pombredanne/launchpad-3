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
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)


class CodeLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Code layer."""


class CodeRequestMixin:

    implements(CodeLayer)


class CodeBrowserRequest(CodeRequestMixin, LaunchpadBrowserRequest):
    pass


def code_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'code', CodeBrowserRequest, LaunchpadBrowserPublication)
