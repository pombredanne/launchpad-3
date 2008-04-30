__metaclass__ = type

__all__ = [
    'CodeReviewMessageView',
    ]


from canonical.launchpad.interfaces import ICodeReviewMessage
from canonical.launchpad.webapp import (
    LaunchpadView)


class CodeReviewMessageView(LaunchpadView):
    """Standard view of a CodeReviewMessage"""
