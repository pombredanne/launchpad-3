# Copyright 2009 Canonical Ltd.  All rights reserved.


__metaclass__ = type
all = [
    'ubuntu_request_publication_factory',
    'kubuntu_request_publication_factory',
    'edubuntu_request_publication_factory',
    ]


from zope.interface import implements

from canonical.launchpad import versioninfo
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    AccountPrincipalMixin, LaunchpadBrowserRequest,
    VirtualHostRequestPublicationFactory)
from canonical.launchpad.webapp.vhosts import allvhosts

from canonical.shipit.interfaces.shipit import IShipItApplication
from canonical.shipit.layers import (
    ShipItEdUbuntuLayer, ShipItKUbuntuLayer, ShipItUbuntuLayer)


class ShipItPublication(AccountPrincipalMixin, LaunchpadBrowserPublication):
    """The publication used for the ShipIt sites."""

    root_object_interface = IShipItApplication


class UbuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(ShipItUbuntuLayer)

    def getRootURL(self, rootsite):
        """See IBasicLaunchpadRequest."""
        return allvhosts.configs['shipitubuntu'].rooturl

    @property
    def icing_url(self):
        """The URL to the directory containing resources for this request."""
        return "%s+icing-ubuntu/rev%d" % (
            allvhosts.configs['shipitubuntu'].rooturl, versioninfo.revno)


class KubuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(ShipItKUbuntuLayer)

    def getRootURL(self, rootsite):
        """See IBasicLaunchpadRequest."""
        return allvhosts.configs['shipitkubuntu'].rooturl

    @property
    def icing_url(self):
        """The URL to the directory containing resources for this request."""
        return "%s+icing-kubuntu/rev%d" % (
            allvhosts.configs['shipitkubuntu'].rooturl, versioninfo.revno)


class EdubuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(ShipItEdUbuntuLayer)

    def getRootURL(self, rootsite):
        """See IBasicLaunchpadRequest."""
        return allvhosts.configs['shipitedubuntu'].rooturl

    @property
    def icing_url(self):
        """The URL to the directory containing resources for this request."""
        return "%s+icing-edubuntu/rev%d" % (
            allvhosts.configs['shipitedubuntu'].rooturl, versioninfo.revno)


def ubuntu_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'shipitubuntu', UbuntuShipItBrowserRequest, ShipItPublication)


def kubuntu_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'shipitkubuntu', KubuntuShipItBrowserRequest, ShipItPublication)


def edubuntu_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'shipitedubuntu', EdubuntuShipItBrowserRequest, ShipItPublication)
