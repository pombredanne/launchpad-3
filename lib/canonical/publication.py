# (c) Canonical Software Ltd. 2004, all rights reserved.
#

__metaclass__ = type


from zope.security.interfaces import Unauthorized
from zope.security.management import newInteraction
import transaction
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
import canonical.launchpad.webapp.zodb

from zope.app import zapi
from zope.publisher.interfaces.browser import IDefaultSkin
from zope.publisher.interfaces import NotFound, IPublishTraverse

from zope.event import notify
from zope.interface import implements, Interface
from zope.interface import providedBy

import canonical.launchpad.layers as layers
from canonical.launchpad.interfaces import ILaunchpadApplication

from zope.component import getUtility
from zope.component import queryView

from zope.publisher.http import HTTPRequest
from zope.publisher.browser import BrowserRequest

from zope.app.publication.interfaces import IPublicationRequestFactory
from zope.app.publication.interfaces import BeforeTraverseEvent
from zope.app.publication.zopepublication import Cleanup
from zope.app.publication.http import HTTPPublication
from zope.app.publication.browser import BrowserPublication as BrowserPub
from zope.publisher.publish import publish

from zope.app.errorservice import globalErrorReportingService
from zope.app.errorservice.interfaces import ILocalErrorReportingService
from zope.app.errorservice import RootErrorReportingService

from zope.app.applicationcontrol.applicationcontrol \
     import applicationControllerRoot

from zope.app.location import Location
from zope.app.traversing.interfaces import IContainmentRoot
from zope.security.checker import ProxyFactory, NamesChecker
from zope.security.proxy import removeSecurityProxy

from zope.app.server.servertype import ServerType
from zope.server.http.commonaccesslogger import CommonAccessLogger
from zope.server.http.publisherhttpserver import PublisherHTTPServer
from zope.interface.common.interfaces import IException
from zope.exceptions.exceptionformatter import format_exception

from canonical.launchpad.interfaces import IOpenLaunchBag

import sqlos.connection
from sqlos.interfaces import IConnectionName

import sys, thread
import traceback
from new import instancemethod



class RootObject(Location):
    implements(IContainmentRoot, ILaunchpadApplication)

    def __init__(self):
        self.title = 'The Open Source Launchpad'



class DebugView:
    """Helper class for views on exceptions for the Debug layer."""

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


class ErrorReportingService(RootErrorReportingService):
    """Error reporting service that copies tracebacks to the log by default.
    """
    copy_to_zlog = True


class LoginRoot:
    """Object that provides IPublishTraverse to return only itself.

    We anchor the +login view to this object.  This allows other
    special namespaces to be traversed, but doesn't traverse other
    normal names.
    """
    implements(IPublishTraverse)

    def publishTraverse(self, request, name):
        if not request.getTraversalStack():
            view = queryView(rootObject, name, request)
            return view
        else:
            return self


class BrowserPublication(BrowserPub):
    """Subclass of z.a.publication.BrowserPublication that removes ZODB.

    This subclass undoes the ZODB-specific things in ZopePublication, a
    superclass of z.a.publication.BrowserPublication.
    """

    def __init__(self, db):
        self.db = db

    def annotateTransaction(self, txn, request, ob):
        """Set some useful meta-information on the transaction. This
        information is used by the undo framework, for example.

        This method is not part of the `IPublication` interface, since
        it's specific to this particular implementation.
        """

        # It is possible that request.principal is None if the principal has
        # not been set yet.

        if request.principal is not None:
            txn.setUser(request.principal.id)

        # Work around methods that are usually used for views
        bare = removeSecurityProxy(ob)
        if isinstance(bare, instancemethod):
            ob = bare.im_self

        return txn

    def getDefaultTraversal(self, request, ob):
        return BrowserPub.getDefaultTraversal(self, request, ob)

    def getApplication(self, request):
        # If the first name is '++etc++process', then we should
        # get it rather than look in the database!
        stack = request.getTraversalStack()

        if '++etc++process' in stack:
            return applicationControllerRoot

        end_of_traversal_stack = request.getTraversalStack()[:1]
        if end_of_traversal_stack == ['+login']:
            return LoginRoot()
        else:
            bag = getUtility(IOpenLaunchBag)
            assert bag.site is None, 'Argh! Steve was wrong!'
            bag.add(rootObject)
            return rootObject

    # the below ovverrides to zopepublication (callTraversalHooks,
    # afterTraversal, and _maybePlacefullyAuthenticate) make the
    # assumption that there will never be a ZODB "local"
    # authentication service (such as the "pluggable auth service").
    # If this becomes untrue at some point, the code will need to be
    # revisited.

    def clearSQLOSCache(self):
        # Big boot for fixing SQLOS transaction issues - nuke the
        # connection cache at the start of a transaction. This shouldn't
        # affect performance much, as psycopg does connection pooling.
        #
        # XXX: Move this to SQLOS, in a method that is subscribed to the
        # transaction begin event rather than hacking it into traversal.
        # -- Steve Alexander, Tue Dec 14 13:15:06 UTC 2004
        name = getUtility(IConnectionName).name
        key = (thread.get_ident(), name)
        cache = sqlos.connection.connCache
        if cache.has_key(key):
            del cache[key]
        # SQLOS Connection objects also only register themselves for
        # the transaction in which they are instantiated - this is
        # no longer a problem as we are nuking the connection cache,
        # but it is still an issue in SQLOS that needs to be fixed.
        #name = getUtility(IConnectionName).name
        #con = sqlos.connection.getConnection(None, name)
        #t = transaction.get_transaction()
        #t.join(con._dm)

    def beforeTraversal(self, request):
        newInteraction(request)
        transaction.begin()

        # Open the ZODB.
        conn = self.db.open('')
        cleanup = Cleanup(conn.close)
        request.hold(cleanup)  # Close the connection on request.close()

        self.openedConnection(conn)

        root = conn.root()
        canonical.launchpad.webapp.zodb.handle_before_traversal(root)

        self.clearSQLOSCache()
        getUtility(IOpenLaunchBag).clear()

        # Set the default layer.
        adapters = zapi.getService(zapi.servicenames.Adapters)
        layer = adapters.lookup((providedBy(request),), IDefaultSkin, '')
        if layer is not None:
            layers.setAdditionalLayer(request, layer)

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

    def handleException(self, object, request, exc_info, retry_allowed=True,
                        counter=[0]):
        # XXX: Debugging code.  Please leave.  SteveAlexander 2005-03-23
        #counter[0] += 1
        #import traceback, sys
        #f = open('/tmp/traceback.txt', 'a')
        #print >>f, '----------------------------------------'
        #print >>f, 'Count:', counter[0]
        #print >>f, 'Request: %r' % request
        #print >>f
        #etype, value, tb = sys.exc_info()
        #traceback.print_exception(etype, value, tb, file=f)
        #f.close()
        BrowserPub.handleException(self, object, request, exc_info,
                                   retry_allowed)
        # If it's a HEAD request, we don't care about the body, regardless of
        # exception.
        # UPSTREAM: Should this be part of zope, or is it only required because
        #           of our customisations?
        #        - Andrew Bennetts, 2005-03-08
        if request.method == 'HEAD':
            request.response.setBody('')


_browser_methods = 'GET', 'POST', 'HEAD'

class HTTPPublicationRequestFactory:
    implements(IPublicationRequestFactory)

    def __init__(self, db):
        ## self._http = HTTPPublication(db)
        self._browser = BrowserPublication(db)

    def __call__(self, input_stream, output_steam, env):
        """See zope.app.publication.interfaces.IPublicationRequestFactory"""
        method = env.get('REQUEST_METHOD', 'GET').upper()

        if method in _browser_methods:
            request = BrowserRequest(input_stream, output_steam, env)
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
        layers.setFirstLayer(request, layers.DebugLayer)
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

debughttp = ServerType(PublisherHTTPServer,
                       DebugLayerRequestFactory,
                       CommonAccessLogger,
                       8082, True)

globalErrorService = ErrorReportingService()
globalErrorUtility = ProxyFactory(
    removeSecurityProxy(globalErrorService),
    NamesChecker(ILocalErrorReportingService.names())
    )

rootObject = ProxyFactory(RootObject(), NamesChecker(["__class__"]))

