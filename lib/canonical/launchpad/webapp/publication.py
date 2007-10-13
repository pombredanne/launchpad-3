# (c) Canonical Ltd. 2004-2006, all rights reserved.

__metaclass__ = type

from zope.publisher.publish import mapply

from new import instancemethod
import thread
import traceback
import urllib

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
    BeforeTraverseEvent, OffsiteFormPostError)
import canonical.launchpad.layers as layers
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.opstats import OpStats
from canonical.launchpad.webapp.uri import URI, InvalidURIError
from canonical.launchpad.webapp.vhosts import allvhosts


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
        """See `zope.app.publication.zopepublication.ZopePublication`.

        We override the method to simply save the authenticated user id
        in the transaction.
        """
        # It is possible that request.principal is None if the principal has
        # not been set yet.
        if request.principal is not None:
            txn.setUser(request.principal.id)

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
        # XXX Steve Alexander 2004-12-14: Move this to SQLOS, in a method
        # that is subscribed to the transaction begin event rather than
        # hacking it into traversal.
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
        self.maybeBlockOffsiteFormPost(request)

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

        non_restricted_url = self.getNonRestrictedURL(request)
        if non_restricted_url is not None:
            location += '?production=%s' % urllib.quote(non_restricted_url)

        request.response.setResult('')
        request.response.redirect(location, temporary_if_possible=True)
        # Quash further traversal.
        request.setTraversalStack([])

    def getNonRestrictedURL(self, request):
        """Returns the non-restricted version of the request URL.

        The intended use is for determining the equivalent URL on the
        production Launchpad instance if a user accidentally ends up
        on a restrict_to_team Launchpad instance.

        If a non-restricted URL can not be determined, None is returned.
        """
        base_host = config.launchpad.vhosts.mainsite.hostname
        production_host = config.launchpad.non_restricted_hostname
        # If we don't have a production hostname, or it is the same as
        # this instance, then we can't provide a nonRestricted URL.
        if production_host is None or base_host == production_host:
            return None

        # Are we under the main site's domain?
        uri = URI(request.getURL())
        if not uri.host.endswith(base_host):
            return None

        # Update the hostname, and complete the URL from the request:
        new_host = uri.host[:-len(base_host)] + production_host
        uri = uri.replace(host=new_host, path=request['PATH_INFO'])
        query_string = request.get('QUERY_STRING')
        if query_string:
            uri = uri.replace(query=query_string)
        return str(uri)

    def maybeBlockOffsiteFormPost(self, request):
        """Check if an attempt was made to post a form from a remote site.

        The OffsiteFormPostError exception is raised if the following
        holds true:
          1. the request method is POST
          2. the HTTP referer header is not empty
          3. the host portion of the referrer is not a registered vhost
        """
        if request.method != 'POST':
            return
        referrer = request.getHeader('referer') # match HTTP spec misspelling
        if not referrer:
            return
        # XXX: jamesh 2007-04-26 bug=98437:
        # The Zope testing infrastructure sets a default (incorrect)
        # referrer value of "localhost" or "localhost:9000" if no
        # referrer is included in the request.  We let it pass through
        # here for the benefits of the tests.  Web browsers send full
        # URLs so this does not open us up to extra XSRF attacks.
        if referrer in ['localhost', 'localhost:9000']:
            return
        # Extract the hostname from the referrer URI
        try:
            hostname = URI(referrer).host
        except InvalidURIError:
            hostname = None
        if hostname not in allvhosts.hostnames:
            raise OffsiteFormPostError(referrer)

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

    def afterCall(self, request, ob):
        """See `zope.publisher.interfaces.IPublication`.

        Our implementation aborts() the transaction on read-only requests.
        Because of this we cannot chain to the superclass and implement
        the whole behaviour here.
        """

        # Annotate the transaction with user data. That was done by
        # zope.app.publication.zopepublication.ZopePublication.
        txn = transaction.get()
        self.annotateTransaction(txn, request, ob)

        # Abort the transaction on a read-only request.
        if request.method in ['GET', 'HEAD']:
            txn.abort()
        else:
            txn.commit()

        # Don't render any content for a HEAD.  This was done
        # by zope.app.publication.browser.BrowserPublication
        if request.method == 'HEAD':
            request.response.setResult('')

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
        # Retry the request if we get a database disconnection.
        if retry_allowed and isinstance(exc_info[1], da.DisconnectionError):
            raise Retry(exc_info)
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


