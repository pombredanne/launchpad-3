# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ('ILaunchpadApplication', 'IMaloneApplication',
           'IRosettaApplication', 'ISoyuzApplication',
           'IDOAPApplication', 'IFOAFApplication',
           'IPasswordEncryptor', 'IReadZODBAnnotation',
           'IWriteZODBAnnotation', 'IZODBAnnotation',
           'IAuthorization')

class ILaunchpadApplication(Interface):
    """Marker interface for a launchpad application.

    Rosetta, Malone and Soyuz are launchpad applications.  Their root
    application objects will provide an interface that extends this
    interface.
    """


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""


class IRosettaApplication(ILaunchpadApplication):
    """Application root for rosetta."""

    def translatables():
        """Return an iterator over the set of translatable Products which
        are part of Ubuntu's translation project."""


class ISoyuzApplication(ILaunchpadApplication):
    """Application root for soyuz."""


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


class IAuthorization(Interface):
    """Authorization policy for a particular object."""

    def checkPermission(principal, permission):
        """Returns True if the principal has that permission on the adapted
        object.

        Otherwise returns False or returns None; these are equivalent.

        The easiest way to return None is to allow the flow control to
        'fall off the end' of the method.
        """
