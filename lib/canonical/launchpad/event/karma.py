# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['KarmaAssignedEvent']

from zope.interface import implements

from canonical.launchpad.event.interfaces import IKarmaAssignedEvent


class KarmaAssignedEvent:
    """See canonical.launchpad.event.interfaces.IKarmaAssignedEvent."""

    implements(IKarmaAssignedEvent)

    def __init__(self, object, karma):
        self.object = object
        self.karma = karma

