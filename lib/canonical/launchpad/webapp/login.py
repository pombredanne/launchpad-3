# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Stuff to do with logging in and logging out."""

__metaclass__ = type

from datetime import datetime
from zope.component import getUtility
from zope.app.session.interfaces import ISession
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from zope.event import notify
from canonical.launchpad.webapp.interfaces import CookieAuthLoggedInEvent
from canonical.launchpad.webapp.interfaces import LoggedOutEvent


class BasicLoginPage:

    def isSameHost(self, url):
        """Returns True if the url appears to be from the same host as we are.
        """
        return url.startswith(self.request.getApplicationURL())

    def login(self):
        referer = self.request.getHeader('referer')  # Traditional w3c speling
        if referer and self.isSameHost(referer):
            self.request.response.redirect(referer)
        else:
            self.request.response.redirect(self.request.getURL(1))
        return ''


class CookieLoginPage:

    was_logged_in = False
    errortext = None

    def process_form(self):
        """Process the form data.

        If there is an error, returns a string containing a description
        of the error for presentation to the user.
        """
        email = self.request.form.get('email')
        password = self.request.form.get('password')
        submitted = self.request.form.get('SUBMIT')
        if not submitted:
            return ''
        if not email or not password:
            errortext = "Enter your email address and password."
            return ''
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        if principal is not None and principal.validate(password):
            self._logInPerson(principal, email)
            self.was_logged_in = True
        else:
            errortext = "The email address and password do not match."
        return ''

    def _logInPerson(self, principal, email):
        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        previous_login = authdata.get('personid')
        authdata['personid'] = principal.id
        authdata['logintime'] = datetime.utcnow()
        authdata['login'] = email
        notify(CookieAuthLoggedInEvent(self.request, email))


class CookieLogoutPage:

    def logout(self):
        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        previous_login = authdata.get('personid')
        authdata['personid'] = None
        authdata['logintime'] = datetime.utcnow()
        notify(LoggedOutEvent(self.request))
        return ''
