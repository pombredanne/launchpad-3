# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type
__all__ = ['vostok_request_publication_factory']


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad import versioninfo
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    AccountPrincipalMixin, LaunchpadBrowserRequest,
    VirtualHostRequestPublicationFactory)
from canonical.launchpad.webapp.vhosts import allvhosts


class VostokLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The `Vostok` layer."""


class VostokPublication(AccountPrincipalMixin, LaunchpadBrowserPublication):
    """The publication used for the  sites."""
    # Can override root object here.  Not sure if we need to.


class VostokBrowserRequest(LaunchpadBrowserRequest):
    implements(VostokLayer)

    def getRootURL(self, rootsite):
        """See IBasicLaunchpadRequest."""
        return allvhosts.configs['shipitubuntu'].rooturl

    @property
    def icing_url(self):
        """The URL to the directory containing resources for this request."""
        return "%s+icing-ubuntu/rev%d" % (
            allvhosts.configs['vostok'].rooturl, versioninfo.revno)


def vostok_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'vostok', VostokBrowserRequest, VostokPublication)
