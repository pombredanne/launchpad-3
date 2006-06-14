# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bug comment browser view classes."""

__metaclass__ = type
__all__ = ['BugComment', 'BugCommentView']

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import IBugComment, ILaunchBag, IMessage
from canonical.launchpad.webapp import LaunchpadView
from canonical.lp import decorates


class BugComment:
    """A bug comment for displaying on a page.

    It keeps track on which index it has in the bug comment list and
    also provides functionality to truncate the comment.
    """
    implements(IBugComment)
    decorates(IMessage, 'message')

    is_truncated = False

    def __init__(self, bugtask, index, message, comment_limit=None):
        self.bugtask = bugtask
        self.index = index
        self.message = message
        self.comment_limit = comment_limit
        self._setTextForDisplay(message.text_contents)

    def _setTextForDisplay(self, text):
        """Set the text for display and truncate it if necessary."""
        comment_limit = self.comment_limit
        if comment_limit and len(text) > comment_limit:
            self.text_for_display = "%s..." % text[:comment_limit-3]
            self.is_truncated = True
        else:
            self.text_for_display = text


class BugCommentView(LaunchpadView):
    """View for a single bug comment."""

    def __init__(self, context, request):
        # We use the current bug task as the context in order to get the
        # menu and portlets working.
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.comment = context
