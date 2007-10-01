# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Definition of the internet servers that Launchpad uses."""

__metaclass__ = type

import threading
import xmlrpclib

from zope.app.form.browser.widget import SimpleInputWidget
from zope.app.form.browser.itemswidgets import  MultiDataHelper
from zope.app.session.interfaces import ISession
from zope.app.publication.httpfactory import HTTPPublicationRequestFactory
from zope.app.publication.interfaces import IRequestPublicationFactory
from zope.app.server import wsgi
from zope.app.wsgi import WSGIPublisherApplication
from zope.interface import implements
from zope.publisher.browser import (
    BrowserRequest, BrowserResponse, TestRequest)
from zope.publisher.xmlrpc import XMLRPCRequest, XMLRPCResponse
from zope.security.proxy import isinstance as zope_isinstance
from zope.server.http.commonaccesslogger import CommonAccessLogger
from zope.server.http.wsgihttpserver import PMDBWSGIHTTPServer, WSGIHTTPServer

from canonical.cachedproperty import cachedproperty
from canonical.config import config

import canonical.launchpad.layers
from canonical.launchpad.interfaces import (
    IFeedsApplication, IPrivateApplication, IOpenIdApplication,
    IShipItApplication)
from canonical.launchpad.webapp.notifications import (
    NotificationRequest, NotificationResponse, NotificationList)
from canonical.launchpad.webapp.interfaces import (
    ILaunchpadBrowserApplicationRequest, IBasicLaunchpadRequest,
    IBrowserFormNG, INotificationRequest, INotificationResponse,
    UnexpectedFormData)
from canonical.launchpad.webapp.errorlog import ErrorReportRequest
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.webapp.opstats import OpStats


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
    appropriate request and call its setApplicationServer method before it
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


class LaunchpadRequestPublicationFactory:
    """An IRequestPublicationFactory which looks at the Host header.

    It chooses the request and publication factories by looking at the
    Host header and comparing it to the configured site.
    """

    implements(IRequestPublicationFactory)

    _request_factory = None
    _publication_factory = None
    USE_DEFAULTS = object()
    UNHANDLED_HOST = object()

    class VirtualHostRequestPublication:
        """Data type to represent request publication of a single virtual host.
        """
        def __init__(self, conffilename, requestfactory, publicationfactory):
            self.conffilename = conffilename
            self.requestfactory = requestfactory
            self.publicationfactory = publicationfactory
            # Add data from launchpad.conf
            self.vhostconfig = allvhosts.configs[self.conffilename]
            self.allhostnames = set(self.vhostconfig.althostnames
                                    + [self.vhostconfig.hostname])

    def __init__(self):
        # This is run just once at server start-up.

        vhrps = []
        # Use a short form of VirtualHostRequestPublication, for clarity.
        VHRP = self.VirtualHostRequestPublication
        vhrps.append(VHRP('mainsite', LaunchpadBrowserRequest,
            MainLaunchpadPublication))
        vhrps.append(VHRP('blueprints', BlueprintBrowserRequest,
            BlueprintPublication))
        vhrps.append(VHRP('code', CodeBrowserRequest, CodePublication))
        vhrps.append(VHRP('translations', TranslationsBrowserRequest,
            TranslationsPublication))
        vhrps.append(VHRP('bugs', BugsBrowserRequest, BugsPublication))
        vhrps.append(VHRP('answers', AnswersBrowserRequest,
            AnswersPublication))
        vhrps.append(VHRP('openid', OpenIdBrowserRequest, OpenIdPublication))
        vhrps.append(VHRP('shipitubuntu', UbuntuShipItBrowserRequest,
            ShipItPublication))
        vhrps.append(VHRP('shipitkubuntu', KubuntuShipItBrowserRequest,
            ShipItPublication))
        vhrps.append(VHRP('shipitedubuntu', EdubuntuShipItBrowserRequest,
            ShipItPublication))
        vhrps.append(VHRP('xmlrpc',
                          PublicXMLRPCRequest, PublicXMLRPCPublication))
        vhrps.append(VHRP('xmlrpc_private',
                          PrivateXMLRPCRequest, PrivateXMLRPCPublication))
        # Done with using the short form of VirtualHostRequestPublication, so
        # clean up, as we won't need to use it again later.
        del VHRP

        # Set up a dict that maps a host name to a
        # VirtualHostRequestPublication object.
        self._hostname_vhrp = {}

        # Register hostname and althostnames for each virtual host.
        for vhrp in vhrps:
            for hostname in vhrp.allhostnames:
                assert hostname not in self._hostname_vhrp, (
                    "The alt host name '%s' was defined more than once.")
                self._hostname_vhrp[hostname] = vhrp

        self._thread_local = threading.local()

    def _defaultFactories(self):
        from canonical.launchpad.webapp.publication import (
            LaunchpadBrowserPublication)
        return LaunchpadBrowserRequest, LaunchpadBrowserPublication

    def canHandle(self, environment):
        """Only configured domains are handled."""
        if 'HTTP_HOST' not in environment:
            self._thread_local.host = self.USE_DEFAULTS
            return True

        # We look at the wsgi environment to get the port this request is
        # coming in over.  If it's our private port (as determined by matching
        # the PrivateXMLRPC server type), then we route calls to the private
        # xmlrpc host.  The port number can be in one of two places; either
        # it's on the SERVER_PORT environment variable or, as is the case with
        # the test suite, it's on the HTTP_HOST variable after a colon.  Check
        # the former first.
        host = environment['HTTP_HOST']
        server_port = environment.get('SERVER_PORT')
        if server_port is None and ':' in host:
            host, server_port = host.split(':', 1)
        try:
            port = int(server_port)
        except (ValueError, TypeError):
            # This request is not coming in on a usable private port, so don't
            # try to look up the server type.
            pass
        else:
            # See if there is a server configuration with a matching port,
            # using the special PrivateXMLRPC server type name.  If so, set
            # the thread's host name to the proper configuration value and
            # return immediately.
            for server in config.servers:
                if (server.address[1] == port and
                    server.type == 'PrivateXMLRPC'):
                    # This request came over the private XMLRPC port.
                    self._thread_local.host = (
                        config.launchpad.vhosts.xmlrpc_private.hostname)
                    return True
                if (server.address[1] == port and
                    server.type == 'FeedsHTTP'):
                    # This request came over the feeds port.
                    self._thread_local.host = (
                        config.launchpad.vhosts.feeds.hostname)
                    return True

        host = environment['HTTP_HOST']
        if ":" in host:
            assert len(host.split(':')) == 2, (
                "Having a ':' in the host name isn't allowed.")
            host, port = host.split(':')
        if host not in self._hostname_vhrp:
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

        vhrp = self._hostname_vhrp[host]

        # Get hostname, protocol and port out of rooturl.
        rooturlobj = URI(vhrp.vhostconfig.rooturl)

        requestfactory = ApplicationServerSettingRequestFactory(
            vhrp.requestfactory,
            rooturlobj.host,
            rooturlobj.scheme,
            rooturlobj.port)
        return requestfactory, vhrp.publicationfactory


class BasicLaunchpadRequest:
    """Mixin request class to provide stepstogo and breadcrumbs."""

    implements(IBasicLaunchpadRequest)

    def __init__(self, body_instream, environ, response=None):
        self.breadcrumbs = []
        self.traversed_objects = []
        self._wsgi_keys = set()
        super(BasicLaunchpadRequest, self).__init__(
            body_instream, environ, response)

    @property
    def stepstogo(self):
        return StepsToGo(self)

    def retry(self):
        """See IPublisherRequest."""
        new_request = super(BasicLaunchpadRequest, self).retry()
        # propagate the list of keys we have set in the WSGI environment
        new_request._wsgi_keys = self._wsgi_keys
        return new_request

    def getNearest(self, *some_interfaces):
        """See ILaunchpadBrowserApplicationRequest.getNearest()"""
        for context in reversed(self.traversed_objects):
            for iface in some_interfaces:
                if iface.providedBy(context):
                    return context, iface
        return None, None

    def setInWSGIEnvironment(self, key, value):
        """Set a key-value pair in the WSGI environment of this request.

        Raises KeyError if the key is already present in the environment
        but not set with setInWSGIEnvironment().
        """
        # This method expects the BasicLaunchpadRequest mixin to be used
        # with a base that provides self._orig_env.
        if key not in self._wsgi_keys and key in self._orig_env:
            raise KeyError("'%s' already present in wsgi environment." % key)
        self._orig_env[key] = value
        self._wsgi_keys.add(key)


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

    @cachedproperty
    def form_ng(self):
        """See ILaunchpadBrowserApplicationRequest."""
        return BrowserFormNG(self.form)


class BrowserFormNG:
    """Wrapper that provides IBrowserFormNG around a regular form dict."""

    implements(IBrowserFormNG)

    def __init__(self, form):
        """Create a new BrowserFormNG that wraps a dict containing form data."""
        self.form = form

    def __contains__(self, name):
        """See IBrowserFormNG."""
        return name in self.form

    def __iter__(self):
        """See IBrowserFormNG."""
        return iter(self.form)

    def getOne(self, name, default=None):
        """See IBrowserFormNG."""
        value = self.form.get(name, default)
        if zope_isinstance(value, (list, tuple)):
            raise UnexpectedFormData(
                'Expected only one value form field %s: %s' % (name, value))
        return value

    def getAll(self, name, default=None):
        """See IBrowserFormNG."""
        # We don't want a mutable as a default parameter, so we use None as a
        # marker.
        if default is None:
            default = []
        else:
            assert zope_isinstance(default, list), (
                "default should be a list: %s" % default)
        value = self.form.get(name, default)
        if not zope_isinstance(value, list):
            value = [value]
        return value


class Zope3WidgetsUseIBrowserFormNGMonkeyPatch:
    """Make Zope3 widgets use IBrowserFormNG.

    Replace the SimpleInputWidget._getFormInput method with one using
    `IBrowserFormNG`.
    """

    installed = False

    @classmethod
    def install(cls):
        """Install the monkey patch."""
        assert not cls.installed, "Monkey patch is already installed."
        def _getFormInput_single(self):
            """Return the submitted form value.

            :raises UnexpectedFormData: If more than one value is submitted.
            """
            return self.request.form_ng.getOne(self.name)

        def _getFormInput_multi(self):
            """Return the submitted form values.
            """
            return self.request.form_ng.getAll(self.name)

        # Save the original method and replace it with fixed ones.
        # We don't save MultiDataHelper._getFormInput because it doesn't
        # override the one in SimpleInputWidget.
        cls._original__getFormInput = SimpleInputWidget._getFormInput
        SimpleInputWidget._getFormInput = _getFormInput_single
        MultiDataHelper._getFormInput = _getFormInput_multi
        cls.installed = True

    @classmethod
    def uninstall(cls):
        """Uninstall the monkey patch."""
        assert cls.installed, "Monkey patch is not installed."

        # Restore saved method.
        SimpleInputWidget._getFormInput = cls._original__getFormInput
        del MultiDataHelper._getFormInput
        cls.installed = False


Zope3WidgetsUseIBrowserFormNGMonkeyPatch.install()


class LaunchpadBrowserResponse(NotificationResponse, BrowserResponse):

    # Note that NotificationResponse defines a 'redirect' method which
    # needs to override the 'redirect' method in BrowserResponse
    def __init__(self, header_output=None, http_transaction=None):
        super(LaunchpadBrowserResponse, self).__init__(
                header_output, http_transaction
                )

    def redirect(self, location, status=None, temporary_if_possible=False):
        """Do a redirect.

        If temporary_if_possible is True, then do a temporary redirect
        if this is a HEAD or GET, otherwise do a 303.

        See RFC 2616.

        The interface doesn't say that redirect returns anything.
        However, Zope's implementation does return the location given.  This
        is largely useless, as it is just the location given which is often
        relative.  So we won't return anything.
        """
        if temporary_if_possible:
            assert status is None, (
                "Do not set 'status' if also setting 'temporary_if_possible'.")
            method = self._request.method
            if method == 'GET' or method == 'HEAD':
                status = 307
            else:
                status = 303
        super(LaunchpadBrowserResponse, self).redirect(
                unicode(location).encode('UTF-8'), status=status
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

    It provides LaunchpadLayer and adds a mock INotificationRequest
    implementation.

    >>> canonical.launchpad.layers.LaunchpadLayer.providedBy(request)
    True
    >>> INotificationRequest.providedBy(request)
    True
    >>> request.uuid == request.response.uuid
    True
    >>> request.notifications is request.response.notifications
    True

    It also provides the form_ng attribute that is available from
    LaunchpadBrowserRequest.

    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IBrowserFormNG, request.form_ng)
    True
    """
    implements(INotificationRequest, IBasicLaunchpadRequest,
               canonical.launchpad.layers.LaunchpadLayer)

    def __init__(self, body_instream=None, environ=None, form=None,
                 skin=None, outstream=None, method='GET', **kw):
        super(LaunchpadTestRequest, self).__init__(
            body_instream=body_instream, environ=environ, form=form,
            skin=skin, outstream=outstream, REQUEST_METHOD=method, **kw)
        self.breadcrumbs = []
        self.traversed_objects = []

    @property
    def uuid(self):
        return self.response.uuid

    @property
    def notifications(self):
        """See INotificationRequest."""
        return self.response.notifications

    @property
    def stepstogo(self):
        """See IBasicLaunchpadRequest."""
        return StepsToGo(self)

    def getNearest(self, *some_interfaces):
        """See IBasicLaunchpadRequest."""
        return None, None

    def _createResponse(self):
        """As per zope.publisher.browser.BrowserRequest._createResponse"""
        return LaunchpadTestResponse()

    @property
    def form_ng(self):
        """See ILaunchpadBrowserApplicationRequest."""
        return BrowserFormNG(self.form)


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


class LaunchpadAccessLogger(CommonAccessLogger):

    def log(self, task):
        """Receives a completed task and logs it in launchpad log format.

        task IP address
        X_FORWARDED_FOR
        HOST
        datetime task started
        request string  (1st line of request)
        response status
        response bytes written
        launchpad user id
        launchpad page id
        REFERER
        USER_AGENT

        """
        request_headers = task.request_data.headers
        cgi_env = task.getCGIEnvironment()

        x_forwarded_for = request_headers.get('X_FORWARDED_FOR', '')
        host = request_headers.get('HOST', '')
        start_time = self.log_date_string(task.start_time)
        first_line = task.request_data.first_line
        status = task.status
        bytes_written = task.bytes_written
        userid = cgi_env.get('launchpad.userid', '')
        pageid = cgi_env.get('launchpad.pageid', '')
        referer = request_headers.get('REFERER', '')
        user_agent = request_headers.get('USER_AGENT', '')

        self.output.logRequest(
            task.channel.addr[0],
            ' - "%s" "%s" [%s] "%s" %s %d "%s" "%s" "%s" "%s"\n' % (
                x_forwarded_for,
                host,
                start_time,
                first_line,
                status,
                bytes_written,
                userid,
                pageid,
                referer,
                user_agent
                )
           )


http = wsgi.ServerType(
    WSGIHTTPServer,
    WSGIPublisherApplication,
    LaunchpadAccessLogger,
    8080,
    True)

pmhttp = wsgi.ServerType(
    PMDBWSGIHTTPServer,
    WSGIPublisherApplication,
    LaunchpadAccessLogger,
    8081,
    True)

debughttp = wsgi.ServerType(
    WSGIHTTPServer,
    WSGIPublisherApplication,
    LaunchpadAccessLogger,
    8082,
    True,
    requestFactory=DebugLayerRequestFactory)

privatexmlrpc = wsgi.ServerType(
    WSGIHTTPServer,
    WSGIPublisherApplication,
    LaunchpadAccessLogger,
    8080,
    True)

# ---- mainsite

class MainLaunchpadPublication(LaunchpadBrowserPublication):
    """The publication used for the main Launchpad site."""

# ---- blueprint

class BlueprintBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.BlueprintLayer)

class BlueprintPublication(LaunchpadBrowserPublication):
    """The publication used for the Blueprint site."""

# ---- code

class CodePublication(LaunchpadBrowserPublication):
    """The publication used for the Code site."""

class CodeBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.CodeLayer)

# ---- translations

class TranslationsPublication(LaunchpadBrowserPublication):
    """The publication used for the Translations site."""

class TranslationsBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.TranslationsLayer)

# ---- bugs

class BugsPublication(LaunchpadBrowserPublication):
    """The publication used for the Bugs site."""

class BugsBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.BugsLayer)

# ---- answers

class AnswersPublication(LaunchpadBrowserPublication):
    """The publication used for the Answers site."""

class AnswersBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.AnswersLayer)

# ---- shipit

class ShipItPublication(LaunchpadBrowserPublication):
    """The publication used for the ShipIt sites."""

    root_object_interface = IShipItApplication

class UbuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.ShipItUbuntuLayer)

class KubuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.ShipItKUbuntuLayer)

class EdubuntuShipItBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.ShipItEdUbuntuLayer)

# ---- xmlrpc

class PublicXMLRPCPublication(LaunchpadBrowserPublication):
    """The publication used for public XML-RPC requests."""
    def handleException(self, object, request, exc_info, retry_allowed=True):
        LaunchpadBrowserPublication.handleException(
                self, object, request, exc_info, retry_allowed
                )
        OpStats.stats['xml-rpc faults'] += 1

    def endRequest(self, request, object):
        OpStats.stats['xml-rpc requests'] += 1
        return LaunchpadBrowserPublication.endRequest(self, request, object)


class PublicXMLRPCRequest(BasicLaunchpadRequest, XMLRPCRequest,
                          ErrorReportRequest):
    """Request type for doing public XML-RPC in Launchpad."""

    def _createResponse(self):
        return PublicXMLRPCResponse()


class PublicXMLRPCResponse(XMLRPCResponse):
    """Response type for doing public XML-RPC in Launchpad."""

    def handleException(self, exc_info):
        # If we don't have a proper xmlrpclib.Fault, and we have
        # logged an OOPS, create a Fault that reports the OOPS ID to
        # the user.
        exc_value = exc_info[1]
        if not isinstance(exc_value, xmlrpclib.Fault):
            request = get_current_browser_request()
            if request is not None and request.oopsid is not None:
                exc_info = (xmlrpclib.Fault,
                            xmlrpclib.Fault(-1, request.oopsid),
                            None)
        XMLRPCResponse.handleException(self, exc_info)


class PrivateXMLRPCPublication(PublicXMLRPCPublication):
    """The publication used for private XML-RPC requests."""

    root_object_interface = IPrivateApplication

    def traverseName(self, request, ob, name):
        """Traverse to an end point or let normal traversal do its thing."""
        assert isinstance(request, PrivateXMLRPCRequest), (
            'Not a private XML-RPC request')
        missing = object()
        end_point = getattr(ob, name, missing)
        if end_point is missing:
            return super(PrivateXMLRPCPublication, self).traverseName(
                request, ob, name)
        return end_point


class PrivateXMLRPCRequest(PublicXMLRPCRequest):
    """Request type for doing private XML-RPC in Launchpad."""
    # For now, the same as public requests.

# ---- feeds

class FeedsPublication(LaunchpadBrowserPublication):
    """The publication used for Launchpad feed requests."""

    root_object_interface = IFeedsApplication

    def traverseName(self, request, ob, name):
        """Traverse to an end point or let normal traversal do its thing."""
        assert isinstance(request, FeedsRequest), (
            'Not a feeds request')
        missing = object()
        end_point = getattr(ob, name, missing)
        if end_point is missing:
            return super(FeedsPublication, self).traverseName(
                request, ob, name)
        return end_point


class FeedsRequest(LaunchpadBrowserRequest):
    """Request type for a launchpad feed."""
    implements(canonical.launchpad.layers.FeedsLayer)


# ---- openid

class OpenIdPublication(LaunchpadBrowserPublication):
    """The publication used for OpenId requests."""

    root_object_interface = IOpenIdApplication


class OpenIdBrowserRequest(LaunchpadBrowserRequest):
    implements(canonical.launchpad.layers.OpenIdLayer)

