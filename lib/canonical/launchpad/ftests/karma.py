# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions/classes to be used when testing the karma framework."""

__metaclass__ = type

from canonical.launchpad.ftests.event import TestEventListener
from canonical.launchpad.event.interfaces import IKarmaAssignedEvent
from canonical.launchpad.interfaces import IPerson


class KarmaAssignedEventListener:
    """Test helper class that registers a listener printing information
    whenever Karma is assigned.

    No karma assignments will be printed until the register_listener()
    method is called. 

    Each time Karma is assigned to a Person, a line in the following format
    will be printed:

        Karma added: action=<action>, points=<value>

    A set of KarmaAction objects assigned since the register_listener()
    method was called is available in the added_listener_actions property.
    """

    def __init__(self):
        self.added_karma_actions = set()

    def _on_assigned_event(self, object, event):
        action = event.karma.action
        self.added_karma_actions.add(action)
        print "Karma added: action=%s, points=%i" % (
            action.name, action.points)

    def register_listener(self):
        self.listener = TestEventListener(
            IPerson, IKarmaAssignedEvent, self._on_assigned_event)

    def unregister_listener(self):
        self.listener.unregister()


