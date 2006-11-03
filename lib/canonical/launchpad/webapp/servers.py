# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Definition of the internet servers that Launchpad uses."""

__metaclass__ = type

import threading

from zope.publisher.browser import BrowserRequest, BrowserResponse, TestRequest
from zope.publisher.xmlrpc import XMLRPCRequest
from zope.app.session.interfaces import ISession
from zope.interface import implements
from zope.app.publication.httpfactory import HTTPPublicationRequestFactory
from zope.app.publication.interfaces import IRequestPublicationFactory
from zope.server.http.wsgihttpserver import PMDBWSGIHTTPServer, WSGIHTTPServer
from zope.app.server import wsgi
from zope.app.wsgi import WSGIPublisherApplication
from zope.server.http.commonaccesslogger import CommonAccessLogger
import zope.publisher.publish
from zope.publisher.interfaces import IRequest

from canonical.config import config
import canonical.launchpad.layers
from canonical.launchpad.interfaces import (
    ILaunchpadBrowserApplicationRequest, IBasicLaunchpadRequest)
from canonical.launchpad.webapp.notifications import (
        NotificationRequest, NotificationResponse, NotificationList
        )
from canonical.launchpad.webapp.interfaces import (
        INotificationRequest, INotificationResponse)
from canonical.launchpad.webapp.errorlog import ErrorReportRequest
from canonical.launchpad.webapp.uri import URI


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


class ApplicationServerSettingRequestFactory:
    """Create a request and call its setApplicationServer method.

    Due to the factory-fanatical design of this part of Zope3, we need
    to have a kind of proxying factory here so that we can create an
    approporiate request and call its setApplicationServer method before it
    is used.
    """

    def __init__(self, requestfactory, host, protocol, port):
        self.requestfactory = requestfactory
        self.host = host
        self.protocol = protocol
        self.port = port

    def __call__(self, body_instream, environ, response=None):
        """Equivalent to the request's __init__ method."""
        request = self.requestfactory(body_instream, environ, response)
        request.setApplicationServer(self.host, self.protocol, self.port)
        return request


class LaunchpadBrowserFactory:
    """An IRequestPublicationFactory which looks at the Host header.

    It chooses the request and publication factories by looking at the
    Host header and comparing it to the configured site.
    """

    implements(IRequestPublicationFactory)

    _request_factory = None
    _publication_factory = None
    USE_DEFAULTS = object()
    UNHANDLED_HOST = object()

    def __init__(self):
        # This is run just once at server start-up.

        from canonical.publication import (
            BlueprintPublication, MainLaunchpadPublication, ShipItPublication)
        # Set up a dict which maps a host name to a tuple of a reqest and
        # publication factory.
        self._hostname_requestpublication = {}
        self._setUpHostnames(
            config.launchpad.main_hostname,
            config.launchpad.root_url,
            LaunchpadBrowserRequest,
            MainLaunchpadPublication)
        self._setUpHostnames(
            config.launchpad.blueprint_hostname,
            config.launchpad.blueprint_root_url,
            BlueprintBrowserRequest,
            BlueprintPublication)
        self._setUpHostnames(
            config.launchpad.shipitubuntu_hostname,
            config.launchpad.shipitubuntu_root_url,
            UbuntuShipItBrowserRequest,
            ShipItPublication)

        self._setUpHostnames(
            config.launchpad.shipitkubuntu_hostname,
            config.launchpad.shipitkubuntu_root_url,
            KubuntuShipItBrowserRequest,
            ShipItPublication)

        self._setUpHostnames(
            config.launchpad.shipitedubuntu_hostname,
            config.launchpad.shipitedubuntu_root_url,
            EdubuntuShipItBrowserRequest,
            ShipItPublication)

        self._setUpHostnames(
            config.launchpad.xmlrpc_hostname,
            config.launchpad.root_url,
            LaunchpadXMLRPCRequest,
            MainLaunchpadPublication)

        self._thread_local = threading.local()

    @staticmethod
    def _hostnameStrToList(hostnamestr):
        """Return list of hostname string.

        >>> thismethod = LaunchpadBrowserFactory._hostnameStrToList
        >>> thismethod('foo')
        ['foo']
        >>> thismethod('foo,bar, baz')
        ['foo', 'bar', 'baz']
        >>> thismethod('foo,,bar, ,baz ,')
        ['foo', 'bar', 'baz']
        >>> thismethod('')
        []
        >>> thismethod(' ')
        []

        """
        if not hostnamestr.strip():
            return []
        return [
            name.strip() for name in hostnamestr.split(',') if name.strip()]

    def _setUpHostnames(
        self, hostnamestr, rooturl, requestfactory, publicationfactory):
        """Set up the hostnames from the given config string in the lookup
        table.
        """
        for hostname in self._hostnameStrToList(hostnamestr):
            self._hostname_requestpublication[hostname] = (
                rooturl, requestfactory, publicationfactory)

    def _defaultFactories(self):
        from canonical.publication import LaunchpadBrowserPublication
        return LaunchpadBrowserRequest, LaunchpadBrowserPublication

    def canHandle(self, environment):
        """Only configured domains are handled."""
        from canonical.publication import LaunchpadBrowserPublication
        if 'HTTP_HOST' not in environment:
            self._thread_local.host = self.USE_DEFAULTS
            return True

        host = environment['HTTP_HOST']
        if ":" in host:
            assert len(host.split(':')) == 2, (
                "Having a ':' in the host name isn't allowed.")
            host, port = host.split(':')
        if host not in self._hostname_requestpublication:
            self._thread_local.host = self.UNHANDLED_HOST
            return False
        self._thread_local.host = host
        return True

    def __call__(self):
        """Return the factories chosen in canHandle()."""
        host = self._thread_local.host
        if host is self.USE_DEFAULTS or host == 'localhost':
            # Don't setApplicationServer here, because we don't have enough
            # information about exactly what was intended.
            # Accept 'localhost' here to support running tests, or hitting
            # the launchpad server directly instead of via Apache.
            return self._defaultFactories()
        if host is self.UNHANDLED_HOST:
            raise AssertionError('unhandled host')
        if host is None:
            raise AssertionError('__call__ called before canHandle')
        self._thread_local.host = None

        # Call self.setApplicationServer(host, protocol, port) based on
        # information in the Host header.
        #
        # There's a problem: the Host header sent into apache may omit the port
        # if it is on the default port from the *outside*.  So, we may be
        # unable to tell if HTTP or HTTPS is appropriate.
        # It is safest to assume that we get just the host and not the port.
        # So, we need to have configured all these things...
        # I have the known hosts in the config, as well as the root urls.  that
        # gives me enough informaiton to set the setApplicationServer in these
        # cases.  Where we have an unknown host header, we can just leave
        # things as is.

        rooturl, request_factory, publication_factory = (
            self._hostname_requestpublication[host])

        # Get hostname, protocol and port out of rooturl.
        rooturlobj = URI(rooturl)

        request_factory = ApplicationServerSettingRequestFactory(
            request_factory,
            rooturlobj.host,
            rooturlobj.scheme,
            rooturlobj.port)
        return request_factory, publication_factory


class BasicLaunchpadRequest:
    """Mixin request class to provide stepstogo and breadcrumbs."""

    implements(IBasicLaunchpadRequest)

    def __init__(self, body_instream, environ, response=None):
        self.breadcrumbs = []
        self.traversed_objects = []
        super(BasicLaunchpadRequest, self).__init__(
            body_instream, environ, response)

    @property
    def stepstogo(self):
        return StepsToGo(self)

    def getNearest(self, *some_interfaces):
        """See ILaunchpadBrowserApplicationRequest.getNearest()"""
        for context in reversed(self.traversed_objects):
            for iface in some_interfaces:
                if iface.providedBy(context):
                    return context, iface
        return None, None


class LaunchpadBrowserRequest(BasicLaunchpadRequest, BrowserRequest,
                              NotificationRequest, ErrorReportRequest):
    """Integration of launchpad mixin request classes to make an uber
    launchpad request class.
    """

    implements(ILaunchpadBrowserApplicationRequest)

    retry_max_count = 5    # How many times we're willing to retry

    def __init__(self, body_instream, environ, response=None):
        super(LaunchpadBrowserRequest, self).__init__(
            body_instream, environ, response)

    def _createResponse(self):
        """As per zope.publisher.browser.BrowserRequest._createResponse"""
        return LaunchpadBrowserResponse()


class LaunchpadBrowserResponse(NotificationResponse, BrowserResponse):

    # Note that NotificationResponse defines a 'redirect' method which
    # needs to override the 'redirect' method in BrowserResponse
    def __init__(self, header_output=None, http_transaction=None):
        super(LaunchpadBrowserResponse, self).__init__(
                header_output, http_transaction
                )


def adaptResponseToSession(response):
    """Adapt LaunchpadBrowserResponse to ISession"""
    return ISession(response._request)


def adaptRequestToResponse(request):
    """Adapt LaunchpadBrowserRequest to LaunchpadBrowserResponse"""
    return request.response


class LaunchpadTestRequest(TestRequest):
    """Mock request for use in unit and functional tests.

    >>> request = LaunchpadTestRequest(SERVER_URL='http://127.0.0.1/foo/bar')

    This class subclasses TestRequest - the standard Mock request object
    used in unit tests

    >>> isinstance(request, TestRequest)
    True

    It adds a mock INotificationRequest implementation

    >>> INotificationRequest.providedBy(request)
    True
    >>> request.uuid == request.response.uuid
    True
    >>> request.notifications is request.response.notifications
    True
    """
    implements(INotificationRequest)

    @property
    def uuid(self):
        return self.response.uuid

    @property
    def notifications(self):
        return self.response.notifications

    def _createResponse(self):
        """As per zope.publisher.browser.BrowserRequest._createResponse"""
        return LaunchpadTestResponse()


class LaunchpadTestResponse(LaunchpadBrowserResponse):
    """Mock response for use in unit and functional tests.

    >>> request = LaunchpadTestRequest()
    >>> response = request.response
    >>> isinstance(response, LaunchpadTestResponse)
    True
    >>> INotificationResponse.providedBy(response)
    True

    >>> response.addWarningNotification('%(val)s Notification', val='Warning')
    >>> request.notifications[0].message
    u'Warning Notification'
    """
    implements(INotificationResponse)

    uuid = 'LaunchpadTestResponse'

    _notifications = None

    @property
    def notifications(self):
        if self._notifications is None:
            self._notifications = NotificationList()
        return self._notifications


class BlueprintBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.BlueprintLayer)


class UbuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.ShipItUbuntuLayer)


class KubuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.ShipItKUbuntuLayer)


class EdubuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.ShipItEdUbuntuLayer)


class LaunchpadXMLRPCRequest(BasicLaunchpadRequest, XMLRPCRequest,
                             ErrorReportRequest):
    """Request type for doing XMLRPC in Launchpad."""


class DebugLayerRequestFactory(HTTPPublicationRequestFactory):
    """RequestFactory that sets the DebugLayer on a request."""

    def __call__(self, input_stream, env, output_stream=None):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        assert output_stream is None, 'output_stream is deprecated in Z3.2'

        # Mark the request with the 'canonical.launchpad.layers.debug' layer
        request = HTTPPublicationRequestFactory.__call__(
            self, input_stream, env)
        canonical.launchpad.layers.setFirstLayer(
            request, canonical.launchpad.layers.DebugLayer)
        return request


http = wsgi.ServerType(
    WSGIHTTPServer,
    WSGIPublisherApplication,
    CommonAccessLogger,
    8080,
    True)

pmhttp = wsgi.ServerType(
    PMDBWSGIHTTPServer,
    WSGIPublisherApplication,
    CommonAccessLogger,
    8081,
    True)

debughttp = wsgi.ServerType(
    WSGIHTTPServer,
    WSGIPublisherApplication,
    CommonAccessLogger,
    8082,
    True,
    requestFactory=DebugLayerRequestFactory)
