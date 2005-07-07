# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Distribution tool interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroTools',
    ]

from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IDistroTools(Interface):
    """Interfaces to Tools for Distribution and DistroRelase Manipulation"""

    def createDistro(owner, name, displayname, title,
        summary, description, domain):
        """ Create a Distribution """

    def createDistroRelease(owner, title, distribution, summary, description,
                            version, parent):
        """ Create a DistroRelease """

    def getDistroRelease():
        """Return All Available DistroReleases"""
