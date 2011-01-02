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
from zope.interface import (
    implements,
    Interface,
    )
from zope.publisher.interfaces.browser import (
    IBrowserRequest,
    IDefaultBrowserLayer,
    )

from canonical.launchpad.webapp import (
    canonical_url,
    Navigation,
    )
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest,
    LaunchpadBrowserResponse,
    VirtualHostRequestPublicationFactory,
    )
from canonical.launchpad.webapp.vhosts import allvhosts
from lp.registry.interfaces.distribution import IDistributionSet


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

    def _createResponse(self):
        """As per zope.publisher.browser.BrowserRequest._createResponse"""
        return VostokBrowserResponse()


class VostokBrowserResponse(LaunchpadBrowserResponse):

    def redirect(self, location, status=None, trusted=False,
                 temporary_if_possible=False):
        """Override the parent method to make redirects untrusted by default.

        This is so that we don't allow redirects to any hosts other than
        vostok's.
        """
        # Need to call LaunchpadBrowserResponse.redirect() directly because
        # the temporary_if_possible argument only exists there.
        LaunchpadBrowserResponse.redirect(
            self, location, status=status, trusted=trusted,
            temporary_if_possible=temporary_if_possible)


class IVostokRoot(Interface):
    """Marker interface for the root vostok object."""


class VostokRoot:
    """The root object for the Vostok site.

    No behaviour here, it just exists so it can have view and navigation
    registrations attached to it.
    """

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
