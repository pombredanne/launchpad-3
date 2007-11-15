# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Announcement views."""

__metaclass__ = type

__all__ = [
    'HasAnnouncementsView',
    'AnnouncementAddView',
    'AnnouncementRetargetView',
    'AnnouncementPublishView',
    'AnnouncementRetractView',
    'AnnouncementEditView',
    'AnnouncementContextMenu',
    'AnnouncementSHP',
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
    AddAnnouncementForm,
    AnnouncementRetargetForm,
    IDistribution,
    ILaunchBag,
    IAnnouncement,
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


class AnnouncementContextMenu(ContextMenu):

    usedfor = IAnnouncement
    links = ['edit', 'retarget']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Modify announcement'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def retarget(self):
        text = 'Retarget'
        return Link('+retarget', text, icon='edit')


class AnnouncementSHP(StructuralHeaderPresentation):

    def getIntroHeading(self):
        return "News for %s" % cgi.escape(self.context.target.title)

    def getMainHeading(self):
        return self.context.title


class AnnouncementAddView(LaunchpadFormView):
    """An abstract view for creating a new Announcement."""

    schema = AddAnnouncementForm
    label = "Make an announcement"

    custom_widget('publication_date', AnnouncementDateWidget)

    @action(_('Make announcement'), name='announce')
    def announce_action(self, action, data):
        """Registers a new announcement."""
        announcement = self.context.announce(
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
        return self._next_url


class AnnouncementEditView(LaunchpadFormView):

    schema = AddAnnouncementForm
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

    def validate_cancel(self, action, data):
        """Noop validation in case we cancel"""
        return []

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    @property
    def next_url(self):
        return self._nextURL


class AnnouncementRetargetView(LaunchpadFormView):

    schema = AnnouncementRetargetForm
    field_names = ['target']
    label = _('Move this announcement to a different project')

    def validate(self, data):
        """Ensure that the person can publish announcement at the new
        target.
        """

        target = data.get('target')

        if target is None:
            self.setFieldError('target',
                "There is no project with the name '%s'. "
                "Please check that name and try again." %
                cgi.escape(self.request.form.get("field.target")))
            return

        if not check_permission('launchpad.Edit', target):
            self.setFieldError('target',
                "You don't have permission to make announcements for "
                "%s. Please check that name and try again." %
                target.displayname)
            return

    @action(_('Retarget'), name='retarget')
    def retarget_action(self, action, data):
        target = data.get('target')
        product = project = distribution = None
        if IProduct.providedBy(target):
            self.context.product = target
            self.context.project = None
            self.context.distribution = None
        elif IDistribution.providedBy(target):
            self.context.distribution = target
            self.context.product = None
            self.context.project = None
        elif IProject.providedBy(target):
            self.context.project = target
            self.context.distribution = None
            self.context.project = None
        else:
            raise AssertionError, 'Unknown target'
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    def validate_cancel(self, action, data):
        """Noop validation in case we cancel"""
        return []

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    @property
    def next_url(self):
        return self._nextURL


class AnnouncementPublishView(LaunchpadFormView):

    schema = IAnnouncement
    field_names = ['publication_date']
    label = _('Publish this announcement')

    def validate(self, data):
        """Make sure that the date proposed for publication is reasonable."""

        target = data.get('target')

        if target is None:
            self.setFieldError('target',
                "There is no project with the name '%s'. "
                "Please check that name and try again." %
                cgi.escape(self.request.form.get("field.target")))
            return

    @action(_('Publish'), name='publish')
    def publish_action(self, action, data):
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    def validate_cancel(self, action, data):
        """Noop validation in case we cancel"""
        return []

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    @property
    def next_url(self):
        return self._nextURL


class AnnouncementRetractView(LaunchpadFormView):

    schema = IAnnouncement
    label = _('Retract this announcement')

    @action(_('Retract'), name='retract')
    def retract_action(self, action, data):
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    def validate_cancel(self, action, data):
        """Noop validation in case we cancel"""
        return []

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self._nextURL = canonical_url(self.context.target)+'/+announcements'

    @property
    def next_url(self):
        return self._nextURL


class HasAnnouncementsView(LaunchpadView):
    """A view class for pillars which have announcements."""

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

