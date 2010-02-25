# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A configuration class describing the Launchpad web service."""

__metaclass__ = type
__all__ = [
    'LaunchpadWebServiceConfiguration',
]

from zope.component import getUtility

from lazr.restful.simple import BaseWebServiceConfiguration

from canonical.config import config
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.servers import (
    WebServiceClientRequest, WebServicePublication)

from canonical.launchpad import versioninfo


class LaunchpadWebServiceConfiguration(BaseWebServiceConfiguration):

    path_override = "api"
    active_versions = ["beta", "1.0", "devel"]
    view_permission = "launchpad.View"
    set_hop_by_hop_headers = True

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
