# Copyright 2007 Canonical Ltd.  All rights reserved.

"""NewsItem views."""

__metaclass__ = type

__all__ = [
    'HasNewsItemsView',
    'NewsItemAddView',
    'NewsItemContextMenu',
    'NewsItemEditView',
    'NewsItemSHP',
    ]

import cgi
from operator import attrgetter

from zope.component import getUtility
from zope.app.form.browser.itemswidgets import DropdownWidget
from zope.formlib import form
from zope.formlib.form import Fields
from zope.schema import Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad import _

from canonical.launchpad.interfaces import (
    AddNewsItemForm,
    IDistribution,
    ILaunchBag,
    INewsItem,
    IProduct,
    NotFoundError,
    )

from canonical.launchpad.webapp import (
    ContextMenu, GeneralFormView, LaunchpadView, LaunchpadFormView,
    Link, Navigation, action, canonical_url, enabled_with_permission,
    safe_action, stepthrough, stepto, custom_widget)
from canonical.launchpad.browser.launchpad import (
    StructuralHeaderPresentation)
from canonical.launchpad.webapp.authorization import check_permission

from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.widgets import AnnouncementDateWidget
from zope.app.form.browser import TextWidget


class NewsItemAddView(LaunchpadFormView):
    """An abstract view for creating a new NewsItem."""

    schema = AddNewsItemForm
    label = "Make an announcement"

    custom_widget('publication_date', AnnouncementDateWidget)

    @action(_('Make announcement'), name='announce')
    def announce_action(self, action, data):
        """Registers a new newsitem."""
        newsitem = self.context.announce(
            user = self.user,
            title = data.get('title'),
            summary = data.get('summary'),
            url = data.get('url'),
            publication_date = data.get('publication_date')
            )
        self._next_url = canonical_url(self.context)

    @property
    def action_url(self):
        return "%s/+announce" % canonical_url(self.context)

    @property
    def next_url(self):
        """The next URL to redirect to after creating a new specification.

        The default implementation returns a URL for the new specification
        itself. Subclasses can override this behaviour by returning an
        alternative URL.
        """
        return self._next_url


class NewsItemContextMenu(ContextMenu):

    usedfor = INewsItem
    links = ['edit', 'retarget']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Edit title and summary'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def retarget(self):
        text = 'Retarget'
        return Link('+retarget', text, icon='edit')



class NewsItemEditView(LaunchpadFormView):

    schema = AddNewsItemForm
    field_names = ['title', 'summary', 'url', ]
    label = _('Modify this announcement')

    @property
    def initial_values(self):
        return {
            'title': self.context.title,
            'summary': self.context.summary,
            'url': self.context.url,
            }

    @action(_('Modify'), name='modify')
    def modify_action(self, action, data):
        self.context.title = data.get('title')
        self.context.summary = data.get('summary')
        self.context.url = data.get('url')
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    @property
    def next_url(self):
        return self._nextURL




class NewsItemRetargetingView(LaunchpadFormView):

    schema = INewsItem
    field_names = ['target']
    label = _('Move this announcement to a different project')

    def validate(self, data):
        """Ensure that the target is valid and that there is not
        already a blueprint with the same name as this one for the
        given target.
        """

        target = data.get('target')

        if target is None:
            self.setFieldError('target',
                "There is no project with the name '%s'. "
                "Please check that name and try again." %
                cgi.escape(self.request.form.get("field.target")))
            return

    @action(_('Retarget Blueprint'), name='retarget')
    def register_action(self, action, data):
        # we need to ensure that there is not already a spec with this name
        # for this new target
        target = data['target']
        if target.getSpecification(self.context.name) is not None:
            return '%s already has a blueprint called %s' % (
                target.displayname, self.context.name)
        product = distribution = None
        if IProduct.providedBy(target):
            product = target
        elif IDistribution.providedBy(target):
            distribution = target
        else:
            raise AssertionError, 'Unknown target'
        self.context.retarget(product=product, distribution=distribution)
        self._nextURL = canonical_url(self.context)

    @property
    def next_url(self):
        return self._nextURL


class NewsItemSHP(StructuralHeaderPresentation):

    def getIntroHeading(self):
        return "News for %s" % cgi.escape(self.context.target.title)

    def getMainHeading(self):
        return self.context.title


class HasNewsItemsView(LaunchpadView):
    """A view class for pillars which have news items."""

    @property
    def announcements(self):
        return self.context.announcements(limit=None)

    @property
    def latest_announcements(self):
        return self.context.announcements(limit=5)

    def initialize(self):
        self.batchnav = BatchNavigator(
            self.announcements, self.request,
            size=config.launchpad.default_batch_size)

