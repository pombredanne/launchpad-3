# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views for IBugLinkTarget."""

__metaclass__ = type

__all__ = [
    'BugLinkView',
    'BugLinksListingView',
    'BugsUnlinkView',
    ]

from zope.event import notify
from zope.interface import providedBy
from zope.security.interfaces import Unauthorized

from canonical.launchpad import _
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.interfaces import (IBugLinkForm, IUnlinkBugsForm)

from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView)
from canonical.launchpad.webapp.snapshot import Snapshot
from canonical.launchpad.webapp.authorization import check_permission

from canonical.widgets import LabeledMultiCheckBoxWidget


class BugLinkView(LaunchpadFormView):
    """This view is used to link bugs to any IBugLinkTarget."""

    label = _('Link to bug report')

    schema = IBugLinkForm

    focused_element_id = 'bug'

    @action(_('Link'))
    def linkBug(self, action, data):
        """Link to the requested bug. Publish an SQLObjectModifiedEvent and
        display a notification.
        """
        response = self.request.response
        target_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        bug = data['bug']
        try:
            self.context.linkBug(bug)
        except Unauthorized:
            # XXX flacoste 2006-08-23: Use proper _() once bug 57470 is fixed.
            self.setFieldError(
                'bug',
                'You are not allowed to link to private bug #%d.'% bug.id)
            return
        bug_props = {'bugid': bug.id, 'title': bug.title}
        response.addNotification(
            _(u'Added link to bug #$bugid: '
              u'\N{left double quotation mark}$title'
              u'\N{right double quotation mark}.', mapping=bug_props))
        notify(SQLObjectModifiedEvent(
            self.context, target_unmodified, ['bugs']))
        self.next_url = canonical_url(self.context)


class BugLinksListingView:
    """View for displaying buglinks."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def buglinks(self):
        """Return a list of dict with bug, title and can_see_bug keys
        for the linked bugs. It makes the Right Thing(tm) with private bug.
        """
        links = []
        for bug in self.context.bugs:
            try:
                links.append(
                    {'bug': bug, 'title': bug.title, 'can_view_bug': True})
            except Unauthorized:
                links.append(
                    {'bug': bug, 'title': _('private bug'),
                     'can_view_bug': False})
        return links


class BugsUnlinkView(LaunchpadFormView):
    """This view is used to remove bug links from any IBugLinkTarget."""

    label = _('Remove links to bug reports')

    schema = IUnlinkBugsForm
    custom_widget('bugs', LabeledMultiCheckBoxWidget)

    @action(_('Remove'))
    def unlinkBugs(self, action, data):
        response = self.request.response
        target_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        for bug in data['bugs']:
            replacements = {'bugid': bug.id}
            try:
                self.context.unlinkBug(bug)
                response.addNotification(
                    _('Removed link to bug #$bugid.', mapping=replacements))
            except Unauthorized:
                response.addErrorNotification(
                    _('Cannot remove link to private bug #$bugid.',
                      mapping=replacements))
        notify(SQLObjectModifiedEvent(
            self.context, target_unmodified, ['bugs']))
        self.next_url = canonical_url(self.context)

    def bugsWithPermission(self):
        """Return the bugs that the user has permission to remove. This
        exclude private bugs to which the user doesn't have any permission.
        """
        return [bug for bug in self.context.bugs
                if check_permission('launchpad.View', bug)]

