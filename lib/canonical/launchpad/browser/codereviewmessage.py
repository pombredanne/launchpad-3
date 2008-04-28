__metaclass__ = type

__all__ = ['CodeReviewMessageNavigation', 'CodeReviewMessageView', ]


from canonical.launchpad.interfaces import ICodeReviewMessage
from canonical.launchpad.webapp import canonical_url, Navigation, stepto


class CodeReviewMessageNavigation:

    usedfor = ICodeReviewMessage

    @stepto('+reply')
    def traverse_reply(self):
        return self.context


class CodeReviewMessageView:
    """Standard view of a CodeReviewMessage"""

    def reply_link(self):
        return canonical_url(self.context, view_name='+reply')
