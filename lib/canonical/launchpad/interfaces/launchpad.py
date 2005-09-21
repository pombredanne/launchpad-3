# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from zope.interface import Interface, Attribute, implements
from zope.i18nmessageid import MessageIDFactory
import zope.app.publication.interfaces
import zope.app.traversing.interfaces
from persistent import IPersistent

_ = MessageIDFactory('launchpad')

__all__ = ['ILaunchpadRoot', 'ILaunchpadApplication', 'IMaloneApplication',
           'IRosettaApplication', 'IRegistryApplication', 'IBazaarApplication',
           'IFOAFApplication', 'IPasswordEncryptor',
           'IReadZODBAnnotation', 'IWriteZODBAnnotation',
           'IZODBAnnotation', 'IAuthorization',
           'IHasOwner', 'IHasAssignee', 'IHasProduct', 
           'IHasProductAndAssignee', 'IOpenLaunchBag',
           'IAging', 'IHasDateCreated',
           'ILaunchBag', 'ICrowd', 'ILaunchpadCelebrities',
           'ILinkData', 'ILink', 'IFacetLink', 'IStructuredString',
           'IMenu', 'IMenuBase', 'IFacetMenu',
           'IApplicationMenu', 'IContextMenu',
           'ICanonicalUrlData', 'NoCanonicalUrl',
           'IDBSchema', 'IDBSchemaItem', 'IAuthApplication',
           'IPasswordChangeApp', 'IPasswordResets', 'IShipItApplication',
           'IAfterTraverseEvent', 'AfterTraverseEvent',
           'IBeforeTraverseEvent', 'BeforeTraverseEvent'
           ]


class ILaunchpadCelebrities(Interface):

    buttsource = Attribute("The 'buttsource' team.")
    admin = Attribute("The 'admins' team.")
    ubuntu = Attribute("The ubuntu Distribution.")
    debian = Attribute("The debian Distribution.")
    rosetta_expert = Attribute("The Rosetta Experts team.")
    debbugs = Attribute("The Debian Bug Tracker")
    shipit_admin = Attribute("The ShipIt Administrators.")


class ICrowd(Interface):

    def __contains__(person_or_team_or_anything):
        """Return True if the given person_or_team_or_anything is in the crowd.

        Note that a particular crowd can choose to answer "True" to this
        question, if that is what it is supposed to do.  So, crowds that
        contain other crowds will want to allow the other crowds the
        opportunity to answer __contains__ before that crowd does.
        """

    def __add__(crowd):
        """Return a new ICrowd that is this crowd added to the given crowd.

        The returned crowd contains the person or teams in
        both this crowd and the given crowd.
        """


class ILaunchpadApplication(Interface):
    """Marker interface for a launchpad application.

    Rosetta, Malone and Soyuz are launchpad applications.  Their root
    application objects will provide an interface that extends this
    interface.
    """
    name = Attribute('Name')
    title = Attribute('Title')


class ILaunchpadRoot(zope.app.traversing.interfaces.IContainmentRoot):
    """Marker interface for the root object of Launchpad."""


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""

    bug_count = Attribute("The number of bugs recorded in Malone")
    bugwatch_count = Attribute("The number of links to external bug trackers")
    bugextref_count = Attribute("The number of links to outside URL's")
    bugtask_count = Attribute("The number of bug tasks in Malone")
    bugtracker_count = Attribute("The number of bug trackers in Malone")
    top_bugtrackers = Attribute("The BugTrackers with the most watches.")
    latest_bugs = Attribute("The latest 5 bugs filed.")


class IRosettaApplication(ILaunchpadApplication):
    """Application root for rosetta."""

    statsdate = Attribute("""The date stats were last updated.""")

    def translatable_products(self):
        """Return a list of the translatable products."""

    def translatable_distroreleases(self):
        """Return a list of the distroreleases in launchpad for which
        translations can be done.
        """

    def translation_groups(self):
        """Return a list of the translation groups in the system."""

    def updateStatistics(self):
        """Update the Rosetta statistics in the system."""

    def potemplate_count(self):
        """Return the number of potemplates in the system."""

    def pofile_count(self):
        """Return the number of pofiles in the system."""

    def pomsgid_count(self):
        """Return the number of msgs in the system."""

    def translator_count(self):
        """Return the number of people who have given translations."""

    def language_count(self):
        """Return the number of languages Rosetta can translate into."""

    def translation_groups():
        """Return an iterator over the set of translation groups in
        Rosetta."""

    def potemplate_count():
        """Return the number of potemplates in the system."""

    def pofile_count():
        """Return the number of pofiles in the system."""

    def pomsgid_count():
        """Return the number of PO MsgID's in the system."""

    def translator_count():
        """Return the number of translators in the system."""

    def language_count():
        """Return the number of languages in the system."""


class IRegistryApplication(ILaunchpadApplication):
    """Registry application root."""


class IFOAFApplication(ILaunchpadApplication):
    """FOAF application root."""


class IShipItApplication(ILaunchpadApplication):
    """ShipIt application root."""


class IBazaarApplication(ILaunchpadApplication):
    """Bazaar Application"""


class IAuthApplication(Interface):
    """Interface for AuthApplication."""

    def __getitem__(name):
        """The __getitem__ method used to traverse the app."""

    def sendPasswordChangeEmail(longurlsegment, toaddress):
        """Send an Password change special link for a user."""

    def getPersonFromDatabase(emailaddr):
        """Returns the Person in the database who has the given email address.

        If there is no Person for that email address, returns None.
        """

    def newLongURL(person):
        """Creates a new long url for the given person.

        Returns the long url segment.
        """

class IPasswordResets(IPersistent):
    """Interface for PasswordResets"""

    lifetime = Attribute("Maximum time between request and reset password")

    def newURL(person):
        """Create a new URL and store person and creation time"""

    def getPerson(long_url):
        """Get the person object using the long_url if not expired"""


class IPasswordChangeApp(Interface):
    """Interface for PasswdChangeApp."""
    code = Attribute("The transaction code")


class IPasswordEncryptor(Interface):
    """An interface representing a password encryption scheme."""

    def encrypt(plaintext):
        """Return the encrypted value of plaintext."""

    def validate(plaintext, encrypted):
        """Return a true value if the encrypted value of 'plaintext' is
        equivalent to the value of 'encrypted'.  In general, if this
        method returns true, it can also be assumed that the value of
        self.encrypt(plaintext) will compare equal to 'encrypted'.
        """


class IReadZODBAnnotation(Interface):

    def __getitem__(namespace):
        """Get the annotation for the given dotted-name namespace."""

    def get(namespace, default=None):
        """Get the annotation for the given dotted-name namespace.

        If there is no such annotation, return the default value.
        """

    def __contains__(namespace):
        """Returns true if there is an annotation with the given namespace.

        Otherwise, returns false.
        """

    def __delitem__(namespace):
        """Removes annotation at the given namespace."""

class IWriteZODBAnnotation(Interface):

    def __setitem__(namespace, value):
        """Set a value as the annotation for the given namespace."""

class IZODBAnnotation(IReadZODBAnnotation, IWriteZODBAnnotation):
    pass


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

class IHasOwner(Interface):
    """An object that has an owner."""

    owner = Attribute("The object's owner, which is an IPerson.")


class IHasAssignee(Interface):
    """An object that has an assignee."""

    assignee = Attribute("The object's assignee, which is an IPerson.")


class IHasProduct(Interface):
    """An object that has a product attribute that is an IProduct."""

    product = Attribute("The object's product")


class IHasProductAndAssignee(IHasProduct, IHasAssignee):
    """An object that has a product attribute and an assigned attribute.
    See IHasProduct and IHasAssignee."""


class IAging(Interface):
    """Something that gets older as time passes."""

    def currentApproximateAge():
        """Return a human-readable string of how old this thing is.

        Values returned are things like '2 minutes', '3 hours', '1 month', etc.
        """

class IHasDateCreated(Interface):
    """Something created on a certain date."""

    datecreated = Attribute("The date on which I was created.")

class ILaunchBag(Interface):
    site = Attribute('The application object, or None')
    person = Attribute('IPerson, or None')
    project = Attribute('IProject, or None')
    product = Attribute('IProduct, or None')
    distribution = Attribute('IDistribution, or None')
    distrorelease = Attribute('IDistroRelease, or None')
    distroarchrelease = Attribute('IDistroArchRelease, or None')
    sourcepackage = Attribute('ISourcepackage, or None')
    sourcepackagereleasepublishing = Attribute(
        'ISourcepackageReleasePublishing, or None')
    bug = Attribute('IBug, or None')
    bugtask = Attribute('IBugTask, or None')

    user = Attribute('Currently authenticated IPerson, or None')
    login = Attribute('The login used by the authenticated person, or None')

    timezone = Attribute("The user's time zone")

class IOpenLaunchBag(ILaunchBag):
    def add(ob):
        '''Stick the object into the correct attribute of the ILaunchBag,
        or ignored, or whatever'''
    def clear():
        '''Empty the bag'''
    def setLogin(login):
        '''Set the login to the given value.'''


class IStructuredString(Interface):
    """An object that represents a string that is to retain its html structure
    in a menu's link text.
    """

    escapedtext = Attribute("The escaped text for display on a web page.")


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


class ILink(ILinkData):
    """An object that represents a link in a menu.

    The attributes name, url and linked may be set by the menus infrastructure.
    """

    name = Attribute("The name of this link in Python data structures.")

    url = Attribute(
        "The full url this link points to.  Set by the menus infrastructure. "
        "None before it is set.")

    linked = Attribute(
        "A boolean value saying whether this link should appear as a clickable"
        " link in the UI.  The general rule is that a link to the current"
        " page should not be shown linked.  Defaults to True.")

    enabled = Attribute(
        "Boolean to say whether this link is enabled.  Can be read and set.")

    escapedtext = Attribute("Text string, escaped as necessary.")


class IFacetLink(ILink):
    """A link in a facet menu.

    It has a 'selected' attribute that is set by the menus infrastructure,
    and indicates whether the link is the selected facet.
    """

    selected = Attribute(
        "A boolean value saying whether this link is the selected facet menu "
        "item.  Defaults to False.")


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

    context = Attribute('the object that has this menu')


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


class ICanonicalUrlData(Interface):
    """Tells you how to work out a canonical url for an object."""

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


class IAfterTraverseEvent(Interface):
    """An event which gets sent after publication traverse."""


class AfterTraverseEvent:
    """An event which gets sent after publication traverse."""

    implements(IAfterTraverseEvent)

    def __init__(self, ob, request):
        self.object = ob
        self.request = request


class IBeforeTraverseEvent(
    zope.app.publication.interfaces.IBeforeTraverseEvent):
    pass


class BeforeTraverseEvent(zope.app.publication.interfaces.BeforeTraverseEvent):
    pass


# XXX: These need making into a launchpad version rather than the zope versions
#      for the publisher simplification work.  SteveAlexander 2005-09-14
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
