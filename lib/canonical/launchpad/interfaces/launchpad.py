# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ('ILaunchpadApplication', 'IMaloneApplication',
           'IRosettaApplication', 'ISoyuzApplication',
           'IDOAPApplication', 'IFOAFApplication',
           'IPasswordEncryptor', 'IReadZODBAnnotation',
           'IWriteZODBAnnotation', 'IZODBAnnotation',
           'IAuthorization', 'IObjectAuthorization',
           'IHasOwner', 'IOpenLaunchBag', 'ILaunchBag')

class ILaunchpadApplication(Interface):
    """Marker interface for a launchpad application.

    Rosetta, Malone and Soyuz are launchpad applications.  Their root
    application objects will provide an interface that extends this
    interface.
    """
    name = Attribute('Name')


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""


class IRosettaApplication(ILaunchpadApplication):
    """Application root for rosetta."""

    def translatables():
        """Return an iterator over the set of translatable Products which
        are part of Ubuntu's translation project."""


class ISoyuzApplication(ILaunchpadApplication):
    """Application root for soyuz."""

    def distributions():
        """Return a list of distributions that are entirely managed
        by Soyuz. This does not include distributions which are parsed by
        the backend tools, such as Fedora and Debian."""


class IDOAPApplication(ILaunchpadApplication):
    """DOAP application root."""


class IFOAFApplication(ILaunchpadApplication):
    """FOAF application root."""


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


class IObjectAuthorization(Interface):
    """Authorization policy for a particular object."""

    def checkPermission(person, permission):
        """Returns True if the person has that permission on the adapted
        object.  Otherwise returns False.

        The argument person is the person who is authenticated, or None if
        the principal is not adaptable to a Person.  So, person is None when
        no-one is logged in.
        """


class IAuthorization(Interface):
    """Authorization policy for a particular object and permission."""

    def checkUnauthenticated():
        """Returns True if an unauthenticated user has that permission
        on the adapted object.  Otherwise returns False.
        """

    def checkPermission(person):
        """Returns True if the person has that permission on the adapted
        object.  Otherwise returns False.

        The argument `person` is the person who is authenticated.
        """


class IHasOwner(Interface):
    """An object that has an owner."""

    owner = Attribute("The object's owner, which is an IPerson.")


class IHasAssignee(Interface):
    """An object that has an assignee."""

    assignee = Attribute("The object's assignee, which is an IPerson.")


class ILaunchBag(Interface):
    site = Attribute('The application object, or None')
    person = Attribute('Person, or None')
    project = Attribute('Project, or None')
    product = Attribute('Product, or None')
    distribution = Attribute('Distribution, or None')
    distrorelease = Attribute('DistroRelease, or None')
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

