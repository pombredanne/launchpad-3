# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for DistroSeriesDifferences."""

__metaclass__ = type
__all__ = [
    'DistroSeriesDifferenceView',
    ]

from zope.app.form.browser.itemswidgets import RadioWidget
from zope.interface import (
    implements,
    Interface,
    )
from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad.webapp import LaunchpadFormView
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.launchpadform import custom_widget
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.services.comments.interfaces.conversation import (
    IComment,
    IConversation,
    )


class IDistroSeriesDifferenceForm(Interface):
    """An interface used in the browser only for displaying form elements."""
    blacklist_options = Choice(vocabulary=SimpleVocabulary((
        SimpleTerm('NONE', 'NONE', 'No'),
        SimpleTerm(
            DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS,
            DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS.name,
            'All versions'),
        SimpleTerm(
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT.name,
            'This version'),
        )))


class DistroSeriesDifferenceView(LaunchpadFormView):

    implements(IConversation)
    schema = IDistroSeriesDifferenceForm
    custom_widget('blacklist_options', RadioWidget)

    @property
    def initial_values(self):
        return dict(blacklist_options='NONE')

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
        return [
            DistroSeriesDifferenceDisplayComment(comment) for
                comment in self.context.getComments()]

    @property
    def show_blacklist_options(self):
        """Only show the options if an editor requests via JS."""
        return self.request.is_ajax and check_permission(
            'launchpad.Edit', self.context)


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
