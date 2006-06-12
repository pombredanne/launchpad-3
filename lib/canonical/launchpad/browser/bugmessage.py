# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugMessage-related browser view classes."""

__metaclass__ = type
__all__ = ['BugMessageAddView', 'BugMessageContextMenu', 'BugMessageView']

from zope.component import getUtility

from canonical.launchpad.browser.bug import BugContextMenu
from canonical.launchpad.browser.message import MessageAddView
from canonical.launchpad.interfaces import IBug, IBugMessage, ILaunchBag
from canonical.launchpad.webapp import LaunchpadView

class BugMessageAddView(MessageAddView):
    def __init__(self, context, request):
        context = IBug(context)
        MessageAddView.__init__(self, context, request)


class BugMessageView(LaunchpadView):

    def __init__(self, context, request):
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.message = context.message

class BugMessageContextMenu(BugContextMenu):
    usedfor = IBugMessage
