# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type

import logging

import zope.app.publication.interfaces
from zope.interface import Interface, Attribute, implements
from zope.app.security.interfaces import IAuthenticationUtility, IPrincipal
from zope.app.pluggableauth.interfaces import IPrincipalSource
from zope.rdb.interfaces import IZopeDatabaseAdapter
from zope.traversing.interfaces import IContainmentRoot
from zope.schema import Bool, Choice, Datetime, Int, Object, Text, TextLine

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem, use_template


class TranslationUnavailable(Exception):
    """Translation objects are unavailable."""


class NotFoundError(KeyError):
    """Launchpad object not found."""


class UnexpectedFormData(AssertionError):
    """Got form data that is not what is expected by a form handler."""


class POSTToNonCanonicalURL(UnexpectedFormData):
    """Got a POST to an incorrect URL.

    One example would be a URL containing uppercase letters.
    """


class ILaunchpadRoot(IContainmentRoot):
    """Marker interface for the root object of Launchpad."""


class ILaunchpadApplication(Interface):
    """Marker interface for a launchpad application.

    Rosetta, Malone and Soyuz are launchpad applications.  Their root
    application objects will provide an interface that extends this
    interface.
    """
    title = Attribute('Title')


class ILaunchpadProtocolError(Interface):
    """Marker interface for a Launchpad protocol error exception."""


class IAuthorization(Interface):
    """Authorization policy for a particular object and permission."""

    def checkUnauthenticated():
        """Returns True if an unauthenticated user has that permission
        on the adapted object.  Otherwise returns False.
        """

    def checkAuthenticated(user):
        """Returns True if the user has that permission on the adapted
        object.  Otherwise returns False.

        The argument `user` is the person who is authenticated.
        """


class OffsiteFormPostError(Exception):
    """An attempt was made to post a form from a remote site."""


class UnsafeFormGetSubmissionError(Exception):
    """An attempt was made to submit an unsafe form action with GET."""


#
# Menus and Facets
#

class IMenu(Interface):
    """Public interface for facets, menus, extra facets and extra menus."""

    def iterlinks(requesturl=None):
        """Iterate over the links in this menu.

        requesturl, if it is not None, is a Url object that is used to
        decide whether a menu link points to the page being requested,
        in which case it will not be linked.
        """


class IMenuBase(IMenu):
    """Common interface for facets, menus, extra facets and extra menus."""

    context = Attribute('The object that has this menu.')

    request = Attribute('The request the menus is used in.')


class IFacetMenu(IMenuBase):
    """Main facet menu for an object."""

    def iterlinks(requesturl=None, selectedfacetname=None):
        """Iterate over the links in this menu.

        requesturl, if it is not None, is a Url object that is used to
        decide whether a menu link points to the page being requested,
        in which case it will not be linked.

        If selectedfacetname is provided, the link with that name will be
        marked as 'selected'.
        """

    defaultlink = Attribute(
        "The name of the default link in this menu.  That is, the one that "
        "will be selected if no others are selected.  It is None if there "
        "is no default link.")


class IApplicationMenu(IMenuBase):
    """Application menu for an object."""


class IContextMenu(IMenuBase):
    """Context menu for an object."""


class ILinkData(Interface):
    """An object with immutable attributes that represents the data a
    programmer provides about a link in a menu.
    """

    target = Attribute("The place this link should link to.  This may be "
        "a path relative to the context of the menu this link appears in, "
        "or an absolute path, or an absolute URL.")

    text = Attribute(
        "The text of this link, as appears underlined on a page.")

    summary = Attribute(
        "The summary text of this link, as appears as a tooltip on the link.")

    icon = Attribute("The name of the icon to use.")

    enabled = Attribute("Boolean to say whether this link is enabled.")

    site = Attribute(
        "The name of the site this link is to, or None for the current site.")

    # CarlosPerelloMarin 20080131 bugs=187837: This should be removed once
    # action menu is not used anymore and we move to use inline navigation.
    sort_key = Attribute(
        "The sort key to use when rendering it with a group of links.")


class ILink(ILinkData):
    """An object that represents a link in a menu.

    The attributes name, url and linked may be set by the menus infrastructure.
    """

    name = Attribute("The name of this link in Python data structures.")

    url = Attribute(
        "The full url this link points to.  Set by the menus infrastructure. "
        "None before it is set.")

    linked = Attribute(
        "A boolean value saying whether this link should appear as a "
        "clickable link in the UI.  The general rule is that a link to "
        "the current page should not be shown linked.  Defaults to True.")

    enabled = Attribute(
        "Boolean to say whether this link is enabled.  Can be read and set.")

    escapedtext = Attribute("Text string, escaped as necessary.")

    icon_url = Attribute(
        "The full URL for this link's associated icon, if it has one.")

    def render():
        """Return a HTML representation of the link."""


class IFacetLink(ILink):
    """A link in a facet menu.

    It has a 'selected' attribute that is set by the menus infrastructure,
    and indicates whether the link is the selected facet.
    """

    selected = Attribute(
        "A boolean value saying whether this link is the selected facet menu "
        "item.  Defaults to False.")


class IStructuredString(Interface):
    """An object that represents a string that is to retain its html structure
    in a menu's link text.
    """

    escapedtext = Attribute("The escaped text for display on a web page.")


class IBreadcrumb(Interface):
    """A breadcrumb link.  IBreadcrumbs get put into request.breadcrumbs."""

    url = Attribute('Absolute url of this breadcrumb.')

    text = Attribute('Text of this breadcrumb.')

    has_menu = Attribute('Whether this breadcrumb has a drop-down menu.')


#
# Canonical URLs
#

class ICanonicalUrlData(Interface):
    """Tells you how to work out a canonical url for an object."""

    rootsite = Attribute(
        'The root id to use.  None means to use the base of the current '
        'request.')

    inside = Attribute('The object this path is relative to.  None for root.')

    path = Attribute('The path relative to "inside", not starting with a /.')


class NoCanonicalUrl(TypeError):
    """There was no canonical URL registered for an object.

    Arguments are:
      - The object for which a URL was sought
      - The object that did not have ICanonicalUrlData
    """
    def __init__(self, object_url_requested_for, broken_link_in_chain):
        TypeError.__init__(self, 'No url for %r because %r broke the chain.' %
            (object_url_requested_for, broken_link_in_chain)
            )

#
# DBSchema
#


# XXX kiko 2007-02-08: this is currently unused. We need somebody to come
# in and set up interfaces for the enums.
class IDBSchema(Interface):
    """A DBSchema enumeration."""

    name = Attribute("Lower-cased-spaces-inserted class name of this schema.")

    title = Attribute("Title of this schema.")

    description = Attribute("Description of this schema.")

    items = Attribute("A mapping of [name or value] -> dbschema item.")


class IDBSchemaItem(Interface):
    """An Item in a DBSchema enumeration."""

    value = Attribute("Integer value of this enum item.")

    name = Attribute("Symbolic name of this item.")

    title = Attribute("Title text of this item.")

    description = Attribute("Description text of this item.")

    def __sqlrepr__(dbname):
        """Return an SQL representation of this item.

        The dbname attribute is required as part of the sqlobject
        interface, but it not used in this case.
        """

    def __eq__(other):
        """An item is equal if it is from the same DBSchema and has the same
        value.
        """

    def __ne__(other):
        """not __eq__"""

    def __hash__():
        """Returns a hash value."""

# XXX kiko 2007-02-08: this needs reconsideration if we are to make it a
# truly generic thing. The problem lies in the fact that half of this (user,
# login, timezone, developer) is actually useful inside webapp/, and the other
# half is very Launchpad-specific. I suggest we split the interface and
# implementation into two parts, having a different name for the webapp/
# bits.
class ILaunchBag(Interface):
    site = Attribute('The application object, or None')
    person = Attribute('IPerson, or None')
    project = Attribute('IProject, or None')
    product = Attribute('IProduct, or None')
    distribution = Attribute('IDistribution, or None')
    distroseries = Attribute('IDistroSeries, or None')
    distroarchseries = Attribute('IDistroArchSeries, or None')
    sourcepackage = Attribute('ISourcepackage, or None')
    sourcepackagereleasepublishing = Attribute(
        'ISourcepackageReleasePublishing, or None')
    bug = Attribute('IBug, or None')
    bugtask = Attribute('IBugTask, or None')

    user = Attribute('Currently authenticated IPerson, or None')
    login = Attribute('The login used by the authenticated person, or None')

    timezone = Attribute("The user's time zone")

    developer = Bool(
        title=u'True if a member of the launchpad developers celebrity'
        )


class IOpenLaunchBag(ILaunchBag):
    def add(ob):
        '''Stick the object into the correct attribute of the ILaunchBag,
        or ignored, or whatever'''
    def clear():
        '''Empty the bag'''
    def setLogin(login):
        '''Set the login to the given value.'''
    def setDeveloper():
        '''Set the developer flag.

        Because we use this during exception handling, we need this set
        and cached at the start of the transaction in case our database
        connection blows up.
        '''

#
# Request
#

class IBasicLaunchpadRequest(Interface):
    stepstogo = Attribute(
        'The StepsToGo object for this request, allowing you to inspect and'
        ' alter the remaining traversal steps.')

    breadcrumbs = Attribute(
        'List of IBreadcrumb objects.  This is appended to during traversal'
        ' so that a page can render appropriate breadcrumbs.')

    traversed_objects = Attribute(
        'List of traversed objects.  This is appended to during traversal.')

    def getNearest(*some_interfaces):
        """Searches for the last traversed object to implement one of
        the given interfaces.

        Returns an (object, matching_interface) tuple.  If the object
        implements more than one of the interfaces, the first one is
        returned.

        If no matching object is found, the tuple (None, None) is returned.
        """


class IBrowserFormNG(Interface):
    """Interface to manipulate submitted form data."""

    def __contains__(name):
        """Return True if a field named name was submitted."""

    def __iter__():
        """Return an iterator over the submitted field names."""

    def getOne(name, default=None):
        """Return the value of the field name.

        If the field wasn't submitted return the default value.
        If more than one value was submitted, raises UnexpectedFormData.
        """

    def getAll(name, default=None):
        """Return the the list of values submitted under field name.

        If the field wasn't submitted return the default value. (If default
        is None, an empty list will be returned. It is an error to use
        something else than None or a list as default value.

        This method should always return a list, if only one value was
        submitted, it will be returned in a list.
        """


class ILaunchpadBrowserApplicationRequest(
    IBasicLaunchpadRequest,
    zope.publisher.interfaces.browser.IBrowserApplicationRequest):
    """The request interface to the application for LP browser requests."""

    form_ng = Object(
        title=u'IBrowserFormNG object containing the submitted form data',
        schema=IBrowserFormNG)


# XXX SteveAlexander 2005-09-14: These need making into a launchpad version
#     rather than the zope versions for the publisher simplification work.
# class IEndRequestEvent(Interface):
#     """An event which gets sent when the publication is ended"""
#
# # called in zopepublication's endRequest method, after ending
# # the interaction.  it is used only by local sites, to clean
# # up per-thread state.
# class EndRequestEvent(object):
#     """An event which gets sent when the publication is ended"""
#     implements(IEndRequestEvent)
#     def __init__(self, ob, request):
#         self.object = ob
#         self.request = request


#
#
#

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


class IPlacelessAuthUtility(IAuthenticationUtility):
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


# We have to define this here because importing from launchpad.interfaces
# would create circular dependencies.
class OAuthPermission(DBEnumeratedType):
    """The permission granted by the user to the OAuth consumer."""

    UNAUTHORIZED = DBItem(10, """
        No Access

        The application will not be allowed to access Launchpad on your
        behalf.
        """)

    READ_PUBLIC = DBItem(20, """
        Read Non-Private Data

        The application will be able to access Launchpad on your behalf
        but only for reading non-private data.
        """)

    WRITE_PUBLIC = DBItem(30, """
        Change Non-Private Data

        The application will be able to access Launchpad on your behalf
        for reading and changing non-private data.
        """)

    READ_PRIVATE = DBItem(40, """
        Read Anything

        The application will be able to access Launchpad on your behalf
        for reading anything, including private data.
        """)

    WRITE_PRIVATE = DBItem(50, """
        Change Anything

        The application will be able to access Launchpad on your behalf
        for reading and changing anything, including private data.
        """)


class AccessLevel(DBEnumeratedType):
    """The level of access any given principal has."""
    use_template(OAuthPermission, exclude='UNAUTHORIZED')


class ILaunchpadPrincipal(IPrincipal):
    """Marker interface for launchpad principals.

    This is used for the launchpad.AnyPerson permission.
    """

    access_level = Choice(
        title=_("The level of access this principal has."),
        vocabulary=AccessLevel, default=AccessLevel.WRITE_PRIVATE)


class ILaunchpadDatabaseAdapter(IZopeDatabaseAdapter):
    """The Launchpad customized database adapter"""
    def readonly():
        """Set the connection to read only.

        This should only be called at the start of the transaction to
        avoid confusing code that defers making database changes until
        transaction commit time.
        """

    def switchUser(self, dbuser=None):
        """Change the PostgreSQL user we are connected as.

        This involves closing the existing connection and reopening it;
        uncommitted changes will be lost. The new connection will also open
        in read/write mode so calls to readonly() will need to be made
        after switchUser.
        """

    def getUser(self):
        """Return the current PostgreSQL user we are connected as.

        The default user comes from config.launchpad.dbuser.
        """

#
# Browser notifications
#

class BrowserNotificationLevel:
    """Matches the standard logging levels, with the addition of notice
    (which we should probably add to our log levels as well)
    """
    # XXX Matthew Paul Thomas 2006-03-22 bugs=36287:
    # NOTICE and INFO should be merged.
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

    def addNotification(msg, level=BrowserNotificationLevel.NOTICE):
        """Append the given message to the list of notifications.

        A plain string message will be CGI escaped.  Passing a message
        that provides the `IStructuredString` interface will return a
        unicode string that has been properly escaped.  Passing an
        instance of a Zope internationalized message will cause the
        message to be translated, then CGI escaped.

        :param msg: This may be a string, `zope.i18n.Message`,
        	`zope.confirmation.fields.MessageID`, or an instance of
        	`IStructuredString`.

        :param level: One of the `BrowserNotificationLevel` values: DEBUG,
        	INFO, NOTICE, WARNING, ERROR.
        """

    def removeAllNotifications():
        """Remove all notifications.

        This will be used when rendering an error page.
        """

    notifications = Object(
            description=u"Notifications generated by current request",
            schema=INotificationList
            )

    def addDebugNotification(msg):
        """Shortcut to addNotification(msg, DEBUG)."""

    def addInfoNotification(msg):
        """Shortcut to addNotification(msg, INFO)."""

    def addNoticeNotification(msg):
        """Shortcut to addNotification(msg, NOTICE)."""

    def addWarningNotification(msg):
        """Shortcut to addNotification(msg, WARNING)."""

    def addErrorNotification(msg):
        """Shortcut to addNotification(msg, ERROR)."""

    def redirect(location, status=None):
        """As per IHTTPApplicationResponse.redirect, except notifications
        are preserved.
        """


class IErrorReport(Interface):
    id = TextLine(description=u"The name of this error report.")
    type = TextLine(description=u"The type of the exception that occurred.")
    value = TextLine(description=u"The value of the exception that occurred.")
    time = Datetime(description=u"The time at which the exception occurred.")
    pageid = TextLine(
        description=u"""
            The context class plus the page template where the exception
            occurred.
            """)
    branch_nick = TextLine(description=u"The branch nickname.")
    revno = TextLine(description=u"The revision number of the branch.")
    tb_text = Text(description=u"A text version of the traceback.")
    username = TextLine(description=u"The user associated with the request.")
    url = TextLine(description=u"The URL for the failed request.")
    req_vars = Attribute("The request variables.")


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


#
# LaunchpadFormView widget layout
#

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


class IBreadcrumbProvider(Interface):
    """Object that provides breadcrumb text."""

    def breadcrumb():
        """Breadcrumb text."""
