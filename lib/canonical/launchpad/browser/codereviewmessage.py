__metaclass__ = type

__all__ = [
    'CodeReviewMessageAddView',
    'CodeReviewMessageView',
    ]

from zope.interface import Interface
from zope.schema import Choice, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    CodeReviewVote, ICodeReviewMessage ICodeReviewMessage)
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)


class CodeReviewMessageView(LaunchpadView):
    """Standard view of a CodeReviewMessage"""
    __used_for__ = ICodeReviewMessage

    @property
    def reply_link(self):
        """Location of the page for replying to this message"""
        return canonical_url(self.context, view_name='+reply')


class IEditCodeReviewMessage(Interface):

    vote = Choice(
        title=_('Vote'), required=False, vocabulary=CodeReviewVote)

    subject = TextLine(
        title=_('Subject'), required=False, description=_(
        "This will be rendered as help text"))

    comment = Text(
        title=_('Comment'), required=False, description=_(
        "This will be rendered as help text"))


class CodeReviewMessageAddView(LaunchpadFormView):

    schema = IEditCodeReviewMessage

    @action('Add')
    def add_action(self, action, data):
        """Create the comment..."""
        message = self.context.branch_merge_proposal.createMessage(
            self.user, data['subject'], data['comment'], data['vote'],
            self.context)
        self.next_url = canonical_url(message)
