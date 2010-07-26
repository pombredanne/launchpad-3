# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vostok's custom publication."""

__metaclass__ = type
__all__ = [
    'VostokBrowserRequest',
    'VostokLayer',
    'VostokRootNavigation',
    'vostok_request_publication_factory',
    ]


from zope.component import getUtility
from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp import canonical_url, Navigation
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)
from canonical.launchpad.webapp.vhosts import allvhosts

from lp.registry.interfaces.distribution import IDistributionSet


class VostokLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Vostok layer."""


class VostokRequestMixin:

    implements(VostokLayer)

    def getRootURL(self, rootsite):
        """See `IBasicLaunchpadRequest`."""
        return allvhosts.configs['vostok'].rooturl


class VostokBrowserRequest(VostokRequestMixin, LaunchpadBrowserRequest):
    pass


class IVostokRoot(Interface): # might need to inherit from some IRoot thing
    """Marker interface for the root vostok object."""


class VostokRoot:
    implements(IVostokRoot)


class VostokRootNavigation(Navigation):

    usedfor = IVostokRoot

    def traverse(self, name):
        distro = getUtility(IDistributionSet)[name]
        if distro is not None and distro.name != name:
            # This distro was accessed through one of its aliases, so we
            # must redirect to its canonical URL.
            return self.redirectSubTree(canonical_url(distro), status=301)
        return distro


class VostokBrowserPublication(LaunchpadBrowserPublication):
    root_object_interface = IVostokRoot


def vostok_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'vostok', VostokBrowserRequest, VostokBrowserPublication)
