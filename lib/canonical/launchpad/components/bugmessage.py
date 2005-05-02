# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

class BugMessageToMessageAdapter:
    """Adapt an IBugMessage into an IMessage."""

    def __init__(self, bugmessage):
        self.bugmessage = bugmessage

    def __call__(self):
        return self.bugmessage.message

class BugMessageToAddMessageAdapter:
    """Adapt an IBugMessage to an IAddMessage."""

    def __init__(self, bugmessage):
        self.bugmessage = bugmessage

    def title(self):
        return self.bugmessage.message.title
    title = property(title)

    def content(self):
        return self.bugmessage.message.contents
    content = property(content)
