# Copyright 2009 Canonical Ltd.  All rights reserved.

"""A configuration class describing the LAZR example web service."""

__metaclass__ = type
__all__ = [
    'CookbookWebServiceConfiguration',
]

from zope.component import getUtility
from zope.interface import implements

from canonical.lazr.interfaces.rest import (
    IServiceRootResource, IWebServiceConfiguration)
from canonical.lazr.testing.webservice import (
    WebServiceTestPublication, WebServiceTestRequest)

class CookbookWebServiceConfiguration:
    """A configuration object for the cookbook web service."""
    implements(IWebServiceConfiguration)

    path_override = "api"
    service_version_uri_prefix = "1.0"
    view_permission = 'lazr.restful.example.View'
    use_https = False
    code_revision = "test.revision"
    show_tracebacks = True

    def createRequest(self, body_instream, environ):
        """See `IWebServiceConfiguration`."""
        request = WebServiceTestRequest(body_instream, environ)
        request.setPublication(
            WebServiceTestPublication(getUtility(IServiceRootResource)))
        return request
