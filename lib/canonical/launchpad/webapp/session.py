# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Support for browser-cookie sessions."""

__metaclass__ = type

from cookielib import domain_match
from zope.component import getUtility
from zope.app.session.http import CookieClientIdManager
from zope.app.rdb.interfaces import IZopeDatabaseAdapter

from canonical.config import config
from canonical.launchpad.webapp.url import urlparse

SECONDS = 1
MINUTES = 60 * SECONDS
HOURS = 60 * MINUTES
DAYS = 24 * HOURS
YEARS = 365 * DAYS

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
            da = getUtility(IZopeDatabaseAdapter, 'session')
            cursor = da().cursor()
            cursor.execute("SELECT secret FROM secret")
            self._secret = cursor.fetchone()[0]
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

        We now also log the referrer url on creation of a new
        requestid so we can track where first time users arrive from.
        """
        if request.getCookies().has_key(self.namespace):
            new_session = False
        elif request.response.getCookie(self.namespace, None) is not None:
            new_session = False
        else:
            new_session = True

        CookieClientIdManager.setRequestId(self, request, id)

        cookie = request.response.getCookie(self.namespace)
        protocol, request_domain = urlparse(request.getURL())[:2]

        # Set secure flag on cookie.
        if protocol != 'http':
            cookie['secure'] = True
        else:
            cookie['secure'] = False

        # Set domain attribute on cookie if vhosting requires it.
        for domain in config.launchpad.cookie_domains:
            assert not domain.startswith('.'), \
                    "domain should not start with '.'"
            dotted_domain = '.' + domain
            if (domain_match(request_domain, domain)
                    or domain_match(request_domain, dotted_domain)):
                cookie['domain'] = dotted_domain
                break

        if new_session:
            session = ISession(request)['launchpad']
            session['initial_referrer'] = request['HTTP_REFERER']

idmanager = LaunchpadCookieClientIdManager()
