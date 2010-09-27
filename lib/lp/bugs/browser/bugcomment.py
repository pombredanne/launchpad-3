# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug comment browser view classes."""

__metaclass__ = type
__all__ = [
    'BugComment',
    'BugCommentView',
    'BugCommentBoxView',
    'BugCommentBoxExpandedReplyView',
    'BugCommentXHTMLRepresentation',
    'BugCommentBreadcrumb',
    'build_comments_from_chunks',
    ]

from datetime import (
    datetime,
    timedelta,
    )

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
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.bugs.interfaces.bugmessage import (
    IBugComment,
    IBugMessageSet,
    )
from lp.registry.interfaces.person import IPersonSet


def build_comments_from_chunks(chunks, bugtask, truncate=False):
    """Build BugComments from MessageChunks."""
    comments = {}
    index = 0
    for chunk in chunks:
        message_id = chunk.message.id
        bug_comment = comments.get(message_id)
        if bug_comment is None:
            bug_comment = BugComment(
                index, chunk.message, bugtask)
            comments[message_id] = bug_comment
            index += 1
        bug_comment.chunks.append(chunk)

    # Set up the bug watch for all the imported comments. We do it
    # outside the for loop to avoid issuing one db query per comment.
    imported_bug_messages = getUtility(IBugMessageSet).getImportedBugMessages(
        bugtask.bug)
    for bug_message in imported_bug_messages:
        message_id = bug_message.message.id
        comments[message_id].bugwatch = bug_message.bugwatch
        comments[message_id].synchronized = (
            bug_message.remote_comment_id is not None)

    for bug_message in bugtask.bug.bug_messages:
        comment = comments.get(bug_message.messageID, None)
        # XXX intellectronica 2009-04-22, bug=365092: Currently, there are
        # some bug messages for which no chunks exist in the DB, so we need to
        # make sure that we skip them, since the corresponding message wont
        # have been added to the comments dictionary in the section above.
        if comment is not None:
            comment.visible = bug_message.visible

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

    def __init__(self, index, message, bugtask, activity=None):
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

    @property
    def show_for_admin(self):
        """Show hidden comments for Launchpad admins.

        This is used in templates to add a class to hidden
        comments to enable display for admins, so the admin
        can see the comment even after it is hidden.
        """
        user = getUtility(ILaunchBag).user
        is_admin = check_permission('launchpad.Admin', user)
        if is_admin and not self.visible:
            return True
        else:
            return False

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
        if len(self.activity) > 0 or self.bugwatch:
            return True
        else:
            return False

    @property
    def rendered_cache_time(self):
        """The number of seconds we can cache the rendered comment for.

        Bug comments are cached with 'authenticated' visibility, so
        should contain no information hidden from some users. We use
        'authenticated' rather than 'public' as email addresses are
        obfuscated for unauthenticated users.
        """
        now = datetime.now(tz=utc)
        # The major factor in how long we can cache a bug comment is
        # the timestamp. The rendering of the timestamp changes every
        # minute for the first hour because we say '7 minutes ago'.
        if self.datecreated > now - timedelta(hours=1):
            return 60

        # Don't cache for long if we are waiting for synchronization.
        elif self.bugwatch and not self.synchronized:
            return 5*60

        # For the rest of the first day, the rendering changes every
        # hour. '4 hours ago'. Expire in 15 minutes so the timestamp
        # is at most 15 minutes out of date.
        elif self.datecreated > now - timedelta(days=1):
            return 15*60

        # Otherwise, cache away. Lets cache for 6 hours. We don't want
        # to cache for too long as there are still things that can
        # become stale - eg. if a bug attachment has been deleted we
        # should stop rendering the link.
        else:
            return 6*60*60


class BugCommentView(LaunchpadView):
    """View for a single bug comment."""

    def __init__(self, context, request):
        # We use the current bug task as the context in order to get the
        # menu and portlets working.
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.comment = context

    def page_title(self):
        return 'Comment %d for bug %d' % (
            self.comment.index, self.context.bug.id)


class BugCommentBoxViewMixin:
    """A class which provides proxied Librarian URLs for bug attachments."""

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
