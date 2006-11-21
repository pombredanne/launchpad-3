# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import logging

from zope.interface import Interface, Attribute, implements
from zope.app.security.interfaces import IAuthenticationService, IPrincipal
from zope.app.pluggableauth.interfaces import IPrincipalSource
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from zope.schema import Int, Text, Object, Datetime, TextLine

from canonical.launchpad import _


class IPrincipalIdentifiedEvent(Interface):
    """An event that is sent after a principal has been recovered from the
    request's credentials.
    """
    principal = Attribute('The principal')
    request = Attribute('The request')
    login = Attribute(
        'The login id that was used.  For example, an email address.')


class ILoggedInEvent(Interface):
    """An event that is sent after someone has logged in.

    Exactly what this means will vary according to the type of login,
    primarily as to whether it is per-request or session-based.
    """
    request = Attribute('The request')
    login = Attribute(
        'The login id that was used.  For example, an email address.')


class CookieAuthLoggedInEvent:
    implements(ILoggedInEvent)
    def __init__(self, request, login):
        self.request = request
        self.login = login


class CookieAuthPrincipalIdentifiedEvent:
    implements(IPrincipalIdentifiedEvent)
    def __init__(self, principal, request, login):
        self.principal = principal
        self.request = request
        self.login = login


class BasicAuthLoggedInEvent:
    implements(ILoggedInEvent, IPrincipalIdentifiedEvent)
    def __init__(self, request, login, principal):
        # these one from ILoggedInEvent
        self.login = login
        # this one from IPrincipalIdentifiedEvent
        self.principal = principal
        # this one from ILoggedInEvent and IPrincipalIdentifiedEvent
        self.request = request


class ILoggedOutEvent(Interface):
    """An event which gets sent after someone has logged out via a form."""


class LoggedOutEvent:
    implements(ILoggedOutEvent)
    def __init__(self, request):
        self.request = request


class IPlacelessAuthUtility(IAuthenticationService):
    """This is a marker interface for a utility that supplies the interface
    of the authentication service placelessly, with the addition of
    a method to allow the acquisition of a principal using his
    login name.
    """

    def getPrincipalByLogin(login):
        """Return a principal based on his login name."""


class IPlacelessLoginSource(IPrincipalSource):
    """This is a principal source that has no place.  It extends
    the pluggable auth IPrincipalSource interface, allowing for disparity
    between the user id and login name.
    """

    def getPrincipalByLogin(login):
        """Return a principal based on his login name."""

    def getPrincipals(name):
        """Not implemented.

        Get principals with matching names.
        See zope.app.pluggableauth.interfaces.IPrincipalSource
        """


class ILaunchpadPrincipal(IPrincipal):
    """Marker interface for launchpad principals.

    This is used for the launchpad.AnyPerson permission.
    """


class ILaunchpadDatabaseAdapter(IZopeDatabaseAdapter):
    """The Launchpad customized database adapter"""
    def readonly():
        """Set the connection to read only.
        
        This should only be called at the start of the transaction to
        avoid confusing code that defers making database changes until
        transaction commit time.
        """

    def switchUser(self, dbuser=None):
        """Change the PostgreSQL user we are connected as, defaulting to the
        default Launchpad user.
       
        This involves closing the existing connection and reopening it;
        uncommitted changes will be lost. The new connection will also open
        in read/write mode so calls to readonly() will need to be made
        after switchUser.
        """

#
# Browser notifications
#

class BrowserNotificationLevel:
    """Matches the standard logging levels, with the addition of notice
    (which we should probably add to our log levels as well)
    """
    # XXX Matthew Paul Thomas 2006-03-22: NOTICE and INFO should be merged.
    # https://launchpad.net/bugs/36287
    DEBUG = logging.DEBUG     # A debugging message
    INFO = logging.INFO       # simple confirmation of a change
    NOTICE = logging.INFO + 5 # action had effects you might not have intended
    WARNING = logging.WARNING # action will not be successful unless you ...
    ERROR = logging.ERROR     # the previous action did not succeed, and why

    ALL_LEVELS = (DEBUG, INFO, NOTICE, WARNING, ERROR)


class INotification(Interface):
    level = Int(title=_('Level of notification'), required=True)
    message = Text(title=_('Message as an XHTML snippet'), required=True)


class INotificationList(Interface):

    created = Datetime(title=_('Time this notification was created'))

    def append(notification):
        """Add an INotification to the list of notifications"""

    def __getitem__(index_or_levelname):
        """Retrieve an INotification by index, or a list of INotification
        instances by level name (DEBUG, NOTICE, INFO, WARNING, ERROR).
        """

    def __iter__():
        """Iterate over list of INotification"""


class INotificationRequest(Interface):

    notifications = Object(
        description=u"""
            Notifications received from previous request as well as any
            notifications added in the current request
            """,
        schema=INotificationList
        )


class INotificationResponse(Interface):
    """This class is responsible for propogating any notifications that
    have been set when redirect() is called.
    """

    def addNotification(msg, level=BrowserNotificationLevel.NOTICE, **kw):
        """Append the given message to the list of notifications

        msg may be an XHTML fragment suitable for inclusion in a block
        tag such as <div>. It may also contain standard Python string
        replacement markers to be filled out by the keyword arguments
        (ie. %(foo)s). The keyword arguments inserted this way are
        automatically HTML quoted.

        level is one of the BrowserNotificationLevels: DEBUG, INFO, NOTICE,
        WARNING, ERROR.
        """

    def removeAllNotifications():
        """Remove all notifications.

        This will be used when rendering an error page.
        """

    notifications = Object(
            description=u"Notifications generated by current request",
            schema=INotificationList
            )

    def addDebugNotification(msg, **kw):
        """Shortcut to addNotification(msg, DEBUG, **kw)"""

    def addInfoNotification(msg, **kw):
        """Shortcut to addNotification(msg, INFO, **kw)"""

    def addNoticeNotification(msg, **kw):
        """Shortcut to addNotification(msg, NOTICE, **kw)"""

    def addWarningNotification(msg, **kw):
        """Shortcut to addNotification(msg, WARNING, **kw)"""

    def addErrorNotification(msg, **kw):
        """Shortcut to addNotification(msg, ERROR, **kw)"""

    def redirect(location, status=None):
        """As per IHTTPApplicationResponse.redirect, except notifications
        are preserved.
        """

 
class IErrorReport(Interface):
    id = TextLine(description=u"the name of this error report")
    type = TextLine(description=u"the type of the exception that occurred")
    value = TextLine(description=u"the value of the exception that occurred")
    time = Datetime(description=u"the time at which the exception occurred")
    tb_text = Text(description=u"a text version of the traceback")
    username = TextLine(description=u"the user associated with the request")
    url = TextLine(description=u"the URL for the failed request")
    req_vars = Attribute('the request variables')


class IErrorReportRequest(Interface):
    oopsid = TextLine(
        description=u"""an identifier for the exception, or None if no 
        exception has occurred""")

#
# Batch Navigation
#

class IBatchNavigator(Interface):
    """A batch navigator for a specified set of results."""

    batch = Attribute("The IBatch for which navigation links are provided.")

    def prevBatchURL():
        """Return a URL to the previous chunk of results."""

    def nextBatchURL():
        """Return a URL to the next chunk of results."""

    def batchPageURLs():
        """Return a list of links representing URLs to pages of
        results."""


class ITableBatchNavigator(IBatchNavigator):
    """A batch navigator for tabular listings."""

    # This attribute reads well in ZPT, e.g.:
    #
    # <tal:foo condition="batch_nav/show_column/foo">
    show_column = Attribute(
        "A dict keyed by column name. If the value is True, that column will "
        "be shown in the list, otherwise it won't.")


# LaunchpadFormView widget layout

class IAlwaysSubmittedWidget(Interface):
    """A widget that is always submitted (such as a checkbox or radio
    button group).  It doesn't make sense to show a 'Required' or
    'Optional' marker for such widgets.
    """

class ISingleLineWidgetLayout(Interface):
    """A widget that is displayed in a single table row next to its label."""

class IMultiLineWidgetLayout(Interface):
    """A widget that is displayed on its own table row below its label."""

class ICheckBoxWidgetLayout(IAlwaysSubmittedWidget):
    """A widget that is displayed like a check box with label to the right."""
