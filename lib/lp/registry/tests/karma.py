# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions/classes to be used when testing the karma framework."""

__metaclass__ = type

from canonical.launchpad.event.interfaces import IKarmaAssignedEvent
from canonical.launchpad.ftests.event import TestEventListener
from lp.registry.interfaces.person import IPerson


class KarmaAssignedEventListener:
    """Test helper class that registers a listener printing information
    whenever Karma is assigned.

    No karma assignments will be printed until the register_listener()
    method is called.

    Each time Karma is assigned to a Person, a line in the following format
    will be printed:

        Karma added: action=<action>, [product|distribution]=<contextname>

    If show_person is set to True, the name of the person to whom karma is
    granted will also be shown like this (on one line):

        Karma added: action=<action>, [product|distribution]=<contextname>,
        person=<name>

    A set of KarmaAction objects assigned since the register_listener()
    method was called is available in the added_listener_actions property.
    """

    def __init__(self, show_person=False):
        self.added_karma_actions = set()
        self.show_person = show_person

    def _on_assigned_event(self, object, event):
        action = event.karma.action
        self.added_karma_actions.add(action)
        text = "Karma added: action=%s," % action.name
        if event.karma.product is not None:
            text += " product=%s" % event.karma.product.name
        elif event.karma.distribution is not None:
            text += " distribution=%s" % event.karma.distribution.name
        if self.show_person:
            text += ", person=%s" % event.karma.person.name
        print text

    def register_listener(self):
        self.listener = TestEventListener(
            IPerson, IKarmaAssignedEvent, self._on_assigned_event)

    def unregister_listener(self):
        self.listener.unregister()

