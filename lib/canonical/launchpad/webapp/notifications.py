# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Browser notification messages

Provides an API for displaying arbitrary  notifications to users after
an action has been performed, independant of what page the user
ends up on after the action is done.

Note that the current implementation is deliberately broken - the only way
to do this correctly is by passing a token in the URL to identify the
browser window the request came from.
"""

__metaclass__ = type

import cgi, urllib
from urlparse import urlunsplit
from datetime import datetime, timedelta

from zope.interface import implements
from zope.app.session.interfaces import ISession
import zope.i18n
from zope.publisher.interfaces.browser import IBrowserRequest

from canonical.config import config
from canonical.uuid import generate_uuid
from canonical.launchpad.webapp.interfaces import (
        INotificationRequest, INotificationResponse, BrowserNotificationLevel,
        INotification, INotificationList, IStructuredString
        )
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.url import urlsplit

SESSION_KEY = 'launchpad'

class NotificationRequest:
    """NotificationRequest extracts notifications to display to the user
    from the request and session

    It is designed to be mixed in with an IBrowserRequest

    By default, there are no notifications

    >>> request = NotificationRequest()
    >>> len(request.notifications)
    0
    >>> INotificationRequest.providedBy(request)
    True

    >>> request = NotificationRequest()
    >>> session = ISession(request)[SESSION_KEY]
    >>> notifications = NotificationList()
    >>> session['notifications'] = notifications
    >>> notifications.append(Notification(0, 'Fnord'))
    >>> [notification.message for notification in request.notifications]
    ['Fnord']

    Note that NotificationRequest.notifications also returns any notifications
    that have been added so far in this request, making it the single source
    you need to interogate to display notifications to the user.

    >>> response = INotificationResponse(request)
    >>> response.addNotification('Aargh')
    >>> [notification.message for notification in request.notifications]
    ['Fnord', 'Aargh']
    """
    implements(INotificationRequest)

    @property
    def notifications(self):
        return INotificationResponse(self).notifications


class NotificationResponse:
    """The NotificationResponse collects notifications to propogate to the
    next page loaded. Notifications are stored in the session, with a key
    propogated via the URL to load the correct messages in the next loaded
    page.

    It needs to be mixed in with an IHTTPApplicationResponse so its redirect
    method intercepts the default behavior.

    >>> class MyNotificationResponse(NotificationResponse, MockResponse):
    ...     pass
    >>> response = MyNotificationResponse()
    >>> INotificationResponse.providedBy(response)
    True
    >>> request = NotificationRequest()
    >>> request.response = response
    >>> response._request = request

    >>> len(response.notifications)
    0

    >>> response.addNotification("something")
    >>> len(response.notifications)
    1

    >>> response.removeAllNotifications()
    >>> len(response.notifications)
    0

    >>> response.addNotification("<b>%(escaped)s</b>", escaped="<Fnord>")

    >>> response.addNotification("Whatever", BrowserNotificationLevel.DEBUG)
    >>> response.addNotification("%(percentage)0.2f%%", percentage=99.0)
    >>> response.addNotification("%(num)d thingies", num=10)
    >>> response.addDebugNotification('Debug')
    >>> response.addInfoNotification('Info')
    >>> response.addNoticeNotification('Notice')
    >>> response.addWarningNotification('Warning')

    And an odd one to test Bug #54987

    >>> from canonical.launchpad import _
    >>> response.addErrorNotification(_('Error${value}', mapping={'value':''}))

    >>> INotificationList.providedBy(response.notifications)
    True

    >>> for notification in response.notifications:
    ...     print "%d -- %s" % (notification.level, notification.message)
    25 -- <b>&lt;Fnord&gt;</b>
    10 -- Whatever
    25 -- 99.00%
    25 -- 10 thingies
    10 -- Debug
    20 -- Info
    25 -- Notice
    30 -- Warning
    40 -- Error

    >>> response.redirect("http://example.com?foo=bar")
    302: http://example.com?foo=bar

    Once redirect has been called, any notifications that have been set
    are stored in the session

    >>> for notification in ISession(request)[SESSION_KEY]['notifications']:
    ...     print "%d -- %s" % (notification.level, notification.message)
    ...     break
    25 -- <b>&lt;Fnord&gt;</b>

    If there are no notifications, the session is not touched. This ensures
    that we don't needlessly burden the session storage.

    >>> response = MyNotificationResponse()
    >>> request = NotificationRequest()
    >>> request.response = response
    >>> response._request = request

    >>> session = ISession(request)[SESSION_KEY]
    >>> del ISession(request)[SESSION_KEY]['notifications']
    >>> session.has_key('notifications')
    False
    >>> len(response.notifications)
    0
    >>> response.redirect("http://example.com")
    302: http://example.com
    >>> session.has_key('notifications')
    False
    """
    implements(INotificationResponse)

    # We stuff our Notifications here until we are sure we should persist it
    # in the request. This avoids needless calls to the session machinery
    # which would be bad.
    _notifications = None

    def addNotification(self, msg, level=BrowserNotificationLevel.NOTICE):
        """See `INotificationResponse`.

	XXX FIX ME XXX
	Add a docstring describing the IStructuredString and
	i18n.Message parts of the API.

	"""
        # It is possible that the message is wrapped in an
        # internationalized object, so we need to translate it
        # first. See bug #54987.
        if isinstance(msg, (zope.i18n.Message, zope.i18n.MessageID)):
            msg = zope.i18n.translate(msg, context=self._request)

	if IStructuredString.providedBy(msg):
	    escaped_msg = msg.escapedtext
	else:
	    escaped_msg = cgi.escape(unicode(msg))

        self.notifications.append(Notification(level, escaped_msg))

    @property
    def notifications(self):
        # If we have already retrieved our INotificationList this request,
        # just return it
        if self._notifications is not None:
            return self._notifications
        # XXX: SteveAlexander 2007-04-01:
        #      If there is no session currently then there can be no
        #      notifications.  However, ISession(self)[SESSION_KEY] creates
        #      a session whether one is needed or not.
        #      Options are to refactor the session code so that it makes a
        #      session only when necessary, or to check for the presence of
        #      the session cookie at call-sites like this one.
        #      A get_session() helper would help here.
        #      Maybe a get_or_create_session() to go with it.
        cookie_name = config.launchpad.session.cookie
        request = self._request
        response = self
        # Do some getattr sniffing so that the doctests in this module
        # still pass.  Doing this rather than improving the Mock classes
        # that the mixins are used with, as we'll be moving this hack to
        # the sesions machinery in due course.
        if (not (getattr(request, 'cookies', None) and
                 getattr(response, 'getCookie', None))
            or
            (request.cookies.get(cookie_name) is not None or
             response.getCookie(cookie_name) is not None)):
            session = ISession(self)[SESSION_KEY]
            try:
                # Use notifications stored in the session.
                self._notifications = session['notifications']
                # Remove them from the session so they don't propogate to
                # subsequent pages, unless redirect() is called which will
                # push the notifications back into the session.
                del session['notifications']
            except KeyError:
                # No stored notifications - create a new NotificationList
                self._notifications = NotificationList()
        else:
            self._notifications = NotificationList()

        return self._notifications

    def removeAllNotifications(self):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        self._notifications = None

    def redirect(self, location, status=None):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        # We are redirecting, so we need to stuff our notifications into
        # the session
        if self._notifications is not None and len(self._notifications) > 0:
            session = ISession(self)[SESSION_KEY]
            session['notifications'] = self._notifications
        return super(NotificationResponse, self).redirect(location, status)

    def addDebugNotification(self, msg, **kw):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        self.addNotification(msg, BrowserNotificationLevel.DEBUG, **kw)

    def addInfoNotification(self, msg, **kw):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        self.addNotification(msg, BrowserNotificationLevel.INFO, **kw)

    def addNoticeNotification(self, msg, **kw):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        self.addNotification(msg, BrowserNotificationLevel.NOTICE, **kw)

    def addWarningNotification(self, msg, **kw):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        self.addNotification(msg, BrowserNotificationLevel.WARNING, **kw)

    def addErrorNotification(self, msg, **kw):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse"""
        self.addNotification(msg, BrowserNotificationLevel.ERROR, **kw)


class NotificationList(list):
    """
    Collection of INotification instances with a creation date

    >>> notifications = NotificationList()
    >>> notifications.created <= datetime.utcnow()
    True
    >>> notifications[0]
    Traceback (most recent call last):
    ...
    IndexError: list index out of range

    >>> debug = BrowserNotificationLevel.DEBUG
    >>> error = BrowserNotificationLevel.ERROR
    >>> notifications.append(Notification(error, u'An error'))
    >>> notifications.append(Notification(debug, u'A debug message'))
    >>> for notification in notifications:
    ...     print repr(notification.message)
    u'An error'
    u'A debug message'

    The __getitem__ method is also overloaded to allow TALES expressions
    to easily retrieve lists of notifications that match a particular
    notification level.

    >>> for notification in notifications['debug']:
    ...     print repr(notification.message)
    u'A debug message'
    """
    implements(INotificationList)

    created = None

    def __init__(self):
        self.created = datetime.utcnow()
        super(NotificationList, self).__init__()

    def __getitem__(self, index_or_levelname):
        if isinstance(index_or_levelname, int):
            return super(NotificationList, self).__getitem__(index_or_levelname)

        level = getattr(
                BrowserNotificationLevel, index_or_levelname.upper(), None
                )
        if level is None:
            raise KeyError(index_or_levelname)

        return [
            notification for notification in self
                if notification.level == level
            ]


class Notification:
    implements(INotification)

    level = None
    message = None

    def __init__(self, level, message):
        self.level = level
        self.message = message


class NotificationTestView1(LaunchpadView):
    """Display some notifications.

    This is installed into the real instance, rather than added on the fly
    in the test suite, as this page is useful for adjusting the visual style
    of the notifications
    """
    def initialize(self):
        response = self.request.response

        # Add some notifications
        for count in range(1, 3):
            response.addDebugNotification(
                    'Debug notification <b>%(count)d</b>', count=count
                    )
            response.addInfoNotification(
                    'Info notification <b>%(count)d</b>', count=count
                    )
            response.addNoticeNotification(
                    'Notice notification <b>%(count)d</b>', count=count
                    )
            response.addWarningNotification(
                    'Warning notification <b>%(count)d</b>', count=count
                    )
            response.addErrorNotification(
                    'Error notification <b>%(count)d</b>', count=count
                    )


class NotificationTestView2(NotificationTestView1):
    """Redirect to another page, propogating some notification messages.

    This is installed into the real instance, rather than added on the fly
    in the test suite, as this page is useful for adjusting the visual style
    of the notifications
    """
    def initialize(self):
        NotificationTestView1.initialize(self)
        self.request.response.redirect('/')


class NotificationTestView3(NotificationTestView1):
    """Redirect, propagating some notification messages, to another page
    that adds more notifications before rendering.

    This is installed into the real instance, rather than added on the fly
    in the test suite, as this page is useful for adjusting the visual style
    of the notifications
    """
    def initialize(self):
        self.request.response.addErrorNotification(
                    '+notificationtest3 error'
                    )
        self.request.response.redirect('/+notificationtest1')


class NotificationTestView4(NotificationTestView1):
    """Redirect twice, propagating some notification messages each time,
    ending up at another page that adds more notifications before rendering.

    This is installed into the real instance, rather than added on the fly
    in the test suite, as this page is useful for adjusting the visual style
    of the notifications
    """
    def initialize(self):
        self.request.response.addErrorNotification(
                    '+notificationtest4 error'
                    )
        self.request.response.redirect('/+notificationtest3')
