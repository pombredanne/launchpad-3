# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Testing helpers for webservice unit tests."""

__metaclass__ = type
__all__ = [
    'ExampleWebServiceTestCaller',
    'ExampleWebServicePublication',
    'FakeRequest',
    'FakeResponse',
    'MockRootFolder',
    'pprint_entry',
    'WebServiceTestPublication',
    'WebServiceTestRequest',
    'TestPublication',
    ]

import os
import traceback
import simplejson
import urllib
from urlparse import urljoin

from zope.app.testing.functional import HTTPCaller
from zope.component import getUtility, queryMultiAdapter
from zope.interface import implements
from zope.publisher.browser import BrowserRequest
from zope.publisher.interfaces import IPublication, IPublishTraverse, NotFound
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.publisher.publish import mapply
from zope.proxy import ProxyBase
from zope.security.checker import ProxyFactory
from zope.security.management import endInteraction, newInteraction

from canonical.launchpad.webapp.servers import StepsToGo
from canonical.lazr.interfaces.rest import (
    IWebServiceConfiguration, IWebServiceLayer)
from canonical.lazr.rest.publisher import (
    WebServicePublicationMixin, WebServiceRequestTraversal)
from canonical.lazr.rest.example.root import (
    CookbookServiceRootResource)

from lazr.uri import URI

class FakeResponse:
    """Simple response wrapper object."""
    def __init__(self):
        self.status = 599
        self.headers = {}

    def setStatus(self, new_status):
        self.status = new_status

    def setHeader(self, name, value):
        self.headers[name] = value

    def getHeader(self, name):
        """Return the value of the named header."""
        return self.headers.get(name)

    def getStatus(self):
        """Return the response status code."""
        return self.status


class FakeRequest:
    """Simple request object for testing purpose."""
    # IHTTPApplicationRequest makes us eligible for
    # get_current_browser_request()
    implements(IHTTPApplicationRequest, IWebServiceLayer)

    def __init__(self, traversed=None, stack=None):
        self._traversed_names = traversed
        self._stack = stack
        self.response = FakeResponse()
        self.principal = None
        self.interaction = None
        self.traversed_objects = []
        # XXX: noodles 2009-02-12 bug=328462
        # NOTE: There shouldn't be a dependency here on LP code, but
        # some of the tests are using this FakeRequest to create
        # a launchpad.webapp.BatchNavigator object.
        self.query_string_params = {}
        self.method = 'GET'

    def getTraversalStack(self):
        """See `IPublicationRequest`.

        This method is called by traversal machinery.
        """
        return self._stack

    def setTraversalStack(self, stack):
        """See `IPublicationRequest`.

        This method is called by traversal machinery.
        """
        self._stack = stack

    @property
    def stepstogo(self):
        """See IBasicLaunchpadRequest.

        This method is called by traversal machinery.
        """
        return StepsToGo(self)

    def getApplicationURL(self):
        return "http://api.example.org"

    def get(self, key, default=None):
        """Simulate an empty set of request parameters."""
        return default


def pprint_entry(json_body):
    """Pretty-print a webservice entry JSON representation.

    Omits the http_etag key, which is always present and never
    interesting for a test.
    """
    for key, value in sorted(json_body.items()):
        if key != 'http_etag':
            print '%s: %r' % (key, value)


def pprint_collection(json_body):
    """Pretty-print a webservice collection JSON representation."""
    for key, value in sorted(json_body.items()):
        if key != 'entries':
            print '%s: %r' % (key, value)
    print '---'
    for entry in json_body['entries']:
        pprint_entry(entry)
        print '---'


class WebServiceTestRequest(WebServiceRequestTraversal, BrowserRequest):
    """A test request for the webservice."""
    implements(IWebServiceLayer)


class TestPublication:
    """Very simple implementation of `IPublication`.

    The object pass to the constructor is returned by getApplication().
    """
    implements(IPublication)

    def __init__(self, application):
        """Create the test publication.

        The object at which traversal should start is passed as parameter.
        """
        self.application = application

    def beforeTraversal(self, request):
        """Sets the request as the current interaction.

        (It also ends any previous interaction, that's convenient when
        tests don't go through the whole request.)
        """
        endInteraction()
        newInteraction(request)

    def getApplication(self, request):
        """Returns the application passed to the constructor."""
        return self.application

    def callTraversalHooks(self, request, ob):
        """Does nothing."""

    def traverseName(self, request, ob, name):
        """Traverse by looking of an `IPublishTraverse` adapter.

        The object is security wrapped.
        """
        # XXX flacoste 2009/03/06 bug=338831. This is copied from
        # zope.app.publication.publicationtraverse.PublicationTraverse.
        # This should really live in zope.publisher, we are copying because
        # we don't want to depend on zope.app stuff.
        # Namespace support was dropped.
        if name == '.':
            return ob

        if IPublishTraverse.providedBy(ob):
            ob2 = ob.publishTraverse(request, name)
        else:
            # self is marker.
            adapter = queryMultiAdapter(
                (ob, request), IPublishTraverse, default=self)
            if adapter is not self:
                ob2 = adapter.publishTraverse(request, name)
            else:
                raise NotFound(ob, name, request)

        return ProxyFactory(ob2)

    def afterTraversal(self, request, ob):
        """Does nothing."""

    def callObject(self, request, ob):
        """Call the object, returning the result."""
        return mapply(ob, request.getPositionalArguments(), request)

    def afterCall(self, request, ob):
        """Does nothing."""

    def handleException(self, object, request, exc_info, retry_allowed=1):
        """Prints the exception."""
        # Reproduce the behavior of ZopePublication by looking up a view
        # for this exception.
        exception = exc_info[1]
        view = queryMultiAdapter((exception, request), name='index.html')
        if view is not None:
            exc_info = None
            request.response.reset()
            request.response.setResult(view())
        else:
            traceback.print_exception(*exc_info)

    def endRequest(self, request, ob):
        """Ends the interaction."""
        endInteraction()


class WebServiceTestPublication(WebServicePublicationMixin, TestPublication):
    """Test publication that mixes in the necessary web service stuff."""


class CookbookWebServiceTestPublication(WebServiceTestPublication):
    def getApplication(self, request):
        return CookbookServiceRootResource()


class WebServiceCaller:
    """A class for making calls to lazr.restful web services."""

    def __init__(self, handle_errors=True, http_caller=None,
                 *args, **kwargs):
        """Create a WebServiceCaller.
        :param handle_errors: Should errors raise exception or be handled by
            the publisher. Default is to let the publisher handle them.

        Other parameters are passed to the HTTPCaller used to make the calls.
        """
        self.handle_errors = handle_errors

        # Set up a delegate to make the actual HTTP calls.
        if http_caller is None:
            http_caller = HTTPCaller(*args, **kwargs)
        self.http_caller = http_caller

    @property
    def base_url(self):
        raise NotImplementedError()

    def apiVersion(self):
        return getUtility(
            IWebServiceConfiguration).service_version_uri_prefix

    def getAbsoluteUrl(self, resource_path, api_version=None):
        """Convenience method for creating a url in tests.

        :param resource_path: This is the url section to be joined to hostname
                              and api version.
        :param api_version: This is the first part of the absolute
                            url after the hostname.
        """
        if api_version is None:
            api_version = self.apiVersion()
        if resource_path.startswith('/'):
            # Prevent os.path.join() from interpreting resource_path as an
            # absolute url. This allows paths that appear consistent with urls
            # from other *.launchpad.dev virtual hosts.
            # For example:
            #   /firefox = http://launchpad.dev/firefox
            #   /firefox = http://api.launchpad.dev/beta/firefox
            resource_path = resource_path[1:]
        url_with_version = os.path.join(api_version, resource_path)
        return urljoin(self.base_url, url_with_version)

    def addHeadersTo(self, url, headers):
        """Add any neccessary headers to the request.

        For instance, this is where a subclass might create an OAuth
        signature for a request.

        :param: The headers that will go into the HTTP request. Modify
        this value in place.
        """

    def __call__(self, path_or_url, method='GET', data=None, headers=None,
                 api_version=None):
        if api_version is None:
            api_version = self.apiVersion()
        path_or_url = str(path_or_url)
        if path_or_url.startswith('http:'):
            full_url = path_or_url
        else:
            full_url = self.getAbsoluteUrl(path_or_url,
                                           api_version=api_version)
        uri = URI(full_url)
        scheme = uri.scheme
        host = uri.host
        port = uri.port
        if port is not None:
            host = host + ':' + str(port)
        path = uri.path
        query = uri.query
        fragment = uri.fragment

        # Make an HTTP request.
        full_headers = {'Host': host}
        if headers is not None:
            full_headers.update(headers)
        self.addHeadersTo(full_url, full_headers)
        header_strings = ["%s: %s" % (header, str(value))
                          for header, value in full_headers.items()]
        path_and_query = path
        if query is not None:
            path_and_query += '?%s' % query
        request_string = "%s %s HTTP/1.1\n%s\n" % (method, path_and_query,
                                                   "\n".join(header_strings))
        if data:
            request_string += "\n" + data

        response = self.http_caller(
            request_string, handle_errors=self.handle_errors)
        return WebServiceResponseWrapper(response)

    def get(self, path, media_type='application/json', headers=None,
            api_version=None):
        """Make a GET request."""
        full_headers = {'Accept': media_type}
        if headers is not None:
            full_headers.update(headers)
        return self(path, 'GET', headers=full_headers,
                    api_version=api_version)

    def head(self, path, headers=None,
             api_version=None):
        """Make a HEAD request."""
        return self(path, 'HEAD', headers=headers, api_version=api_version)

    def delete(self, path, headers=None,
               api_version=None):
        """Make a DELETE request."""
        return self(path, 'DELETE', headers=headers, api_version=api_version)

    def put(self, path, media_type, data, headers=None,
            api_version=None):
        """Make a PUT request."""
        return self._make_request_with_entity_body(
            path, 'PUT', media_type, data, headers, api_version=api_version)

    def post(self, path, media_type, data, headers=None,
             api_version=None):
        """Make a POST request."""
        return self._make_request_with_entity_body(
            path, 'POST', media_type, data, headers, api_version=api_version)

    def _convertArgs(self, operation_name, args):
        """Encode and convert keyword arguments."""
        args['ws.op'] = operation_name
        # To be properly marshalled all values must be strings or converted to
        # JSON.
        for key, value in args.items():
            if not isinstance(value, basestring):
                args[key] = simplejson.dumps(value)
        return urllib.urlencode(args)

    def named_get(self, path_or_url, operation_name, headers=None,
                  api_version=None, **kwargs):
        kwargs['ws.op'] = operation_name
        data = '&'.join(['%s=%s' % (key, self._quote_value(value))
                         for key, value in kwargs.items()])
        return self.get("%s?%s" % (path_or_url, data), data, headers,
                        api_version=api_version)

    def named_post(self, path, operation_name, headers=None,
                   api_version=None, **kwargs):
        data = self._convertArgs(operation_name, kwargs)
        return self.post(path, 'application/x-www-form-urlencoded', data,
                         headers, api_version=api_version)

    def patch(self, path, media_type, data, headers=None,
              api_version=None):
        """Make a PATCH request."""
        return self._make_request_with_entity_body(
            path, 'PATCH', media_type, data, headers, api_version=api_version)

    def _quote_value(self, value):
        """Quote a value for inclusion in a named GET.

        This may mean turning the value into a JSON string.
        """
        if not isinstance(value, basestring):
            value = simplejson.dumps(value)
        return urllib.quote(value)

    def _make_request_with_entity_body(self, path, method, media_type, data,
                                       headers, api_version):
        """A helper method for requests that include an entity-body.

        This means PUT, PATCH, and POST requests.
        """
        real_headers = {'Content-type' : media_type }
        if headers is not None:
            real_headers.update(headers)
        return self(path, method, data, real_headers, api_version=api_version)


class WebServiceResponseWrapper(ProxyBase):
    """A response from the web service with easy access to the JSON body."""

    def jsonBody(self):
        """Return the body of the web service request as a JSON document."""
        try:
            json = simplejson.loads(self.getBody())
            if isinstance(json, list):
                json = sorted(json)
            return json
        except ValueError:
            # Return a useful ValueError that displays the problematic
            # string, instead of one that just says the string wasn't
            # JSON.
            raise ValueError(self.getOutput())


class CookbookWebServiceHTTPCaller(HTTPCaller):

    def chooseRequestClass(self, method, path, environment):
        return WebServiceTestRequest, CookbookWebServiceTestPublication


class CookbookWebServiceCaller(WebServiceCaller):

    base_url = "https://cookbooks.dev/"

    def __init__(self, handle_errors=True):
        super(CookbookWebServiceCaller, self).__init__(
            handle_errors, CookbookWebServiceHTTPCaller())


class CookbookWebServiceAjaxCaller(CookbookWebServiceCaller):
    """A caller that simulates an Ajax client like a web browser."""

    def apiVersion(self):
        """Introduce the Ajax path override to the URI prefix."""
        config = getUtility(IWebServiceConfiguration)
        return (config.path_override
                + '/' + config.service_version_uri_prefix)
