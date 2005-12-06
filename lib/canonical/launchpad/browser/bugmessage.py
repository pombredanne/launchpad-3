# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugMessage-related browser view classes."""

__metaclass__ = type
__all__ = ['BugMessageAddView']

from canonical.launchpad.browser.message import MessageAddView
from canonical.launchpad.interfaces.bug import IBug

class BugMessageAddView(MessageAddView):
    def __init__(self, context, request):
        context = IBug(context)
        MessageAddView.__init__(self, context, request)
