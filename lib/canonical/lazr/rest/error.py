# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Error handling on the webservice."""

__metaclass__ = type
__all__ = [
    'NotFoundView',
    'RequestExpiredView',
    'SystemErrorView',
    'UnauthorizedView',
    'WebServiceExceptionView',
    ]

import traceback

from zope.component import getUtility
from zope.interface import implements
from zope.app.exception.interfaces import ISystemErrorView

from canonical.lazr.interfaces.rest import IWebServiceConfiguration

class WebServiceExceptionView:
    """Generic view handling exceptions on the web service."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def status(self):
        """The HTTP status to use for the response.

        By default, use the __lazr_webservice_error__ attribute on
        the exception.
        """
        return self.context.__lazr_webservice_error__

    def __call__(self):
        """Generate the HTTP response describing the exception."""
        response = self.request.response
        response.setStatus(self.status)
        response.setHeader('Content-Type', 'text/plain')
        if getattr(self.request, 'oopsid', None) is not None:
            response.setHeader('X-Lazr-OopsId', self.request.oopsid)

        show_tracebacks = getUtility(
            IWebServiceConfiguration).show_tracebacks
        if (not show_tracebacks and self.status / 100 == 5):
            # Don't show the exception message; it might contain
            # private information.
            result = [self.context.__class__.__name__]
        else:
            # It's okay to show the exception message
            result = [str(self.context)]

        if show_tracebacks:
            result.append('\n\n')
            result.append(traceback.format_exc())

        return ''.join(result)


class SystemErrorView(WebServiceExceptionView):
    """Server error."""
    implements(ISystemErrorView)

    status = 500

    def isSystemError(self):
        """See `ISystemErrorView`.

        We want these logged in the SiteError log.
        """
        return True


class NotFoundView(WebServiceExceptionView):
    """View for NotFound."""

    status = 404


class UnauthorizedView(WebServiceExceptionView):
    """View for Unauthorized exception."""

    status = 401


class RequestExpiredView(WebServiceExceptionView):
    """View for RequestExpired exception."""

    status = 503
