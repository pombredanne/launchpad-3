# (c) Canonical Ltd. 2004-2005, all rights reserved.

__metaclass__ = type

# python standard library
import sys
import thread
import traceback
from new import instancemethod

# interfaces and components
from zope.interface import implements, providedBy
from zope.component import getUtility, queryView
from zope.event import notify
from zope.app import zapi  # used to get at the adapters service

# zope publication and traversal
import zope.app.publication.browser
from zope.app.publication.zopepublication import Cleanup
from zope.publisher.interfaces.browser import IDefaultSkin
from zope.publisher.interfaces import IPublishTraverse

# zope transactions
import transaction

# zope security
from zope.security.proxy import removeSecurityProxy
from zope.security.interfaces import Unauthorized
from zope.security.management import newInteraction

# launchpad
from canonical.launchpad.interfaces import (
    IOpenLaunchBag, ILaunchpadRoot, AfterTraverseEvent, BeforeTraverseEvent)
import canonical.launchpad.layers as layers
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
import canonical.launchpad.webapp.zodb
import canonical.launchpad.webapp.adapter as da

# sqlos
import sqlos.connection
from sqlos.interfaces import IConnectionName


__all__ = ['LoginRoot', 'LaunchpadBrowserPublication']

class LoginRoot:
    """Object that provides IPublishTraverse to return only itself.

    We anchor the +login view to this object.  This allows other
    special namespaces to be traversed, but doesn't traverse other
    normal names.
    """
    implements(IPublishTraverse)

    def publishTraverse(self, request, name):
        if not request.getTraversalStack():
            root_object = getUtility(ILaunchpadRoot)
            view = queryView(root_object, name, request)
            return view
        else:
            return self


class LaunchpadBrowserPublication(
    zope.app.publication.browser.BrowserPublication):
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
        superclass = zope.app.publication.browser.BrowserPublication
        return superclass.getDefaultTraversal(self, request, ob)

    def getApplication(self, request):
        end_of_traversal_stack = request.getTraversalStack()[:1]
        if end_of_traversal_stack == ['+login']:
            return LoginRoot()
        else:
            bag = getUtility(IOpenLaunchBag)
            assert bag.site is None, 'Argh! Steve was wrong!'
            root_object = getUtility(ILaunchpadRoot)
            bag.add(root_object)
            return root_object

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

        da.set_request_started()

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
        
        # Debugging code. Please leave. -- StuartBishop 20050622
        # Set 'threads 1' in launchpad.conf if you are using this.
        # from canonical.mem import printCounts, mostRefs, memory
        # from datetime import datetime
        # mem = memory()
        # try:
        #     delta = mem - self._debug_mem
        # except AttributeError:
        #     print '= Startup memory %d bytes' % mem
        #     delta = 0
        # self._debug_mem = mem
        # now = datetime.now().strftime('%H:%M:%S')
        # print '== %s (%.1f MB/%+d bytes) %s' % (
        #         now, mem/(1024*1024), delta, str(request.URL))
        # print str(request.URL)
        # printCounts(mostRefs(4))

    def _maybePlacefullyAuthenticate(self, request, ob):
        """ This should never be called because we've excised it in
        favor of dealing with auth in events; if it is called for any
        reason, raise an error """
        raise NotImplementedError

    def handleException(self, object, request, exc_info, retry_allowed=True):
        superclass = zope.app.publication.browser.BrowserPublication
        superclass.handleException(self, object, request, exc_info,
                                   retry_allowed)
        # If it's a HEAD request, we don't care about the body, regardless of
        # exception.
        # UPSTREAM: Should this be part of zope, or is it only required because
        #           of our customisations?
        #        - Andrew Bennetts, 2005-03-08
        if request.method == 'HEAD':
            request.response.setBody('')

    def endRequest(self, request, object):
        da.clear_request_started()
        superclass = zope.app.publication.browser.BrowserPublication
        superclass.endRequest(self, request, object)

