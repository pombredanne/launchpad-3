# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Publisher classes for the SSO service."""

__metaclass__ = type
__all__ = [
    'openid_request_publication_factory',
    'id_request_publication_factory',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    AccountPrincipalMixin, LaunchpadBrowserRequest, LaunchpadTestRequest,
    VirtualHostRequestPublicationFactory)
from canonical.launchpad.webapp.vhosts import allvhosts

from canonical.signon.interfaces.openidserver import IOpenIDApplication
from canonical.signon.layers import OpenIDLayer


class OpenIDPublication(AccountPrincipalMixin, LaunchpadBrowserPublication):
    """The publication used for OpenID requests."""

    root_object_interface = IOpenIDApplication

    def getApplication(self, request):
        """Return the `IOpenIDApplication`."""
        return getUtility(IOpenIDApplication)

    def maybeNotifyReadOnlyMode(self, request):
        """SSO doesn't care about read-only mode."""
        pass


class OpenIDBrowserRequest(LaunchpadBrowserRequest):
    implements(OpenIDLayer)


class OpenIDServerTestRequest(LaunchpadTestRequest):
    implements(OpenIDLayer)

    def __init__(self, body_instream=None, environ=None, **kw):
        test_environ = {
            'SERVER_URL': allvhosts.configs['openid'].rooturl,
            'HTTP_HOST': allvhosts.configs['openid'].hostname}
        if environ is not None:
            test_environ.update(environ)
        super(OpenIDServerTestRequest, self).__init__(
            body_instream=body_instream, environ=test_environ, **kw)


def openid_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'openid', OpenIDBrowserRequest, OpenIDPublication)

