# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bug comment browser view classes."""

__metaclass__ = type
__all__ = ['BugCommentView', 'BugComment', 'build_comments_from_chunks']

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import ILaunchBag, IBugComment
from canonical.launchpad.webapp import LaunchpadView

from canonical.config import config


def build_comments_from_chunks(chunks, bugtask, truncate=False):
    """Build BugComments from MessageChunks."""
    comments = {}
    index = 0
    for chunk in chunks:
        message_id = chunk.message.id
        if not comments.has_key(message_id):
            bc = BugComment(index, chunk.message, bugtask)
            bc.chunks.append(chunk)
            comments[message_id] = bc
            index += 1
    for comment in comments.values():
        # Once we have all the chunks related to a comment set up,
        # we get the text set up for display.
        comment.setupText(truncate=truncate)
    return comments


class BugComment:
    """Data structure that holds all data pertaining to a bug comment.

    It keeps track of which index it has in the bug comment list and
    also provides functionality to truncate the comment.

    Note that although this class is called BugComment it really takes
    as an argument a bugtask. The reason for this is to allow
    canonical_url()s of BugComments to take you to the correct
    (task-specific) location.
    """
    implements(IBugComment)

    def __init__(self, index, message, bugtask):
        self.index = index
        self.bugtask = bugtask

        self.title = message.title
        self.datecreated = message.datecreated
        self.owner = message.owner

        self.chunks = []
        self.bugattachments = []

    def setupText(self, truncate=False):
        """Set the text for display and truncate it if necessary."""
        comment_limit = config.malone.max_comment_size

        bits = [unicode(chunk.content) for chunk in self.chunks if chunk.content]
        text = self.text_contents = '\n\n'.join(bits)

        if truncate and comment_limit and len(text) > comment_limit:
            self.text_for_display = "%s..." % text[:comment_limit-3]
            self.was_truncated = True
        else:
            self.text_for_display = text
            self.was_truncated = False


class BugCommentView(LaunchpadView):
    """View for a single bug comment."""

    def __init__(self, context, request):
        # We use the current bug task as the context in order to get the
        # menu and portlets working.
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.comment = context
