# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views for IBugLinkTarget."""

__metaclass__ = type

__all__ = [
    'BugLinkView',
    'BugLinksPortlet',
    'BugsUnlinkView',
    ]

from zope.event import notify
from zope.interface import implements, Interface, providedBy
from zope.schema import Choice, Set
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.security.interfaces import Unauthorized

from canonical.launchpad import _
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.fields import BugField
from canonical.launchpad.helpers import check_permission
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView)
from canonical.launchpad.webapp.snapshot import Snapshot

from canonical.widgets import LabeledMultiCheckBoxWidget

class IBugLinkForm(Interface):
    """Schema for the unlink bugs form."""

    bug = BugField(
        title=_('Bug ID'), required=True,
        description=_("Enter the Malone bug ID or nickname that "
                      "you want to link to."))


class BugLinkView(LaunchpadFormView):
    """This view is used to link bugs to any IBugLinkTarget."""

    label = _('Link to bug report')

    schema = IBugLinkForm

    focused_element_id = 'bug'

    @action(_('Link'))
    def linkBug(self, action, data):
        """Link to the requested bug. Publish an SQLObjectModifiedEvent and
        display a notification on the ticket page.
        """
        response = self.request.response
        target_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        bug = data['bug']
        try:
            self.context.linkBug(bug)
        except Unauthorized:
            # XXX flacoste 2006-08-23 Use proper _() once bug 57470 is fixed.
            self.setFieldError(
                'bug',
                'You are not allowed to link to private bug #%d.'% bug.id)
            return
        bug_props = {'bugid': bug.id, 'title': bug.title}
        # XXX flacoste 2006-08-11 Reenable I18N once
        # bug 54987 is fixed. (Using MessageId with addNotification is broken)
        response.addNotification(
            u'Added link to bug #%(bugid)s: '
            u'\N{left double quotation mark}%(title)s'
            u'\N{right double quotation mark}.' % bug_props)
        notify(SQLObjectModifiedEvent(
            self.context, target_unmodified, ['bugs']))
        self.next_url = canonical_url(self.context)


class BugLinksPortlet:
    """View for the Related Bugs portlet."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def buglinks(self):
        """Return a list of dict with bug and title keys for the linked bugs.
        It makes the Right Thing(tm) with private bug.
        """
        links = []
        for bug in self.context.bugs:
            try:
                links.append({'bug': bug, 'title': bug.title})
            except Unauthorized:
                links.append({'bug': bug, 'title': _('private bug')})
        return links


class BugLinksVocabularyFactory(object):
    """IContextSourceBinder that creates a vocabulary of the linked bugs on
    the IBugLinkTarget.
    """

    implements(IContextSourceBinder)

    def __call__(self, context):
        """See IContextSourceBinder."""
        terms = []
        for bug in context.bugs:
            try:
                title = _(
                    '#${bugid}: ${title}',
                    mapping={'bugid': bug.id, 'title': bug.title})
                terms.append(SimpleTerm(bug, bug.id, title))
            except Unauthorized:
                pass
        return SimpleVocabulary(terms)


class IUnlinkBugsForm(Interface):
    """Schema for the unlink bugs form."""

    bugs = Set(title=_('Bug Links:'), required=True,
               value_type=Choice(source=BugLinksVocabularyFactory()),
               description=_('Select the bug links that you want to remove.'))


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
            try:
                self.context.unlinkBug(bug)
                # XXX flacoste 2006-08-11 Reenable I18N once
                # bug 54987 is fixed. (Using MessageId with addNotification is
                # broken)
                response.addNotification('Removed link to bug #%d.' % bug.id)
            except Unauthorized:
                response.addErrorNotification(
                    'Cannot remove link to private bug #%d.' % bug.id)
        notify(SQLObjectModifiedEvent(
            self.context, target_unmodified, ['bugs']))
        self.next_url = canonical_url(self.context)

    def bugsWithPermission(self):
        """Return the bugs that the user has permission to remove. This
        exclude private bugs to which the user doesn't have any permission.
        """
        return [bug for bug in self.context.bugs
                if check_permission('launchpad.View', bug)]

