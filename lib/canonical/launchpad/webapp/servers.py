# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Definition of the internet servers that Launchpad uses."""

__metaclass__ = type

from zope.interface import implements
from zope.app.publication.interfaces import IPublicationRequestFactory
import canonical.launchpad.layers
from zope.server.http.publisherhttpserver import PublisherHTTPServer
from zope.app.server.servertype import ServerType
from zope.server.http.commonaccesslogger import CommonAccessLogger
from canonical.publication import LaunchpadBrowserPublication
from zope.publisher.browser import BrowserRequest
#from zope.publisher.http import HTTPRequest
import zope.publisher.publish


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


class LaunchpadBrowserRequest(BrowserRequest):

    @property
    def stepstogo(self):
        return StepsToGo(self)


class HTTPPublicationRequestFactory:
    implements(IPublicationRequestFactory)

    _browser_methods = 'GET', 'POST', 'HEAD'

    def __init__(self, db):
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

