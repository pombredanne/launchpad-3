# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bug comment browser view classes."""

__metaclass__ = type
__all__ = ['BugCommentView', 'BugComment', 'build_comments_from_chunks']

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (ILaunchBag, IBugComment,
    IBugMessageSet)
from canonical.launchpad.webapp import LaunchpadView

from canonical.config import config


def build_comments_from_chunks(chunks, bugtask, truncate=False):
    """Build BugComments from MessageChunks."""
    comments = {}
    index = 0
    for chunk in chunks:
        message_id = chunk.message.id
        bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
            bugtask.bug, chunk.message)
        bug_comment = comments.get(message_id)
        if bug_comment is None:
            bug_comment = BugComment(index, chunk.message, bugtask,
                bug_message.bugwatch)
            comments[message_id] = bug_comment
            index += 1
        bug_comment.chunks.append(chunk)
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

    def __init__(self, index, message, bugtask, bugwatch=None):
        self.index = index
        self.bugtask = bugtask
        self.bugwatch = bugwatch

        self.title = message.title
        self.display_title = False
        self.datecreated = message.datecreated
        self.owner = message.owner
        self.rfc822msgid = message.rfc822msgid

        self.chunks = []
        self.bugattachments = []

        self.display_if_from_bugwatch = config.malone.show_imported_comments

    @property
    def can_be_shown(self):
        """Return whether or not the BugComment can be shown."""
        if self.bugwatch and not self.display_if_from_bugwatch:
            return False
        else:
            return True

    def setupText(self, truncate=False):
        """Set the text for display and truncate it if necessary.

        Note that this method must be called before either isIdenticalTo() or
        isEmpty() are called, since to do otherwise would mean that they could
        return false positives and negatives respectively.
        """
        comment_limit = config.malone.max_comment_size

        bits = [unicode(chunk.content) for chunk in self.chunks if chunk.content]
        text = self.text_contents = '\n\n'.join(bits)

        if truncate and comment_limit and len(text) > comment_limit:
            # Note here that we truncate at comment_limit, and not
            # comment_limit - 3; while it would be nice to account for
            # the ellipsis, this breaks down when the comment limit is
            # less than 3 (which can happen in a testcase) and it makes
            # counting the strings harder.
            self.text_for_display = "%s..." % text[:comment_limit]
            self.was_truncated = True
        else:
            self.text_for_display = text
            self.was_truncated = False

    def isIdenticalTo(self, other):
        """Compare this BugComment to another and return True if they are
        identical.
        """
        if self.owner != other.owner:
            return False
        if self.text_for_display != other.text_for_display:
            return False
        if self.title != other.title:
            return False
        if self.bugattachments or other.bugattachments:
            # We shouldn't collapse comments which have attachments;
            # there's really no possible identity in that case.
            return False
        return True

    def isEmpty(self):
        """Return True if text_for_display is empty."""
        return (len(self.text_for_display) == 0 and
            len(self.bugattachments) == 0)


class BugCommentView(LaunchpadView):
    """View for a single bug comment."""

    def __init__(self, context, request):
        # We use the current bug task as the context in order to get the
        # menu and portlets working.
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.comment = context

