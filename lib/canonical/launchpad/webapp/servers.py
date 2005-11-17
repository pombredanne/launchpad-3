# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Definition of the internet servers that Launchpad uses."""

__metaclass__ = type

from zope.publisher.browser import BrowserRequest, BrowserResponse
from zope.app.session.interfaces import ISession
from zope.interface import Interface, implements
from zope.app.publication.interfaces import IPublicationRequestFactory
from zope.server.http.publisherhttpserver import PublisherHTTPServer
from zope.app.server.servertype import ServerType
from zope.server.http.commonaccesslogger import CommonAccessLogger
import zope.publisher.publish

import canonical.launchpad.layers
from zope.publisher.browser import BrowserRequest
#from zope.publisher.http import HTTPRequest
import zope.publisher.publish
from canonical.launchpad.interfaces import ILaunchpadBrowserApplicationRequest
from canonical.launchpad.webapp.notification import (
        NotificationRequest, NotificationResponse
        )


class StepsToGo:
    """

    >>> class FakeRequest:
    ...     def __init__(self, traversed, stack):
    ...         self._traversed_names = traversed
    ...         self.stack = stack
    ...     def getTraversalStack(self):
    ...         return self.stack
    ...     def setTraversalStack(self, stack):
    ...         self.stack = stack

    >>> request = FakeRequest([], ['baz', 'bar', 'foo'])
    >>> stepstogo = StepsToGo(request)
    >>> stepstogo.startswith()
    True
    >>> stepstogo.startswith('foo')
    True
    >>> stepstogo.startswith('foo', 'bar')
    True
    >>> stepstogo.startswith('foo', 'baz')
    False
    >>> len(stepstogo)
    3
    >>> print stepstogo.consume()
    foo
    >>> request._traversed_names
    ['foo']
    >>> request.stack
    ['baz', 'bar']
    >>> print stepstogo.consume()
    bar
    >>> bool(stepstogo)
    True
    >>> print stepstogo.consume()
    baz
    >>> print stepstogo.consume()
    None
    >>> bool(stepstogo)
    False

    """

    @property
    def _stack(self):
        return self.request.getTraversalStack()

    def __init__(self, request):
        self.request = request

    def consume(self):
        """Remove the next path step and return it.

        Returns None if there are no path steps left.
        """
        stack = self.request.getTraversalStack()
        try:
            nextstep = stack.pop()
        except IndexError:
            return None
        self.request._traversed_names.append(nextstep)
        self.request.setTraversalStack(stack)
        return nextstep

    def startswith(self, *args):
        """Return whether the steps to go start with the names given."""
        if not args:
            return True
        return self._stack[-len(args):] == list(reversed(args))

    def __len__(self):
        return len(self._stack)

    def __nonzero__(self):
        return bool(self._stack)


class LaunchpadBrowserRequest(BrowserRequest, NotificationRequest):

    implements(ILaunchpadBrowserApplicationRequest)

    def __init__(self, body_instream, outstream, environ, response=None):
        self.breadcrumbs = []
        super(LaunchpadBrowserRequest, self).__init__(
            body_instream, outstream, environ, response)

    @property
    def stepstogo(self):
        return StepsToGo(self)

    def _createResponse(self, outstream):
        """As per zope.publisher.browser.BrowserRequest._createResponse"""
        return LaunchpadBrowserResponse(outstream)


class LaunchpadBrowserResponse(NotificationResponse, BrowserResponse):

    # Note that NotificationResponse defines a 'redirect' method which
    # needs to override the 'redirect' method in BrowserResponse
    def __init__(self, outstream, header_output=None, http_transaction=None):
        super(LaunchpadBrowserResponse, self).__init__(
                outstream, header_output, http_transaction
                )


def adaptResponseToSession(response):
    """Adapt LaunchpadBrowserResponse to ISession"""
    return ISession(response._request)

def adaptRequestToResponse(request):
    """Adapt LaunchpadBrowserRequest to LaunchpadBrowserResponse"""
    return request.response


class HTTPPublicationRequestFactory:
    implements(IPublicationRequestFactory)

    _browser_methods = 'GET', 'POST', 'HEAD'

    def __init__(self, db):
        from canonical.publication import LaunchpadBrowserPublication
        ## self._http = HTTPPublication(db)
        self._browser = LaunchpadBrowserPublication(db)

    def __call__(self, input_stream, output_steam, env):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        method = env.get('REQUEST_METHOD', 'GET').upper()

        if method in self._browser_methods:
            request = LaunchpadBrowserRequest(input_stream, output_steam, env)
            request.setPublication(self._browser)
        else:
            raise NotImplementedError()
            ## request = HTTPRequest(input_stream, output_steam, env)
            ## request.setPublication(self._http)

        return request


class DebugLayerRequestFactory(HTTPPublicationRequestFactory):
    """RequestFactory that sets the DebugLayer on a request."""

    def __call__(self, input_stream, output_steam, env):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        # Mark the request with the 'canonical.launchpad.layers.debug' layer
        request = HTTPPublicationRequestFactory.__call__(
            self, input_stream, output_steam, env)
        canonical.launchpad.layers.setFirstLayer(
            request, canonical.launchpad.layers.DebugLayer)
        return request


class PMDBHTTPServer(PublisherHTTPServer):
    """Enter the post-mortem debugger when there's an error"""

    def executeRequest(self, task):
        """Overrides HTTPServer.executeRequest()."""
        env = task.getCGIEnvironment()
        instream = task.request_data.getBodyStream()

        request = self.request_factory(instream, task, env)
        response = request.response
        response.setHeaderOutput(task)
        try:
            zope.publisher.publish.publish(request, handle_errors=False)
        except:
            import sys, pdb
            print "%s:" % sys.exc_info()[0]
            print sys.exc_info()[1]
            pdb.post_mortem(sys.exc_info()[2])
            raise


class InternalHTTPLayerRequestFactory(HTTPPublicationRequestFactory):
    """RequestFactory that sets the InternalHTTPLayer on a request."""

    def __call__(self, input_stream, output_steam, env):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        request = HTTPPublicationRequestFactory.__call__(
            self, input_stream, output_steam, env)
        canonical.launchpad.layers.setFirstLayer(
            request, canonical.launchpad.layers.InternalHTTPLayer)
        return request


http = ServerType(
    PublisherHTTPServer,
    HTTPPublicationRequestFactory,
    CommonAccessLogger,
    8080,
    True)

pmhttp = ServerType(
    PMDBHTTPServer,
    HTTPPublicationRequestFactory,
    CommonAccessLogger,
    8081,
    True)

debughttp = ServerType(
    PublisherHTTPServer,
    DebugLayerRequestFactory,
    CommonAccessLogger,
    8082,
    True)

internalhttp = ServerType(
    PublisherHTTPServer,
    InternalHTTPLayerRequestFactory,
    CommonAccessLogger,
    8083,
    True)
