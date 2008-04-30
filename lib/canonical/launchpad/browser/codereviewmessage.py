__metaclass__ = type

__all__ = [
    'CodeReviewMessageAddView', 
    'CodeReviewMessageView',
    ]


from canonical.launchpad.interfaces import ICodeReviewMessage
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView,
    LaunchpadView)


class CodeReviewMessageView(LaunchpadView):
    """Standard view of a CodeReviewMessage"""

    @property
    def reply_link(self):
        return canonical_url(self.context, view_name='+reply')


class CodeReviewMessageAddView(LaunchpadView): #LaunchpadFormView):

    #schema = ICodeReviewMessage
    # fields = ['message', 'vote', 'vote_reason']
    
    #@action('Add')
    #def add_action(self, action, data):
    #    """Create the comment..."""
    pass
        
