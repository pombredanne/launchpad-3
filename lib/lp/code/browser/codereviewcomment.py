# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'CodeReviewCommentAddView',
    'CodeReviewCommentContextMenu',
    'CodeReviewCommentPrimaryContext',
    'CodeReviewCommentSummary',
    'CodeReviewCommentView',
    'CodeReviewDisplayComment',
    ]

from lazr.delegates import delegates
from lazr.restful.interface import copy_field
from zope.app.form.browser import (
    DropdownWidget,
    TextAreaWidget,
    )
from zope.interface import (
    implements,
    Interface,
    )
from zope.schema import Text

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.webapp import (
    canonical_url,
    ContextMenu,
    LaunchpadView,
    Link,
    )
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadFormView,
    )
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.services.comments.interfaces.conversation import IComment
from lp.services.propertycache import cachedproperty


class ICodeReviewDisplayComment(IComment, ICodeReviewComment):
    """Marker interface for displaying code review comments."""


class CodeReviewDisplayComment:
    """A code review comment or activity or both.

    The CodeReviewComment itself does not implement the IComment interface as
    this is purely a display interface, and doesn't make sense to have display
    only code in the model itself.
    """

    implements(ICodeReviewDisplayComment)

    delegates(ICodeReviewComment, 'comment')

    def __init__(self, comment, from_superseded=False):
        self.comment = comment
        self.has_body = bool(self.comment.message_body)
        self.has_footer = self.comment.vote is not None
        # The date attribute is used to sort the comments in the conversation.
        self.date = self.comment.message.datecreated
        self.from_superseded = from_superseded

    @property
    def extra_css_class(self):
        if self.from_superseded:
            return 'from-superseded'
        else:
            return ''

    @cachedproperty
    def comment_author(self):
        """The author of the comment."""
        return self.comment.message.owner

    @cachedproperty
    def has_body(self):
        """Is there body text?"""
        return bool(self.body_text)

    @cachedproperty
    def body_text(self):
        """Get the body text for the message."""
        return self.comment.message_body

    @cachedproperty
    def comment_date(self):
        """The date of the comment."""
        return self.comment.message.datecreated

    @cachedproperty
    def all_attachments(self):
        return self.comment.getAttachments()

    @cachedproperty
    def display_attachments(self):
        # Attachments to show.
        return [DiffAttachment(alias) for alias in self.all_attachments[0]]

    @cachedproperty
    def other_attachments(self):
        # Attachments to not show.
        return self.all_attachments[1]


class CodeReviewCommentPrimaryContext:
    """The primary context is the comment is that of the source branch."""

    implements(IPrimaryContext)

    def __init__(self, comment):
        self.context = IPrimaryContext(
            comment.branch_merge_proposal).context


class CodeReviewCommentContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = ICodeReviewComment
    links = ['reply']

    def reply(self):
        enabled = self.context.branch_merge_proposal.isMergable()
        return Link('+reply', 'Reply', icon='add', enabled=enabled)


class DiffAttachment:
    """An attachment that we are going to display."""

    implements(ILibraryFileAlias)

    delegates(ILibraryFileAlias, 'alias')

    def __init__(self, alias):
        self.alias = alias

    @cachedproperty
    def text(self):
        """Read the text out of the librarin."""
        self.alias.open()
        try:
            return self.alias.read(config.diff.max_read_size)
        finally:
            self.alias.close()

    @cachedproperty
    def diff_text(self):
        """Get the text and attempt to decode it."""
        try:
            diff = self.text.decode('utf-8')
        except UnicodeDecodeError:
            diff = self.text.decode('windows-1252', 'replace')
        # Strip off the trailing carriage returns.
        return diff.rstrip('\n')


class CodeReviewCommentView(LaunchpadView):
    """Standard view of a CodeReviewComment"""

    page_title = "Code review comment"

    @cachedproperty
    def comment(self):
        """The decorated code review comment."""
        return CodeReviewDisplayComment(self.context)

    # Should the comment be shown in full?
    full_comment = True
    # Show comment expanders?
    show_expanders = False


class CodeReviewCommentSummary(CodeReviewCommentView):
    """Summary view of a CodeReviewComment"""

    # How many lines do we show in the main view?
    SHORT_MESSAGE_LENGTH = 3

    # Show comment expanders?
    show_expanders = True

    # Should the comment be shown in full?
    @property
    def full_comment(self):
        """Show the full comment if it is short."""
        return not self.is_long_message

    @cachedproperty
    def _comment_lines(self):
        return self.context.message.text_contents.splitlines()

    @property
    def is_long_message(self):
        return len(self._comment_lines) > self.SHORT_MESSAGE_LENGTH

    @property
    def message_summary(self):
        """Return an elided message with the first X lines of the comment."""
        short_message = (
            '\n'.join(self._comment_lines[:self.SHORT_MESSAGE_LENGTH]))
        short_message += "..."
        return short_message


class IEditCodeReviewComment(Interface):
    """Interface for use as a schema for CodeReviewComment forms."""

    vote = copy_field(ICodeReviewComment['vote'], required=False)

    review_type = copy_field(
        ICodeReviewVoteReference['review_type'],
        description=u'Lowercase keywords describing the type of review you '
                     'are performing.')

    comment = Text(title=_('Comment'), required=False)


class CodeReviewCommentAddView(LaunchpadFormView):
    """View for adding a CodeReviewComment."""

    class MyDropWidget(DropdownWidget):
        "Override the default no-value display name to -Select-."
        _messageNoValue = 'Comment only'

    schema = IEditCodeReviewComment

    custom_widget('comment', TextAreaWidget, cssClass='codereviewcomment')
    custom_widget('vote', MyDropWidget)

    page_title = 'Reply to code review comment'

    @property
    def initial_values(self):
        """The initial values are used to populate the form fields.

        In this case, the default value of the comment should be the
        quoted comment being replied to.
        """
        if self.is_reply:
            comment = self.reply_to.as_quoted_email
        else:
            comment = ''
        return {'comment': comment}

    @property
    def is_reply(self):
        """True if this comment is a reply to another comment, else False."""
        return ICodeReviewComment.providedBy(self.context)

    @property
    def branch_merge_proposal(self):
        """The BranchMergeProposal being commented on."""
        if self.is_reply:
            return self.context.branch_merge_proposal
        else:
            return self.context

    @cachedproperty
    def reply_to(self):
        """The comment being replied to, or None."""
        if self.is_reply:
            return CodeReviewDisplayComment(self.context)
        else:
            return None

    @action('Save Comment', name='add')
    def add_action(self, action, data):
        """Create the comment..."""
        vote = data.get('vote')
        review_type = data.get('review_type')
        self.branch_merge_proposal.createComment(
            self.user, subject=None, content=data['comment'],
            parent=self.reply_to, vote=vote, review_type=review_type)

    @property
    def next_url(self):
        """Always take the user back to the merge proposal itself."""
        return canonical_url(self.branch_merge_proposal)

    cancel_url = next_url
