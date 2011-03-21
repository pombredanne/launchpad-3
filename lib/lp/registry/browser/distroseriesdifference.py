# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for DistroSeriesDifferences."""

__metaclass__ = type
__all__ = [
    'CommentXHTMLRepresentation',
    'DistroSeriesDifferenceView',
    ]

from lazr.restful.interfaces import IWebServiceClientRequest
from z3c.ptcompat import ViewPageTemplateFile
from zope.app.form.browser.itemswidgets import RadioWidget
from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import (
    implements,
    Interface,
    )
from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad.webapp import (
    LaunchpadView,
    Navigation,
    stepthrough,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.launchpadform import custom_widget
from lp.app.browser.launchpadform import (
    LaunchpadFormView,
    )
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceComment,
    IDistroSeriesDifferenceCommentSource,
    )
from lp.registry.model.distroseriesdifferencecomment import (
    DistroSeriesDifferenceComment,
    )
from lp.services.comments.interfaces.conversation import (
    IComment,
    IConversation,
    )


class DistroSeriesDifferenceNavigation(Navigation):
    usedfor = IDistroSeriesDifference

    @stepthrough('comments')
    def traverse_comment(self, id_str):
        try:
            id = int(id_str)
        except ValueError:
            return None

        return getUtility(
            IDistroSeriesDifferenceCommentSource).getForDifference(
                self.context, id)


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
        """Ensure the correct radio button is checked for blacklisting."""
        blacklisted_statuses = (
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS,
            )
        if self.context.status in blacklisted_statuses:
            return dict(blacklist_options=self.context.status)

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
        comments = self.context.getComments().order_by(
            DistroSeriesDifferenceComment.id)
        return [
            DistroSeriesDifferenceDisplayComment(comment) for
                comment in comments]

    @property
    def show_edit_options(self):
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
        self.comment_author = comment.comment_author
        self.comment_date = comment.comment_date
        self.body_text = comment.body_text


class CommentXHTMLRepresentation(LaunchpadView):
    """Render individual comments when requested via the API."""
    adapts(IDistroSeriesDifferenceComment, IWebServiceClientRequest)
    implements(Interface)

    template = ViewPageTemplateFile(
        '../templates/distroseriesdifferencecomment-fragment.pt')

    @property
    def comment(self):
        return DistroSeriesDifferenceDisplayComment(self.context)
