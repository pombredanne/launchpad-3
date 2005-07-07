# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug attachment views."""

__metaclass__ = type

__all__ = [
    'traverseBugAttachment',
    'BugAttachmentContentView',
    ]

def traverseBugAttachment(bugattachment, request, name):
    # TODO: Find out how to make SQLObject only retrieve the
    # desired IBugAttachmentContent rather than all of them
    # and only returning the requested one.
    try:
        name = int(name)
        content = bugattachment.versions
        for c in content:
            if c.bugattachment == bugattachment.id:
                return c
        raise KeyError, name
    except ValueError:
        raise KeyError, name


class BugAttachmentContentView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def index(self):
        self.request.response.setHeader('Content-Type', self.context.mimetype)
        return self.context.content


