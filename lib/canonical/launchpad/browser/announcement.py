# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Announcement views."""

__metaclass__ = type

__all__ = [
    'HasAnnouncementsView',
    'AnnouncementAddView',
    'AnnouncementRetargetView',
    'AnnouncementPublishView',
    'AnnouncementRetractView',
    'AnnouncementDeleteView',
    'AnnouncementEditView',
    'AnnouncementContextMenu',
    'AnnouncementSHP',
    ]

import cgi

from zope.interface import Interface

from zope.schema import Choice, TextLine

from canonical.cachedproperty import cachedproperty
from canonical.config import config

from canonical.launchpad.interfaces import (
    IAnnouncement, IAnnouncementSet, IHasAnnouncements, ILaunchpadRoot)

from canonical.launchpad import _
from canonical.launchpad.fields import AnnouncementDate, Summary, Title
from canonical.launchpad.interfaces.validation import valid_webref

from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, custom_widget,
    enabled_with_permission, LaunchpadView, LaunchpadFormView, Link
    )
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.launchpad.browser.launchpad import (
    StructuralHeaderPresentation)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.url import urlappend

from canonical.widgets import AnnouncementDateWidget


class AnnouncementContextMenu(ContextMenu):

    usedfor = IAnnouncement
    links = ['edit', 'retarget', 'retract']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Modify announcement'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def retarget(self):
        text = 'Move to another project'
        return Link('+retarget', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def retract(self):
        text = 'Retract announcement'
        return Link('+retract', text, icon='edit')


class AnnouncementSHP(StructuralHeaderPresentation):

    def getIntroHeading(self):
        return "News for %s" % cgi.escape(self.context.target.displayname)

    def getMainHeading(self):
        return self.context.title


class AddAnnouncementForm(Interface):
    """Form definition for the view which creates new Announcements."""

    title = Title(title=_('Headline'), required=True)
    summary = Summary(title=_('Summary'), required=True)
    url = TextLine(title=_('URL'), required=False, constraint=valid_webref,
        description=_("The web location of your announcement."))
    publication_date = AnnouncementDate(title=_('Date'), required=True)


class AnnouncementAddView(LaunchpadFormView):
    """A view for creating a new Announcement."""

    schema = AddAnnouncementForm
    label = "Make an announcement"

    custom_widget('publication_date', AnnouncementDateWidget)

    def validate(self, data):
        if not self.isBetaUser:
            self.addError(
                'This capability is only available to beta testers.')

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
        self.next_url = canonical_url(self.context)

    @property
    def action_url(self):
        return "%s/+announce" % canonical_url(self.context)


class AnnouncementEditView(LaunchpadFormView):
    """A view which allows you to edit the announcement."""

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
        self.context.modify(title=data.get('title'),
                            summary=data.get('summary'),
                            url=data.get('url'))
        self.next_url = canonical_url(self.context.target)+'/+announcements'

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context.target)+'/+announcements'


class AnnouncementRetargetForm(Interface):
    """Form that requires the user to choose a pillar for the Announcement."""

    target = Choice(
        title=_("For"),
        description=_("The project where this announcement is being made."),
        required=True, vocabulary='DistributionOrProductOrProject')


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
        self.context.retarget(target)
        self.next_url = canonical_url(self.context.target)+'/+announcements'

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context.target)+'/+announcements'


class AnnouncementPublishView(LaunchpadFormView):

    schema = AddAnnouncementForm
    field_names = ['publication_date']
    label = _('Publish this announcement')

    custom_widget('publication_date', AnnouncementDateWidget)

    @action(_('Publish'), name='publish')
    def publish_action(self, action, data):
        publication_date = data['publication_date']
        self.context.set_publication_date(publication_date)
        self.next_url = canonical_url(self.context.target)+'/+announcements'

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context.target)+'/+announcements'


class AnnouncementRetractView(LaunchpadFormView):

    schema = IAnnouncement
    label = _('Retract this announcement')

    @action(_('Retract'), name='retract')
    def retract_action(self, action, data):
        self.context.retract()
        self.next_url = canonical_url(self.context.target)+'/+announcements'

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context.target)+'/+announcements'


class AnnouncementDeleteView(LaunchpadFormView):

    schema = IAnnouncement
    label = _('Delete this announcement')

    @action(_("Cancel"), name="cancel", validator='validate_cancel')
    def action_cancel(self, action, data):
        self.next_url = canonical_url(self.context.target)+'/+announcements'

    @action(_("Delete"), name="delete", validator='validate_cancel')
    def action_delete(self, action, data):
        self.context.destroySelf()
        self.next_url = canonical_url(self.context.target)+'/+announcements'


class HasAnnouncementsView(LaunchpadView):
    """A view class for pillars which have announcements."""

    @cachedproperty
    def feed_url(self):
        base_url = allvhosts.configs['feeds'].rooturl
        if IAnnouncementSet.providedBy(self.context):
            return urlappend(base_url, 'announcements.atom')
        elif ILaunchpadRoot.providedBy(self.context):
            return urlappend(base_url, 'announcements.atom')
        elif IHasAnnouncements.providedBy(self.context):
            return urlappend(canonical_url(self.context, rootsite='feeds'),
                             'announcements.atom')
        else:
            raise AssertionError, 'Unknown feed source'

    @cachedproperty
    def announcements(self):
        published_only = not check_permission('launchpad.Edit', self.context)
        return self.context.announcements(
                    limit=None, published_only=published_only)

    @cachedproperty
    def latest_announcements(self):
        published_only = not check_permission('launchpad.Edit', self.context)
        return self.context.announcements(
                    limit=5, published_only=published_only)

    @cachedproperty
    def announcement_nav(self):
        return BatchNavigator(
            self.announcements, self.request,
            size=config.launchpad.default_batch_size)

