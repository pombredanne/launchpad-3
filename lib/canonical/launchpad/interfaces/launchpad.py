# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ['ILaunchpadRoot', 'ILaunchpadApplication', 'IMaloneApplication',
           'IRosettaApplication', 'IDOAPApplication', 'IBazaarApplication',
           'IFOAFApplication', 'IPasswordEncryptor',
           'IReadZODBAnnotation', 'IWriteZODBAnnotation',
           'IZODBAnnotation', 'IAuthorization',
           'IHasOwner', 'IHasAssignee', 'IHasProduct', 
           'IHasProductAndAssignee', 'IOpenLaunchBag',
           'IAging', 'IHasDateCreated',
           'ILaunchBag', 'ICrowd', 'ILaunchpadCelebrities',
           'IBasicLink', 'ILink', 'ISelectionAwareLink',
           'ITabList', 'IFacetList', 'ICanonicalUrlData',
           'NoCanonicalUrl']


class ILaunchpadCelebrities(Interface):

    buttsource = Attribute("The 'buttsource' team.")
    admin = Attribute("The 'admins' team.")
    ubuntu = Attribute("The ubuntu Distribution.")
    rosetta_expert = Attribute("The Rosetta Experts team.")


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


class ILaunchpadRoot(Interface):
    """Marker interface for the root object of Launchpad."""


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""


class IRosettaApplication(ILaunchpadApplication):
    """Application root for rosetta."""

    def translatable_products(self, translationProject=None):
        """Return a list of the translatable products in the given
        Translation Project.

        For the moment it just returns every translatable product.
        """

    def translatable_distroreleases(self):
        """Return a list of the distroreleases in launchpad for which
        translations can be done.
        """

    def translation_groups(self):
        """Return a list of the translation groups in the system."""

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


class IDOAPApplication(ILaunchpadApplication):
    """DOAP application root."""


class IFOAFApplication(ILaunchpadApplication):
    """FOAF application root."""


class IBazaarApplication(ILaunchpadApplication):
    """Bazaar Application"""


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
    person = Attribute('Person, or None')
    project = Attribute('Project, or None')
    product = Attribute('Product, or None')
    distribution = Attribute('Distribution, or None')
    distrorelease = Attribute('DistroRelease, or None')
    distroarchrelease = Attribute('DistroArchRelease, or None')
    sourcepackage = Attribute('Sourcepackage, or None')
    sourcepackagereleasepublishing = Attribute(
        'SourcepackageReleasePublishing, or None')
    bug = Attribute('Bug, or None')

    user = Attribute('Currently authenticated person, or None')
    login = Attribute('The login used by the authenticated person, or None')


class IOpenLaunchBag(ILaunchBag):
    def add(ob):
        '''Stick the object into the correct attribute of the ILaunchBag,
        or ignored, or whatever'''
    def clear():
        '''Empty the bag'''
    def setLogin(login):
        '''Set the login to the given value.'''


class IBasicLink(Interface):
    """A link."""

    id = Attribute('id')
    href = Attribute('the relative href')
    title = Attribute('text for the link')
    summary = Attribute('summary for this facet')


class ILink(IBasicLink):
    """A link, including whether or not it is disabled."""
    enabled = Attribute('boolean, whether enabled')


class ISelectionAwareLink(ILink):
    selected = Attribute('bool; is this facet the selected one?')


class IFacetList(Interface):
    """A list of facets in various categories."""

    links = Attribute("List of ILinks that are main links.")
    overflow = Attribute("List of ILinks that overflow.")


class ITabList(Interface):
    """A list of tabs in various categories."""

    links = Attribute("List of ILinks that are main links.")
    overflow = Attribute("List of ILinks that overflow.")


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
