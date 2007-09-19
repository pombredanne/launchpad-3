# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Support for browser-cookie sessions."""

__metaclass__ = type

from cookielib import domain_match
from zope.component import getUtility
from zope.app.session.interfaces import ISession
from zope.app.session.http import CookieClientIdManager

from storm.zope.interfaces import IZStorm

from canonical.config import config
from canonical.launchpad.webapp.url import urlparse

SECONDS = 1
MINUTES = 60 * SECONDS
HOURS = 60 * MINUTES
DAYS = 24 * HOURS
YEARS = 365 * DAYS


def get_cookie_domain(request_domain):
    """Return a string suitable for use as the domain parameter of a cookie.

    The returned domain value should allow the cookie to be seen by
    all virtual hosts of the Launchpad instance.  If no matching
    domain is known, None is returned.
    """
    for domain in config.launchpad.cookie_domains:
        assert not domain.startswith('.'), \
               "domain should not start with '.'"
        dotted_domain = '.' + domain
        if (domain_match(request_domain, domain)
            or domain_match(request_domain, dotted_domain)):
            return dotted_domain
    return None


class LaunchpadCookieClientIdManager(CookieClientIdManager):

    def __init__(self):
        CookieClientIdManager.__init__(self)
        self.namespace = config.launchpad.session.cookie
        # Set the cookie life time to something big.
        # It should be larger than our session expiry time.
        self.cookieLifetime = 1 * YEARS
        self._secret = None

    def _get_secret(self):
        # Because our CookieClientIdManager is not persistent, we need to
        # pull the secret from some other data store - failing to do this
        # would mean a new secret is generated every time the server is
        # restarted, invalidating all old session information.
        # Secret is looked up here rather than in __init__, because
        # we can't be sure the database connections are setup at that point.
        if self._secret is None:
            store = getUtility(IZStorm).get('session')
            result = store.execute("SELECT secret FROM secret")
            self._secret = result.get_one()[0]
        return self._secret

    def _set_secret(self, value):
        # Silently ignored so CookieClientIdManager's __init__ method
        # doesn't die
        pass

    secret = property(_get_secret, _set_secret)

    def setRequestId(self, request, id):
        """As per CookieClientIdManager.setRequestID, except
        we force the domain key on the cookie to be set to allow our
        session to be shared between virtual hosts where possible, and
        we set the secure key to stop the session key being sent to
        insecure URLs like the Librarian.

        We also log the referrer url on creation of a new
        requestid so we can track where first time users arrive from.
        """
        if request.getCookies().has_key(self.namespace):
            # Session has already been set in a previous request
            new_session = False
        elif request.response.getCookie(self.namespace, None) is not None:
            # Session has already been set for the first time in this request
            new_session = False
        else:
            # Session has never been set
            new_session = True

        # XXX: SteveAlexander, 2007-04-01.
        #      This is on the codepath where anon users get a session cookie
        #      set unnecessarily.
        CookieClientIdManager.setRequestId(self, request, id)

        cookie = request.response.getCookie(self.namespace)
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

        if new_session:
            session = ISession(request)['launchpad.session']
            referrer = request.get('HTTP_REFERER', None)
            if referrer is not None:
                referrer = referrer.decode('US-ASCII', 'replace')
            session['initial_referrer'] = referrer
            url = str(request.URL).decode('US-ASCII', 'replace')
            if request.get('QUERY_STRING', None):
                url = url + '?' + request['QUERY_STRING']
            session['initial_url'] = url

idmanager = LaunchpadCookieClientIdManager()
