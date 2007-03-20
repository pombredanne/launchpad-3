# (c) Canonical Ltd. 2004-2006, all rights reserved.

__metaclass__ = type

from zope.publisher.publish import mapply

from new import instancemethod
import thread
import traceback

import sqlos.connection
from sqlos.interfaces import IConnectionName

import transaction

from zope.app import zapi  # used to get at the adapters service
import zope.app.publication.browser
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.component import getUtility, queryView
from zope.event import notify
from zope.interface import implements, providedBy

from zope.publisher.interfaces import IPublishTraverse, Retry
from zope.publisher.interfaces.browser import IDefaultSkin, IBrowserRequest

from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy
from zope.security.management import newInteraction

from canonical.config import config
from canonical.launchpad.webapp.interfaces import (
    IOpenLaunchBag, ILaunchpadRoot, AfterTraverseEvent,
    BeforeTraverseEvent)
import canonical.launchpad.layers as layers
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.opstats import OpStats


__all__ = [
    'LoginRoot',
    'LaunchpadBrowserPublication'
    ]


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

    root_object_interface = ILaunchpadRoot

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
            root_object = getUtility(self.root_object_interface)
            bag.add(root_object)
            return root_object

    # the below ovverrides to zopepublication (callTraversalHooks,
    # afterTraversal, and _maybePlacefullyAuthenticate) make the
    # assumption that there will never be a ZODB "local"
    # authentication service (such as the "pluggable auth service").
    # If this becomes untrue at some point, the code will need to be
    # revisited.

    @staticmethod
    def clearSQLOSCache():
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
        threadid = thread.get_ident()
        threadrequestfile = open('thread-%s.request' % threadid, 'w')
        try:
            request_txt = unicode(request).encode('UTF-8')
        except:
            request_txt = 'Exception converting request to string\n\n'
            try:
                request_txt += traceback.format_exc()
            except:
                request_txt += 'Unable to render traceback!'
        threadrequestfile.write(request_txt)
        threadrequestfile.close()

        # Tell our custom database adapter that the request has started.
        da.set_request_started()

        newInteraction(request)
        transaction.begin()

        self.clearSQLOSCache()
        getUtility(IOpenLaunchBag).clear()

        # Set the default layer.
        adapters = zapi.getGlobalSiteManager().adapters
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
        self.maybeRestrictToTeam(request)

    def maybeRestrictToTeam(self, request):

        from canonical.launchpad.interfaces import (
            IPersonSet, IPerson, ITeam, ILaunchpadCelebrities)
        restrict_to_team = config.launchpad.restrict_to_team
        if not restrict_to_team:
            return

        restrictedlogin = '+restricted-login'
        restrictedinfo = '+restricted-info'

        # Always allow access to +restrictedlogin and +restrictedinfo.
        traversal_stack = request.getTraversalStack()
        if (traversal_stack == [restrictedlogin] or
            traversal_stack == [restrictedinfo]):
            return

        principal = request.principal
        team = getUtility(IPersonSet).getByName(restrict_to_team)
        if team is None:
            raise AssertionError(
                'restrict_to_team "%s" not found' % restrict_to_team)
        elif not ITeam.providedBy(team):
            raise AssertionError(
                'restrict_to_team "%s" is not a team' % restrict_to_team)

        if IUnauthenticatedPrincipal.providedBy(principal):
            location = '/%s' % restrictedlogin
        else:
            # We have a team we can work with.
            user = IPerson(principal)
            if (user.inTeam(team) or
                user.inTeam(getUtility(ILaunchpadCelebrities).admin)):
                return
            else:
                location = '/%s' % restrictedinfo

        request.response.setResult('')
        request.response.redirect(location, temporary_if_possible=True)
        # Quash further traversal.
        request.setTraversalStack([])

    def callObject(self, request, ob):

        # Don't render any content on a redirect.
        if request.response.getStatus() in [301, 302, 303, 307]:
            return ''

        # Set the launchpad user-id and page-id (if available) in the
        # wsgi environment, so that the request logger can access it.
        request.setInWSGIEnvironment('launchpad.userid', request.principal.id)
        usedfor = getattr(removeSecurityProxy(ob), '__used_for__', None)
        if usedfor is not None:
            name = getattr(removeSecurityProxy(ob), '__name__', '')
            pageid = '%s:%s' % (usedfor.__name__, name)
            request.setInWSGIEnvironment('launchpad.pageid', pageid)

        return mapply(ob, request.getPositionalArguments(), request)

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
        # Reraise Retry exceptions rather than log.
        # TODO: Remove this when the standard handleException method
        # we call does this (bug to be fixed upstream) -- StuartBishop 20060317
        if retry_allowed and isinstance(exc_info[1], Retry):
            raise
        superclass = zope.app.publication.browser.BrowserPublication
        superclass.handleException(self, object, request, exc_info,
                                   retry_allowed)
        # If it's a HEAD request, we don't care about the body, regardless of
        # exception.
        # UPSTREAM: Should this be part of zope, or is it only required because
        #           of our customisations?
        #        - Andrew Bennetts, 2005-03-08
        if request.method == 'HEAD':
            request.response.setResult('')

    def endRequest(self, request, object):
        superclass = zope.app.publication.browser.BrowserPublication
        superclass.endRequest(self, request, object)
        da.clear_request_started()

        # Maintain operational statistics.
        OpStats.stats['requests'] += 1

        # Increment counters for HTTP status codes we track individually
        # NB. We use IBrowserRequest, as other request types such as
        # IXMLRPCRequest use IHTTPRequest as a superclass.
        # This should be fine as Launchpad only deals with browser
        # and XML-RPC requests.
        if IBrowserRequest.providedBy(request):
            OpStats.stats['http requests'] += 1
            status = request.response.getStatus()
            if status == 404: # Not Found
                OpStats.stats['404s'] += 1
            elif status == 500: # Unhandled exceptions
                OpStats.stats['500s'] += 1
            elif status == 503: # Timeouts
                OpStats.stats['503s'] += 1

            # Increment counters for status code groups.
            OpStats.stats[str(status)[0] + 'XXs'] += 1


