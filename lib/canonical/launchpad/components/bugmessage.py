# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

class BugMessageToMessageAdapter:
    """Adapt an IBugMessage into an IMessage."""

    def __init__(self, bugmessage):
        self.bugmessage = bugmessage

    def __call__(self):
        return self.bugmessage.message
