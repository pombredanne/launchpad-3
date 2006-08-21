# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for objects that can be linked to bugs."""

__metaclass__ = type

__all__ = ['IBugLinkTarget',
           'IBugLink']

from zope.interface import Interface
from zope.schema import List, Object

from canonical.launchpad import _
from canonical.launchpad.fields import BugField
from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.interfaces.launchpad import IHasBug


class IBugLink(IHasBug):
    """An entity representing a link between a bug and its target."""

    bug = BugField(title=_("The bug that is linked to."), required=True,
        readonly=True)

    target = Object(title=_("The object to which the bug is linked."),
        required=True, readonly=True, schema=Interface)


class IBugLinkTarget(Interface):
    """An entity which can be linked to a bug.

    Examples include an ITicket, and an ICve.
    """

    bugs = List(title=_("Bugs related to this object."),
                value_type=Object(schema=IBug), readonly=True)
    bug_links = List(title=_("The links between bugs and this object."),
                     value_type=Object(schema=IBugLink), readonly=True)

    def linkBug(bug):
        """Link the object with this bug. If the object is already linked,
        return the old linker, otherwise return a new IBugLink object.

        If a new IBugLink is created by this method, a SQLObjectCreatedEvent
        should be sent.
        """

    def unlinkBug(bug):
        """Remove any link between this object and the bug. If the bug wasn't
        linked to the target, returns None otherwise returns the IBugLink
        object which was removed.

        If an IBugLink is removed by this method, a SQLObjectDeletedEvent
        should be sent.
        """
