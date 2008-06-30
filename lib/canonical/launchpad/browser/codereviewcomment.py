__metaclass__ = type

__all__ = [
    'CodeReviewCommentAddView',
    'CodeReviewCommentContextMenu',
    'CodeReviewCommentSummary',
    ]

from zope.interface import Interface
from zope.schema import Choice, Text, TextLine

from canonical.cachedproperty import cachedproperty

from canonical.launchpad import _
from canonical.launchpad.fields import Title
from canonical.launchpad.interfaces import (
    CodeReviewVote, ICodeReviewComment)
from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, enabled_with_permission,
    LaunchpadFormView, LaunchpadView, Link)


class CodeReviewCommentContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = ICodeReviewComment
    links = ['reply']

    @enabled_with_permission('launchpad.AnyPerson')
    def reply(self):
        return Link('+reply', 'Reply', icon='add')


class CodeReviewCommentSummary(LaunchpadView):
    """Standard view of a CodeReviewComment"""
    __used_for__ = ICodeReviewComment

    # How many lines do we show in the main view?
    SHORT_MESSAGE_LENGTH = 4

    @cachedproperty
    def _comment_lines(self):
        return self.context.message.text_contents.splitlines()

    @property
    def is_long_message(self):
        return len(self._comment_lines) > self.SHORT_MESSAGE_LENGTH

    @property
    def message_summary(self):
        return '\n'.join(self._comment_lines[:self.SHORT_MESSAGE_LENGTH])


class IEditCodeReviewComment(Interface):
    """Interface for use as a schema for CodeReviewComment forms."""

    subject = Title(title=_('Subject'), required=False)

    comment = Text(title=_('Comment'), required=False)

    vote = Choice(
        title=_('Vote'), required=False, vocabulary=CodeReviewVote)

    vote_tag = TextLine(title=_('Tag'), required=False)


class CodeReviewCommentAddView(LaunchpadFormView):
    """View for adding a CodeReviewComment."""

    schema = IEditCodeReviewComment

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

    @property
    def reply_to(self):
        """The comment being replied to, or None."""
        if self.is_reply:
            return self.context
        else:
            return None

    @action('Add')
    def add_action(self, action, data):
        """Create the comment..."""
        comment = self.branch_merge_proposal.createComment(
            self.user, data['subject'], data['comment'], data['vote'],
            data['vote_tag'], self.reply_to)
        # Always take the user back to the merge proposal itself.
        self.next_url = canonical_url(self.branch_merge_proposal)

    @property
    def cancel_url(self):
        return canonical_url(self.context)
