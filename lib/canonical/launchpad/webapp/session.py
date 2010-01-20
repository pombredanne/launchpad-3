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
        # XXX: Maybe this should raise an AttributeError?  Not sure.
        raise AssertionError(
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

    # Re-implement the parent's method so that we can use
    # self.getNamespace(request) instead of self.namespace.
    def getRequestId(self, request):
        """Return the browser id encoded in request as a string

        Return None if an id is not set.

        For example:

          >>> from zope.publisher.http import HTTPRequest
          >>> request = HTTPRequest(StringIO(''), {}, None)
          >>> bim = CookieClientIdManager()

        Because no cookie has been set, we get no id:

          >>> bim.getRequestId(request) is None
          True

        We can set an id:

          >>> id1 = bim.generateUniqueId()
          >>> bim.setRequestId(request, id1)

        And get it back:

          >>> bim.getRequestId(request) == id1
          True

        When we set the request id, we also set a response cookie.  We
        can simulate getting this cookie back in a subsequent request:

          >>> request2 = HTTPRequest(StringIO(''), {}, None)
          >>> request2._cookies = dict(
          ...   [(name, cookie['value'])
          ...    for (name, cookie) in request.response._cookies.items()
          ...   ])

        And we get the same id back from the new request:

          >>> bim.getRequestId(request) == bim.getRequestId(request2)
          True

        Test a corner case where Python 2.6 hmac module does not allow
        unicode as input:

          >>> id_uni = unicode(bim.generateUniqueId())
          >>> bim.setRequestId(request, id_uni)
          >>> bim.getRequestId(request) == id_uni
          True
        
        If another server is managing the ClientId cookies (Apache, Nginx)
        we're returning their value without checking:

          >>> bim.namespace = 'uid'
          >>> bim.thirdparty = True
          >>> request3 = HTTPRequest(StringIO(''), {}, None)
          >>> request3._cookies = {'uid': 'AQAAf0Y4gjgAAAQ3AwMEAg=='}
          >>> bim.getRequestId(request3)
          'AQAAf0Y4gjgAAAQ3AwMEAg=='
        
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

    def setRequestId(self, request, id):
        """Set cookie with id on request.

        Also force the domain key on the cookie to be set to allow our
        session to be shared between virtual hosts where possible, and
        we set the secure key to stop the session key being sent to
        insecure URLs like the Librarian.

        We also log the referrer url on creation of a new
        requestid so we can track where first time users arrive from.

        See the examples in getRequestId.

        Note that the id is checked for validity. Setting an
        invalid value is silently ignored:

            >>> from zope.publisher.http import HTTPRequest
            >>> request = HTTPRequest(StringIO(''), {}, None)
            >>> bim = CookieClientIdManager()
            >>> bim.getRequestId(request)
            >>> bim.setRequestId(request, 'invalid id')
            >>> bim.getRequestId(request)

        For now, the cookie path is the application URL:

            >>> cookie = request.response.getCookie(bim.namespace)
            >>> cookie['path'] == request.getApplicationURL(path_only=True)
            True

        By default, session cookies don't expire:

            >>> cookie.has_key('expires')
            False

        Expiry time of 0 means never (well - close enough)

            >>> bim.cookieLifetime = 0
            >>> request = HTTPRequest(StringIO(''), {}, None)
            >>> bid = bim.getClientId(request)
            >>> cookie = request.response.getCookie(bim.namespace)
            >>> cookie['expires']
            'Tue, 19 Jan 2038 00:00:00 GMT'

        A non-zero value means to expire after than number of seconds:

            >>> bim.cookieLifetime = 3600
            >>> request = HTTPRequest(StringIO(''), {}, None)
            >>> bid = bim.getClientId(request)
            >>> cookie = request.response.getCookie(bim.namespace)
            >>> import rfc822
            >>> expires = time.mktime(rfc822.parsedate(cookie['expires']))
            >>> expires > time.mktime(time.gmtime()) + 55*60
            True

        If another server in front of Zope (Apache, Nginx) is managing the
        cookies we won't set any ClientId cookies:

          >>> request = HTTPRequest(StringIO(''), {}, None)
          >>> bim.thirdparty = True
          >>> bim.setRequestId(request, '1234')
          >>> cookie = request.response.getCookie(bim.namespace)
          >>> cookie

        If the secure attribute is set to a true value, then the
        secure cookie option is included.
        
          >>> bim.thirdparty = False
          >>> bim.cookieLifetime = None
          >>> request = HTTPRequest(StringIO(''), {}, None)
          >>> bim.secure = True
          >>> bim.setRequestId(request, '1234')
          >>> print request.response.getCookie(bim.namespace)
          {'path': '/', 'secure': True, 'value': '1234'}

        If the domain is specified, it will be set as a cookie attribute.

          >>> bim.domain = u'.example.org'
          >>> bim.setRequestId(request, '1234')
          >>> print request.response.getCookie(bim.namespace)
          {'path': '/', 'domain': u'.example.org', 'secure': True, 'value': '1234'}

        When the cookie is set, cache headers are added to the
        response to try to prevent the cookie header from being cached:

          >>> request.response.getHeader('Cache-Control')
          'no-cache="Set-Cookie,Set-Cookie2"'
          >>> request.response.getHeader('Pragma')
          'no-cache'
          >>> request.response.getHeader('Expires')
          'Mon, 26 Jul 1997 05:00:00 GMT'
        """
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

        if self.secure:
            options['secure'] = True

        if self.domain:
            options['domain'] = self.domain

        response.setCookie(
            self.getNamespace(request), id,
            path=request.getApplicationURL(path_only=True),
            **options)

        response.setHeader(
            'Cache-Control', 'no-cache="Set-Cookie,Set-Cookie2"')
        response.setHeader('Pragma', 'no-cache')
        response.setHeader('Expires', 'Mon, 26 Jul 1997 05:00:00 GMT')

        # From here on it's our custom code -- everything else in this method
        # is copied from zope.session.http, replacing just self.namespace with
        # self.getNamespace(request).
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
