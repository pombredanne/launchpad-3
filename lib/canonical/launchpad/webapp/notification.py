# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Browser notification messages

Provides an API for displaying arbitrary  notifications to users after
an action has been performed, independant of what page the user
ends up on after the action is done.
"""

__metaclass__ = type

import cgi, urllib
from urlparse import urlsplit, urlunsplit
from datetime import datetime, timedelta

from zope.interface import implements
from zope.app.session.interfaces import ISession
from zope.publisher.interfaces.browser import IBrowserRequest

from canonical.uuid import generate_uuid
from canonical.launchpad.webapp.interfaces import (
        INotificationRequest, INotificationResponse, BrowserNotificationLevel,
        INotification, INotificationList
        )
from canonical.launchpad.webapp.publisher import LaunchpadView

NOTIFICATION_PARAMETER = 'lpnotification'
SESSION_KEY = 'launchpad.notifications'

class NotificationRequest:
    """NotificationRequest extracts notifications to display to the user
    from the request and session

    It is designed to be mixed in with an IBrowserRequest

    By default, there are no notifications

    >>> request = NotificationRequest()
    >>> len(request.notifications)
    0

    If we stuff some notifications in the session, the NotificationRequest
    will provide access to them if the relevant information was passed in
    via the URL.

    >>> request = NotificationRequest()
    >>> IBrowserRequest(request).form[NOTIFICATION_PARAMETER] = 'UUID'
    >>> session = ISession(request)[SESSION_KEY]
    >>> notifications = NotificationList()
    >>> session['UUID'] = notifications
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
    def uuid(self):
        form = IBrowserRequest(self).form
        uuid = form.get(NOTIFICATION_PARAMETER, None)
        if uuid is None:
            uuid = generate_uuid()
            form[NOTIFICATION_PARAMETER] = uuid
        return uuid

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
    >>> request = NotificationRequest()
    >>> IBrowserRequest(request).form[NOTIFICATION_PARAMETER] = 'UUID'
    >>> request.response = response
    >>> response._request = request

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
    >>> response.addErrorNotification('Error')

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

    >>> response.redirect("http://example.com")
    302: http://example.com?lpnotification=UUID
    >>> response.redirect("http://example.com?foo=bar")
    302: http://example.com?foo=bar&lpnotification=UUID

    Once redirect has been called, any notifications that have been set
    are stored in the session

    >>> for notification in ISession(request)[SESSION_KEY]['UUID']:
    ...     print "%d -- %s" % (notification.level, notification.message)
    ...     break
    25 -- <b>&lt;Fnord&gt;</b>

    If there are no notifications, the session is not touched. This ensures
    that we don't needlessly burden the session storage.

    >>> response = MyNotificationResponse()
    >>> request = NotificationRequest()
    >>> IBrowserRequest(request).form[NOTIFICATION_PARAMETER] = 'UUID2'
    >>> request.response = response
    >>> response._request = request
    >>> len(response.notifications)
    0
    >>> response.redirect("http://example.com")
    302: http://example.com
    >>> ISession(request)[SESSION_KEY].has_key('UUID2')
    False
    """
    implements(INotificationResponse)

    # We stuff our Notifications here until we are sure we shold persist it
    # in the request. This avoids needless calls to the session machinery
    # which would be bad.
    _notifications = None

    def addNotification(self, msg, level=BrowserNotificationLevel.NOTICE, **kw):
        """See canonical.launchpad.webapp.interfaces.INotificationResponse."""
        if kw:
            quoted_args = {}
            for key, value in kw.items():
                if isinstance(value, (int, float)):
                    quoted_args[key] = value
                else:
                    quoted_args[key] = cgi.escape(unicode(value))
            msg = msg % quoted_args

        self.notifications.append(Notification(level, msg))

    @property
    def uuid(self):
        return INotificationRequest(self._request).uuid

    @property
    def notifications(self):
        # If we have already retrieved our INotificationList this request,
        # just return it
        if self._notifications is not None:
            return self._notifications

        # Clean out old notifications
        session = ISession(self)[SESSION_KEY]
        for key, notification in list(session.items()):
            if notification.created > datetime.utcnow() + timedelta(hours=1):
                try:
                    del session[key]
                except KeyError:
                    # Ignore, as there is possible race condition
                    # when two pages are loaded simultaneously
                    pass

        # If we have a uuid passed in via the URL, then attempt to
        # extract the INotificationList from the session
        uuid = self.uuid
        if uuid is not None:
            try:
                self._notifications = session[uuid]
                return self._notifications
            except KeyError:
                pass

        # Otherwise, create a new INotificationList
        self._notifications = NotificationList()
        return self._notifications

    def redirect(self, location, status=None):
        """See canonical.launchpad.webapp.interfaces.ISessionNotifications"""
        (scheme, location, path, query, fragment) = urlsplit(location)

        # We are redirecting, so we need to stuff our notifications into
        # the session
        if self._notifications is not None and len(self._notifications) > 0:
            session = ISession(self)[SESSION_KEY]
            uuid = self.uuid
            session[uuid] = self._notifications
            query = querystring_inject(query, NOTIFICATION_PARAMETER, uuid)

        location = urlunsplit((scheme, location, path, query, fragment))
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


def querystring_inject(querystring, key, value):
    """Inject extra items into a query string, returning it.
    
    >>> querystring_inject('', 'key', 'value')
    'key=value'
    >>> querystring_inject('foo=bar', 'key', 'value')
    'foo=bar&key=value'

    This method overwrites existing items with the same key

    >>> querystring_inject('key=oldvalue&foo=bar&foo=bar', 'key', 'newvalue')
    'foo=bar&foo=bar&key=newvalue'

    If value is None, that key is removed form the query string if it is
    there.

    >>> querystring_inject('', 'key', None)
    ''
    >>> querystring_inject('key=value', 'key', None)
    ''
    >>> querystring_inject('key=value&key=value', 'key', None)
    ''
    >>> querystring_inject('foo=bar&key=value', 'key', None)
    'foo=bar'
    """
    query = cgi.parse_qsl(querystring, True)
    query = [item for item in query if item[0] != key]
    if value is not None:
        query.append((key, value))
    return urllib.urlencode(query)
    

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
