# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vostok's custom publication."""

__metaclass__ = type
__all__ = [
    'VostokBrowserRequest',
    'VostokLayer',
    'vostok_request_publication_factory',
    ]


from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)
from canonical.launchpad.webapp.vhosts import allvhosts


class VostokLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Vostok layer."""


class VostokRequestMixin:
    """This mixin defines behaviour for the real and test Vostok requests."""

    implements(VostokLayer)

    def getRootURL(self, rootsite):
        """See `IBasicLaunchpadRequest`."""
        return allvhosts.configs['vostok'].rooturl


class VostokBrowserRequest(VostokRequestMixin, LaunchpadBrowserRequest):
    """Request class for Vostok layer."""


class IVostokRoot(Interface):
    """Marker interface for the root vostok object."""


class VostokRoot:
    """The root object for the Vostok site.

    No behaviour here, it just exists so it can have view and navigation
    registrations attached to it.
    """

    implements(IVostokRoot)


class VostokBrowserPublication(LaunchpadBrowserPublication):
    root_object_interface = IVostokRoot


def vostok_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'vostok', VostokBrowserRequest, VostokBrowserPublication)
