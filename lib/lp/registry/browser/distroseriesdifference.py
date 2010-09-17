# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for DistroSeriesDifferences."""

__metaclass__ = type
__all__ = [
    'DistroSeriesDifferenceView',
    ]

from zope.interface import implements

from canonical.launchpad.webapp.publisher import LaunchpadView
from lp.services.comments.interfaces.conversation import (
    IComment,
    IConversation,
    )


class DistroSeriesDifferenceView(LaunchpadView):

    implements(IConversation)

    @property
    def binary_summaries(self):
        """Return the summary of the related binary packages."""
        source_pub = None
        if self.context.source_pub is not None:
            source_pub = self.context.source_pub
        elif self.context.parent_source_pub is not None:
            source_pub = self.context.parent_source_pub

        if source_pub is not None:
            summary = source_pub.meta_sourcepackage.summary
            if summary:
                return summary.split('\n')

        return None

    @property
    def comments(self):
        """See `IConversation`."""
        # Could use a generator here?
        return [
            DistroSeriesDifferenceDisplayComment(comment) for
                comment in self.context.getComments()]


class DistroSeriesDifferenceDisplayComment:
    """Used simply to provide `IComment` for rendering."""
    implements(IComment)

    has_body = True
    has_footer = False
    display_attachments = False
    extra_css_class = ''

    def __init__(self, comment):
        """Setup the attributes required by `IComment`."""
        self.message_body = comment.comment
        self.comment_author = comment.message.owner
        self.comment_date = comment.message.datecreated
        self.body_text = comment.comment
