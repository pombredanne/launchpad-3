# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: e739465e-bd5d-458c-b332-de6a783f21b7

__metaclass__ = type


from zope.security.interfaces import Unauthorized
from zope.security.management import newInteraction
from transaction import get_transaction
from canonical.lp.placelessauth.interfaces import IPlacelessAuthUtility

from zope.event import notify
from zope.interface import implements, Interface
from zope.component import queryView, getDefaultViewName, queryMultiView
from zope.component import getUtility

from zope.publisher.http import HTTPRequest
from zope.publisher.browser import BrowserRequest

from zope.app.publication.interfaces import IPublicationRequestFactory
from zope.app.publication.interfaces import BeforeTraverseEvent
from zope.app.publication.http import HTTPPublication
from zope.app.publication.browser import BrowserPublication as BrowserPub
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound
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

import sqlos.connection
from sqlos.interfaces import IConnectionName

import sys, thread
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

class IAfterTraverseEvent(Interface):
    """An event which gets sent after publication traverse; this
    should really be pushed into Zope proper """

class AfterTraverseEvent(object):
    """An event which gets sent after publication traverse"""
    implements(IAfterTraverseEvent)
    def __init__(self, ob, request):
        self.object = ob
        self.request = request

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

    # the below ovverrides to zopepublication (callTraversalHooks,
    # afterTraversal, and _maybePlacefullyAuthenticate) make the
    # assumption that there will never be a ZODB "local"
    # authentication service (such as the "pluggable auth service").
    # If this becomes untrue at some point, the code will need to be
    # revisited.

    def beforeTraversal(self, request):
        newInteraction(request)
        get_transaction().begin()
        # Big boot for fixing SQLOS transaction issues - nuke the
        # connection cache at the start of a transaction. This shouldn't
        # affect performance much, as psycopg does connection pooling.
        #
        # XXX: Move this to SQLOS, in a method that is subscribed to the
        # transaction begin event rather than hacking it into traversal.
        name = getUtility(IConnectionName).name
        key = (thread.get_ident(), name)
        cache = sqlos.connection.connCache
        if cache.has_key(key):
            del cache[key]
        # SQLOS Connection objects also only register themselves for
        # the transaction in which they are instantiated - this is
        # no longer a problem as we are nuking the connection cache,
        # but it is still an issue in SQLOS that needs to be fixed.
        name = getUtility(IConnectionName).name
        con = sqlos.connection.getConnection(None, name)
        t = transaction.get_transaction()
        t.join(con._dm)

        # Try to authenticate against our registry
        prin_reg = getUtility(IPlacelessAuthUtility)
        p = prin_reg.authenticate(request)
        if p is None:
            p = prin_reg.unauthenticatedPrincipal()
            if p is None:
                raise Unauthorized # If there's no default principal

        request.setPrincipal(p)

    def callTraversalHooks(self, request, ob):
        """ We don't want to call _maybePlacefullyAuthenticate as does
        zopepublication """
        notify(BeforeTraverseEvent(ob, request))

    def afterTraversal(self, request, ob):
        """ We don't want to call _maybePlacefullyAuthenticate as does
        zopepublication but we do want to send an AfterTraverseEvent """
        notify(AfterTraverseEvent(ob, request))

    def _maybePlacefullyAuthenticate(self, request, ob):
        """ This should never be called because we've excised it in
        favor of dealing with auth in events; if it is called for any
        reason, raise an error """
        raise NotImplementedError

_browser_methods = 'GET', 'POST', 'HEAD'

class HTTPPublicationRequestFactory:
    implements(IPublicationRequestFactory)

    def __init__(self, db):
        self._http = HTTPPublication(db)
        self._browser = BrowserPublication()

    def __call__(self, input_stream, output_steam, env):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        method = env.get('REQUEST_METHOD', 'GET').upper()

        if method in _browser_methods:
            request = BrowserRequest(input_stream, output_steam, env)
            request.setPublication(self._browser)
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

