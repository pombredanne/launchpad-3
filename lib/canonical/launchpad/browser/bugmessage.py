# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View classes related to IBugMessage."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.interfaces import (
    ILaunchBag, IBugMessageSet)

class BugMessageAddView(SQLObjectAddView):
    def create(self, *args, **kw):
        bugmessageset = getUtility(IBugMessageSet)
        launchbag = getUtility(ILaunchBag)

        return bugmessageset.createMessage(
            subject=kw.get('subject'), content=kw.get('content'),
            bug=launchbag.bug, owner=launchbag.user)
