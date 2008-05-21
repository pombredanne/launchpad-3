__metaclass__ = type

__all__ = [
    'CodeReviewMessageAddView',
    'CodeReviewMessageView',
    'CodeReviewMessageSummary',
    ]

from zope.interface import Interface
from zope.schema import Choice, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    CodeReviewVote, ICodeReviewMessage)
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)


class CodeReviewMessageSummary(LaunchpadView):
    """Standard view of a CodeReviewMessage"""
    __used_for__ = ICodeReviewMessage

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


class CodeReviewMessageView(LaunchpadView):
    """Standard view of a CodeReviewMessage"""
    __used_for__ = ICodeReviewMessage

    @property
    def reply_link(self):
        """Location of the page for replying to this message."""
        return canonical_url(self.context, view_name='+reply')


class IEditCodeReviewMessage(Interface):
    """Interface for use as a schema for CodeReviewMessage forms."""

    vote = Choice(
        title=_('Vote'), required=False, vocabulary=CodeReviewVote)

    subject = TextLine(
        title=_('Subject'), required=False, description=_(
        "This will be rendered as help text"))

    comment = Text(
        title=_('Comment'), required=False, description=_(
        "This will be rendered as help text"))


class CodeReviewMessageAddView(LaunchpadFormView):
    """View for adding a CodeReviewMessage."""

    schema = IEditCodeReviewMessage

    @property
    def is_reply(self):
        """True if this message is a reply to another message, else False."""
        return ICodeReviewMessage.providedBy(self.context)

    @property
    def branch_merge_proposal(self):
        """The BranchMergeProposal being commented on."""
        if self.is_reply:
            return self.context.branch_merge_proposal
        else:
            return self.context

    @property
    def reply_to(self):
        """The message being replied to, or None."""
        if self.is_reply:
            return self.context
        else:
            return None

    @action('Add')
    def add_action(self, action, data):
        """Create the comment..."""
        message = self.branch_merge_proposal.createMessage(
            self.user, data['subject'], data['comment'], data['vote'],
            self.reply_to)
        self.next_url = canonical_url(message)

    @property
    def cancel_url(self):
        return canonical_url(self.context)
