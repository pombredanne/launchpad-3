# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vostok's custom publication."""

__metaclass__ = type
__all__ = [
    'VostokBrowserRequest',
    'VostokLayer',
    'vostok_request_publication_factory',
    ]


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)


class VostokLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Vostok layer."""


class VostokBrowserRequest(LaunchpadBrowserRequest):
    implements(VostokLayer)


# We *might* end up customizing the root object and so need our own
# LaunchpadBrowserPublication subclass.  Not yet though.


def vostok_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'vostok', VostokBrowserRequest, LaunchpadBrowserPublication)
