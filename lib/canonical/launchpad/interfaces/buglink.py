# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for objects that can be linked to bugs."""

__metaclass__ = type

__all__ = ['IBugLinkTarget']

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class IBugLinkTarget(Interface):
    """An entity which can be linked to a bug.

    Examples include an ITicket, and an ICve.
    """

    bugs = Attribute("Bugs related to this object.")
    bug_links = Attribute("The links between bugs and this object.")

    def linkBug(bug, user=None):
        """Link the object with this bug. If the object is already linked,
        return the old linker, otherwise return a new linking object. User,
        if passed, is the person doing the linking.
        """

    def unlinkBug(bug, user=None):
        """Remove any link between this object and the bug. Action is being
        taken by the user, if passed."""

