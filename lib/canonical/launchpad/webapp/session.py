# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support for browser-cookie sessions."""

__metaclass__ = type

import hmac
import logging
import time
from email.utils import formatdate
from hashlib import sha1

from cookielib import domain_match
from zope.component import getUtility
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.session.http import CookieClientIdManager, digestEncode

from storm.zope.interfaces import IZStorm

from canonical.config import config
from canonical.launchpad.layers import TestOpenIDLayer
from canonical.launchpad.webapp.url import urlparse


SECONDS = 1
MINUTES = 60 * SECONDS
HOURS = 60 * MINUTES
DAYS = 24 * HOURS
YEARS = 365 * DAYS
logger = logging.getLogger()


def get_cookie_domain(request_domain):
    """Return a string suitable for use as the domain parameter of a cookie.

    The returned domain value should allow the cookie to be seen by
    all virtual hosts of the Launchpad instance.  If no matching
    domain is known, None is returned.
    """
    cookie_domains = [v.strip()
                      for v in config.launchpad.cookie_domains.split(',')]
    for domain in cookie_domains:
        assert not domain.startswith('.'), \
               "domain should not start with '.'"
        dotted_domain = '.' + domain
        if (domain_match(request_domain, domain)
            or domain_match(request_domain, dotted_domain)):
            return dotted_domain
    return None

ANNOTATION_KEY = 'canonical.launchpad.webapp.session.sid'

class LaunchpadCookieClientIdManager(CookieClientIdManager):

    def __init__(self):
        # Don't upcall to the parent here as it will only set self.namespace
        # and self.secret, which we don't want as we need to use
        # getNamespace(request) and we have a @property for secret.

        # Set the cookie life time to something big.
        # It should be larger than our session expiry time.
        self.cookieLifetime = 1 * YEARS
        self._secret = None

    @property
    def namespace(self):
        raise AttributeError(
            "This class doesn't provide a namespace attribute because it "
            "needs a request to figure out the correct namespace. Use "
            "getNamespace(request) instead.")

    def getNamespace(self, request):
        """Return the correct namespace according to the given request.

        This is needed so that we can use a separate cookie for the testopenid
        vhost.
        """
        if TestOpenIDLayer.providedBy(request):
            return config.launchpad_session.testopenid_cookie
        else:
            return config.launchpad_session.cookie

    def getClientId(self, request):
        sid = self.getRequestId(request)
        if sid is None:
            # XXX gary 21-Oct-2008 bug 285803
            # Our session data container (see pgsession.py in the same
            # directory) explicitly calls setRequestId the first time a
            # __setitem__ is called. Therefore, we only generate one here,
            # and do not set it. This keeps the session id out of anonymous
            # sessions.  Unfortunately, it is also Rube-Goldbergian: we should
            # consider switching to our own session/cookie machinery that
            # suits us better.
            sid = request.annotations.get(ANNOTATION_KEY)
            if sid is None:
                sid = self.generateUniqueId()
                request.annotations[ANNOTATION_KEY] = sid
        return sid

    @property
    def secret(self):
        # Because our CookieClientIdManager is not persistent, we need to
        # pull the secret from some other data store - failing to do this
        # would mean a new secret is generated every time the server is
        # restarted, invalidating all old session information.
        # Secret is looked up here rather than in __init__, because
        # we can't be sure the database connections are setup at that point.
        if self._secret is None:
            store = getUtility(IZStorm).get('session', 'launchpad-session:')
            result = store.execute("SELECT secret FROM secret")
            self._secret = result.get_one()[0]
        return self._secret

    # XXX: salgado, 2010-02-11, bug=520582: Re-implement the parent's method
    # so that we can use self.getNamespace(request) instead of self.namespace.
    # This method can be removed (just like the block between the dashed lines
    # below) as soon as we ditch canonical-identity-provider.
    def getRequestId(self, request):
        """Return the browser id encoded in request as a string

        Return None if an id is not set.
        """
        cookie_name = self.getNamespace(request)
        response_cookie = request.response.getCookie(cookie_name)
        if response_cookie:
            sid = response_cookie['value']
        else:
            request = IHTTPApplicationRequest(request)
            sid = request.getCookies().get(cookie_name, None)
        if self.thirdparty:
            return sid
        else:
            # If there is an id set on the response, use that but
            # don't trust it.  We need to check the response in case
            # there has already been a new session created during the
            # course of this request.
            if sid is None or len(sid) != 54:
                return None
            s, mac = sid[:27], sid[27:]
            
            # call s.encode() to workaround a bug where the hmac
            # module only accepts str() types in Python 2.6
            if (digestEncode(hmac.new(
                    s.encode(), self.secret, digestmod=sha1
                ).digest()) != mac):
                return None
            else:
                return sid

    def setRequestId(self, request, id):
        """Set cookie with id on request.

        Also force the domain key on the cookie to be set to allow our
        session to be shared between virtual hosts where possible, and
        we set the secure key to stop the session key being sent to
        insecure URLs like the Librarian.

        We also log the referrer url on creation of a new
        requestid so we can track where first time users arrive from.
        """

        # XXX: salgado, 2010-02-11, bug=520582: Everything enclosed between
        # the dashed lines has been cut-n-pasted from the parent class so that
        # we can use .getNamespace(request) instead of .namespace.  We need
        # that in order to have separate cookies between *.launchpad.net and
        # login.launchpad.net.  This code can be removed once we stop using
        # canonical-identity-provider to run login.launchpad.net.
        # -------------------------------------------------------------------
        # TODO: Currently, the path is the ApplicationURL. This is reasonable,
        #     and will be adequate for most purposes.
        #     A better path to use would be that of the folder that contains
        #     the site manager this service is registered within. However,
        #     that would be expensive to look up on each request, and would
        #     have to be altered to take virtual hosting into account.
        #     Seeing as this utility instance has a unique namespace for its
        #     cookie, using ApplicationURL shouldn't be a problem.

        if self.thirdparty:
            logger.warning(
                'ClientIdManager is using thirdparty cookies, ignoring '
                'setRequestId call')
            return

        response = request.response
        options = {}
        if self.cookieLifetime is not None:
            if self.cookieLifetime:
                expires = formatdate(time.time() + self.cookieLifetime,
                                     localtime=False, usegmt=True)
            else:
                expires = 'Tue, 19 Jan 2038 00:00:00 GMT'

            options['expires'] = expires

        response.setCookie(
            self.getNamespace(request), id,
            path=request.getApplicationURL(path_only=True),
            **options)

        response.setHeader(
            'Cache-Control', 'no-cache="Set-Cookie,Set-Cookie2"')
        response.setHeader('Pragma', 'no-cache')
        response.setHeader('Expires', 'Mon, 26 Jul 1997 05:00:00 GMT')
        # -------------------------------------------------------------------
        # End of the code cut-n-pasted from zope.

        cookie = request.response.getCookie(self.getNamespace(request))
        protocol, request_domain = urlparse(request.getURL())[:2]

        # Set secure flag on cookie.
        if protocol != 'http':
            cookie['secure'] = True
        else:
            cookie['secure'] = False

        # Set domain attribute on cookie if vhosting requires it.
        cookie_domain = get_cookie_domain(request_domain)
        if cookie_domain is not None:
            cookie['domain'] = cookie_domain


idmanager = LaunchpadCookieClientIdManager()
