# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Events related to bugs."""

__metaclass__ = type
__all__ = ['BugBecameQuestionEvent']

from zope.interface import implements

from canonical.launchpad.event.interfaces import IBugBecameQuestionEvent


class BugBecameQuestionEvent:
    """See `IBugBecameQuestionEvent`."""

    implements(IBugBecameQuestionEvent)

    def __init__(self, bug, question):
        self.bug = bug
        self.question = question

