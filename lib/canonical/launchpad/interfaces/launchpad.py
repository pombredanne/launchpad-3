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
           'IDOAPApplication', 'IFOAFApplication')

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


class ISoyuzApplication(ILaunchpadApplication):
    """Application root for soyuz."""


class IDOAPApplication(ILaunchpadApplication):
    """DOAP application root."""


class IFOAFApplication(ILaunchpadApplication):
    """FOAF application root."""

