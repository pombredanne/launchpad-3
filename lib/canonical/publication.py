# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: e739465e-bd5d-458c-b332-de6a783f21b7

__metaclass__ = type

from zope.interface import implements, Interface
from zope.component import queryView, getDefaultViewName, queryMultiView

from zope.publisher.http import HTTPRequest
from zope.publisher.browser import BrowserRequest

from zope.app.publication.interfaces import IPublicationRequestFactory
from zope.app.publication.http import HTTPPublication
from zope.app.publication.browser import BrowserPublication as BrowserPub
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import IPublishTraverse, NotFound
from zope.publisher.publish import publish

from zope.app.applicationcontrol.applicationcontrol \
     import applicationControllerRoot

from zope.app.location import Location
from zope.app.traversing.interfaces import IContainmentRoot
from zope.security.checker import ProxyFactory, NamesChecker

from zope.app.server.servertype import ServerType
from zope.server.http.commonaccesslogger import CommonAccessLogger
from zope.server.http.publisherhttpserver import PublisherHTTPServer
from zope.interface.common.interfaces import IException
from zope.exceptions.exceptionformatter import format_exception

import sys
import traceback


class IHasSuburls(Interface):
    """Marker interface for an object that supports suburls."""


class ISubURLDispatch(Interface):

    def __call__():
        """Returns the object at this suburl"""


class SubURLTraverser:
    implements(IBrowserPublisher)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        """Search for views, and if no view is found, look for subURLs."""
        view = queryView(self.context, name, request)
        # XXX I should be looking for views for normal publication here.
        # so, views providing ISubURLDispatch and not "normal publication"
        # shouldn't show up.
        if view is None or ISubURLDispatch.providedBy(view):
            if view is None:
                dispatcher = queryMultiView((self.context,), request,
                        providing=ISubURLDispatch, name=name)
                if dispatcher is None:
                    raise NotFound(self.context, name)
            else:
                dispatcher = view
            return dispatcher()
        else:
            return view

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)


class RootObject(Location):
    implements(IContainmentRoot, IHasSuburls)

rootObject = ProxyFactory(RootObject(), NamesChecker("__class__"))


class DebugView:
    """Helper class for views on exceptions for the Debug skin."""

    __used_for__ = IException

    def __init__(self, context, request):

        self.context = context
        self.request = request

        self.error_type, self.error_object, tb = sys.exc_info()
        try:
            self.traceback_lines = traceback.format_tb(tb)
            self.htmltext = '\n'.join(
                format_exception(self.error_type, self.error_object,
                                 tb, as_html=True)
                )
        finally:
            del tb


class BrowserPublication(BrowserPub):
    """Subclass of z.a.publication.BrowserPublication that removes ZODB.

    This subclass undoes the ZODB-specific things in ZopePublication, a
    superclass of z.a.publication.BrowserPublication.
    """

    def __init__(self, db=None):
        # note, no ZODB
        pass

    def getApplication(self, request):
        # If the first name is '++etc++process', then we should
        # get it rather than look in the database!
        stack = request.getTraversalStack()

        if '++etc++process' in stack:
            return applicationControllerRoot

        return rootObject

_browser_methods = 'GET', 'POST', 'HEAD'

class HTTPPublicationRequestFactory:
    implements(IPublicationRequestFactory)

    def __init__(self, db):
        self._http = HTTPPublication(db)
        self._brower = BrowserPublication()

    def __call__(self, input_stream, output_steam, env):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        method = env.get('REQUEST_METHOD', 'GET').upper()

        if method in _browser_methods:
            request = BrowserRequest(input_stream, output_steam, env)
            request.setPublication(self._brower)
        else:
            request = HTTPRequest(input_stream, output_steam, env)
            request.setPublication(self._http)

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
            publish(request, handle_errors=False)
        except:
            import sys, pdb
            print "%s:" % sys.exc_info()[0]
            print sys.exc_info()[1]
            pdb.post_mortem(sys.exc_info()[2])
            raise



http = ServerType(PublisherHTTPServer,
                  HTTPPublicationRequestFactory,
                  CommonAccessLogger,
                  8080, True)


pmhttp = ServerType(PMDBHTTPServer,
                    HTTPPublicationRequestFactory,
                    CommonAccessLogger,
                    8081, True)

