__metaclass__ = type

__all__ = [
    'CodeReviewCommentAddView',
    'CodeReviewCommentView',
    'CodeReviewCommentSummary',
    ]

from zope.interface import Interface
from zope.schema import Choice, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import Title
from canonical.launchpad.interfaces import (
    CodeReviewVote, ICodeReviewComment)
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)


class CodeReviewCommentSummary(LaunchpadView):
    """Standard view of a CodeReviewComment"""
    __used_for__ = ICodeReviewComment

    @property
    def first_line(self):
        """Return the first line in the message.

        A trailing elipsis is added for messages with more than one line."""
        lines = self.context.message.text_contents.splitlines()
        if len(lines) == 0:
            return ''
        elif len(lines) == 1:
            return lines[0]
        else:
            return lines[0].rstrip('.') + '...'


class CodeReviewCommentView(LaunchpadView):
    """Standard view of a CodeReviewComment"""
    __used_for__ = ICodeReviewComment

    @property
    def reply_link(self):
        """Location of the page for replying to this comment."""
        return canonical_url(self.context, view_name='+reply')


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
        self.next_url = canonical_url(comment)

    @property
    def cancel_url(self):
        return canonical_url(self.context)
