# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for objects that can be linked to bugs."""

__metaclass__ = type

__all__ = ['IBugLinkTarget',
           'IBugLink']

from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.launchpad import IHasBug


class IBugLinkTarget(Interface):
    """An entity which can be linked to a bug.

    Examples include an ITicket, and an ICve.
    """

    bugs = Attribute("Bugs related to this object.")
    bug_links = Attribute("The links between bugs and this object.")

    def linkBug(bug):
        """Link the object with this bug. If the object is already linked,
        return the old linker, otherwise return a new IBugLink object.

        If a new IBugLink is created by this method, an appropriate
        SQLObjectCreatedEvent should be sent for the IBugLink created and
        a SQLObjectModifiedEvent should be sent for the target.
        """

    def unlinkBug(bug):
        """Remove any link between this object and the bug. If the bug wasn't
        linked to the target, returns None otherwise returns the IBugLink
        object which was removed.

        If aIBugLink is created by this method, an appropriate
        SQLObjectDeletedEvent should be sent for the IBugLink removed and
        a SQLObjectModifiedEvent should be sent for the target.
        """


class IBugLink(IHasBug):
    """An entity representing a link between a bug and its target."""

    bug = Attribute("The bug that is linked to.")

    target = Attribute("The object to which the bug is linked.")
