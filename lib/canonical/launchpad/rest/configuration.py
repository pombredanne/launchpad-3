# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A configuration class describing the Launchpad web service."""

__metaclass__ = type
__all__ = [
    'LaunchpadWebServiceConfiguration',
]

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.lazr.interfaces.rest import IWebServiceConfiguration
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.servers import (
    WebServiceClientRequest, WebServicePublication)

from canonical.launchpad import versioninfo


class LaunchpadWebServiceConfiguration:
    implements(IWebServiceConfiguration)

    path_override = "api"
    service_version_uri_prefix = "beta"
    view_permission = "launchpad.View"

    @property
    def use_https(self):
        return config.vhosts.use_https

    @property
    def code_revision(self):
        return str(versioninfo.revno)

    def createRequest(self, body_instream, environ):
        """See `IWebServiceConfiguration`."""
        request = WebServiceClientRequest(body_instream, environ)
        request.setPublication(WebServicePublication(None))
        return request

    @property
    def default_batch_size(self):
        return config.launchpad.default_batch_size

    @property
    def max_batch_size(self):
        return config.launchpad.max_batch_size

    @property
    def show_tracebacks(self):
        """See `IWebServiceConfiguration`.

        People who aren't developers shouldn't be shown any
        information about the exception that caused an internal server
        error. It might contain private information.
        """
        is_developer = getUtility(ILaunchBag).developer
        return (is_developer or config.canonical.show_tracebacks)

    def get_request_user(self):
        """See `IWebServiceConfiguration`."""
        return getUtility(ILaunchBag).user
