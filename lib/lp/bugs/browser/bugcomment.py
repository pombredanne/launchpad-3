# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug comment browser view classes."""

__metaclass__ = type
__all__ = [
    'BugComment',
    'BugCommentBoxExpandedReplyView',
    'BugCommentBoxView',
    'BugCommentBreadcrumb',
    'BugCommentView',
    'BugCommentXHTMLRepresentation',
    'build_comments_from_chunks',
    'group_comments_with_activity',
    ]

from datetime import (
    datetime,
    timedelta,
    )
from itertools import (
    chain,
    groupby,
    )
from operator import itemgetter

from lazr.restful.interfaces import IWebServiceClientRequest
from pytz import utc
from zope.component import (
    adapts,
    getMultiAdapter,
    getUtility,
    )
from zope.interface import (
    implements,
    Interface,
    )

from canonical.config import config
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.webapp import (
    canonical_url,
    LaunchpadView,
    )
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.bugs.interfaces.bugmessage import IBugComment


COMMENT_ACTIVITY_GROUPING_WINDOW = timedelta(minutes=5)


def build_comments_from_chunks(
        bugtask, truncate=False, slice_info=None, show_spam_controls=False):
    """Build BugComments from MessageChunks.

    :param truncate: Perform truncation of large messages.
    :param slice_info: If not None, an iterable of slices to retrieve.
    """
    chunks = bugtask.bug.getMessagesForView(slice_info=slice_info)
    # This would be better as part of indexed_messages eager loading.
    comments = {}
    for bugmessage, message, chunk in chunks:
        bug_comment = comments.get(message.id)
        if bug_comment is None:
            bug_comment = BugComment(
                bugmessage.index, message, bugtask, visible=message.visible,
                show_spam_controls=show_spam_controls)
            comments[message.id] = bug_comment
            # This code path is currently only used from a BugTask view which
            # has already loaded all the bug watches. If we start lazy loading
            # those, or not needing them we will need to batch lookup watches
            # here.
            if bugmessage.bugwatchID is not None:
                bug_comment.bugwatch = bugmessage.bugwatch
                bug_comment.synchronized = (
                    bugmessage.remote_comment_id is not None)
        bug_comment.chunks.append(chunk)

    for comment in comments.values():
        # Once we have all the chunks related to a comment populated,
        # we get the text set up for display.
        comment.setupText(truncate=truncate)
    return comments


def group_comments_with_activity(comments, activities):
    """Group comments and activity together for human consumption.

    Generates a stream of comment instances (with the activity grouped within)
    or `list`s of grouped activities.

    :param comments: An iterable of `BugComment` instances, which should be
        sorted by index already.
    :param activities: An iterable of `BugActivity` instances.
    """
    window = COMMENT_ACTIVITY_GROUPING_WINDOW

    comment_kind = "comment"
    if comments:
        max_index = comments[-1].index + 1
    else:
        max_index = 0
    comments = (
        (comment.datecreated, comment.index,
            comment.owner, comment_kind, comment)
        for comment in comments)
    activity_kind = "activity"
    activity = (
        (activity.datechanged, max_index,
            activity.person, activity_kind, activity)
        for activity in activities)
    # when an action and a comment happen at the same time, the action comes
    # second, when two events are tied the comment index is used to
    # disambiguate.
    events = sorted(chain(comments, activity), key=itemgetter(0, 1, 2))

    def gen_event_windows(events):
        """Generate event windows.

        Yields `(window_index, kind, event)` tuples, where `window_index` is
        an integer, and is incremented each time the windowing conditions are
        triggered.

        :param events: An iterable of `(date, ignored, actor, kind, event)`
            tuples in order.
        """
        window_comment, window_actor = None, None
        window_index, window_end = 0, None
        for date, _, actor, kind, event in events:
            window_ended = (
                # A window may contain only one comment.
                (window_comment is not None and kind is comment_kind) or
                # All events must have happened within a given timeframe.
                (window_end is None or date >= window_end) or
                # All events within the window must belong to the same actor.
                (window_actor is None or actor != window_actor))
            if window_ended:
                window_comment, window_actor = None, actor
                window_index, window_end = window_index + 1, date + window
            if kind is comment_kind:
                window_comment = event
            yield window_index, kind, event

    event_windows = gen_event_windows(events)
    event_windows_grouper = groupby(event_windows, itemgetter(0))
    for window_index, window_group in event_windows_grouper:
        window_group = [
            (kind, event) for (index, kind, event) in window_group]
        for kind, event in window_group:
            if kind is comment_kind:
                window_comment = event
                window_comment.activity.extend(
                    event for (kind, event) in window_group
                    if kind is activity_kind)
                yield window_comment
                # There's only one comment per window.
                break
        else:
            yield [event for (kind, event) in window_group]


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

    def __init__(
            self, index, message, bugtask, activity=None,
            visible=True, show_spam_controls=False):

        self.index = index
        self.bugtask = bugtask
        self.bugwatch = None

        self.title = message.title
        self.display_title = False
        self.datecreated = message.datecreated
        self.owner = message.owner
        self.rfc822msgid = message.rfc822msgid

        self.chunks = []
        self.bugattachments = []
        self.patches = []

        if activity is None:
            activity = []

        self.activity = activity

        self.synchronized = False
        self.visible = visible
        self.show_spam_controls = show_spam_controls

    @property
    def show_for_admin(self):
        """Show hidden comments for Launchpad admins.

        This is used in templates to add a class to hidden
        comments to enable display for admins, so the admin
        can see the comment even after it is hidden. Since comments
        aren't published unless the user is registry or admin, this
        can just check if the comment is visible.
        """
        return not self.visible

    def setupText(self, truncate=False):
        """Set the text for display and truncate it if necessary.

        Note that this method must be called before either isIdenticalTo() or
        isEmpty() are called, since to do otherwise would mean that they could
        return false positives and negatives respectively.
        """
        comment_limit = config.malone.max_comment_size

        bits = [unicode(chunk.content)
                for chunk in self.chunks
                if chunk.content is not None and len(chunk.content) > 0]
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
        if (self.bugattachments or self.patches or other.bugattachments or
            other.patches):
            # We shouldn't collapse comments which have attachments;
            # there's really no possible identity in that case.
            return False
        return True

    def isEmpty(self):
        """Return True if text_for_display is empty."""

        return (len(self.text_for_display) == 0 and
            len(self.bugattachments) == 0 and len(self.patches) == 0)

    @property
    def add_comment_url(self):
        return canonical_url(self.bugtask, view_name='+addcomment')

    @property
    def show_footer(self):
        """Return True if the footer should be shown for this comment."""
        return bool(
            len(self.activity) > 0 or
            self.bugwatch or
            self.show_spam_controls)

    @property
    def rendered_cache_time(self):
        """The number of seconds we can cache the rendered comment for.

        Bug comments are cached with 'authenticated' visibility, so
        should contain no information hidden from some users. We use
        'authenticated' rather than 'public' as email addresses are
        obfuscated for unauthenticated users.
        """
        now = datetime.now(tz=utc)

        # The major factor in how long we can cache a bug comment is the
        # timestamp. For up to 5 minutes comments and activity can be grouped
        # together as related, so do not cache.
        if self.datecreated > now - COMMENT_ACTIVITY_GROUPING_WINDOW:
            # Don't return 0 because that indicates no time limit.
            return -1

        # The rendering of the timestamp changes every minute for the first
        # hour because we say '7 minutes ago'.
        elif self.datecreated > now - timedelta(hours=1):
            return 60

        # Don't cache for long if we are waiting for synchronization.
        elif self.bugwatch and not self.synchronized:
            return 5 * 60

        # For the rest of the first day, the rendering changes every
        # hour. '4 hours ago'. Expire in 15 minutes so the timestamp
        # is at most 15 minutes out of date.
        elif self.datecreated > now - timedelta(days=1):
            return 15 * 60

        # Otherwise, cache away. Lets cache for 6 hours. We don't want
        # to cache for too long as there are still things that can
        # become stale - eg. if a bug attachment has been deleted we
        # should stop rendering the link.
        else:
            return 6 * 60 * 60


class BugCommentView(LaunchpadView):
    """View for a single bug comment."""

    def __init__(self, context, request):
        # We use the current bug task as the context in order to get the
        # menu and portlets working.
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.comment = context

    @property
    def show_spam_controls(self):
        return self.comment.show_spam_controls

    def page_title(self):
        return 'Comment %d for bug %d' % (
            self.comment.index, self.context.bug.id)

    @property
    def privacy_notice_classes(self):
        if not self.context.bug.private:
            return 'hidden'
        else:
            return ''


class BugCommentBoxViewMixin:
    """A class which provides proxied Librarian URLs for bug attachments."""

    @property
    def show_spam_controls(self):
        if hasattr(self.context, 'show_spam_controls'):
            return self.context.show_spam_controls
        elif (hasattr(self, 'comment') and
            hasattr(self.comment, 'show_spam_controls')):
            return self.comment.show_spam_controls
        else:
            return False

    def proxiedUrlOfLibraryFileAlias(self, attachment):
        """Return the proxied URL for the Librarian file of the attachment."""
        return ProxiedLibraryFileAlias(
            attachment.libraryfile, attachment).http_url


class BugCommentBoxView(LaunchpadView, BugCommentBoxViewMixin):
    """Render a comment box with reply field collapsed."""

    expand_reply_box = False


class BugCommentBoxExpandedReplyView(LaunchpadView, BugCommentBoxViewMixin):
    """Render a comment box with reply field expanded."""

    expand_reply_box = True


class BugCommentXHTMLRepresentation:
    adapts(IBugComment, IWebServiceClientRequest)
    implements(Interface)

    def __init__(self, comment, request):
        self.comment = comment
        self.request = request

    def __call__(self):
        """Render `BugComment` as XHTML using the webservice."""
        comment_view = getMultiAdapter(
            (self.comment, self.request), name="+box")
        return comment_view()


class BugCommentBreadcrumb(Breadcrumb):
    """Breadcrumb for an `IBugComment`."""

    def __init__(self, context):
        super(BugCommentBreadcrumb, self).__init__(context)

    @property
    def text(self):
        return "Comment #%d" % self.context.index
