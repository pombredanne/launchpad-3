__metaclass__ = type

__all__ = [
    'CodeReviewMessageAddView',
    'CodeReviewMessageView',
    ]

from zope.interface import Interface
from zope.schema import Text, Choice

from canonical.launchpad import _
from canonical.launchpad.interfaces import CodeReviewVote, ICodeReviewMessage
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView,
    LaunchpadView)


class CodeReviewMessageView(LaunchpadView):
    """Standard view of a CodeReviewMessage"""

    @property
    def reply_link(self):
        return canonical_url(self.context, view_name='+reply')


class IEditCodeReviewMessage(Interface):
    subject = Text(
        title=_('Subject'), required=False, description=_(
        "This will be rendered as help text"))

    comment = Text(
        title=_('Comment'), required=False, description=_(
        "This will be rendered as help text"))

    vote = Choice(
        title=_('Vote'), required=False, vocabulary=CodeReviewVote)


class CodeReviewMessageAddView(LaunchpadFormView):

    schema = IEditCodeReviewMessage

    @action('Add')
    def add_action(self, action, data):
        """Create the comment..."""
        message = self.context.branch_merge_proposal.createMessage(
            self.user, data['subject'], data['comment'], data['vote'],
            self.context)
        self.next_url = canonical_url(message)
