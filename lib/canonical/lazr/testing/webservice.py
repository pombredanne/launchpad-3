# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Testing helpers for webservice unit tests."""

__metaclass__ = type
__all__ = [
    'FakeRequest',
    'FakeResponse',
    'pprint_entry',
    'WebServiceTestPublication',
    'WebServiceTestRequest',
    'TestPublication',
    ]
import traceback

from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.publisher.browser import BrowserRequest
from zope.publisher.interfaces import IPublication, IPublishTraverse, NotFound
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.publisher.publish import mapply
from zope.security.checker import ProxyFactory
from zope.security.management import endInteraction, newInteraction

from canonical.launchpad.webapp.servers import StepsToGo
from canonical.lazr.interfaces.rest import IWebServiceLayer
from canonical.lazr.rest.publisher import (
    WebServicePublicationMixin, WebServiceRequestTraversal)


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
        traceback.print_exception(*exc_info)
        exc_info = None

    def endRequest(self, request, ob):
        """Ends the interaction."""
        endInteraction()


class WebServiceTestPublication(WebServicePublicationMixin, TestPublication):
    """Test publication that mixes in the necessary web service stuff."""
