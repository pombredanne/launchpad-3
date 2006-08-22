# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket views."""

__metaclass__ = type

__all__ = [
    'TicketSetNavigation',
    'TicketView',
    'TicketAddView',
    'TicketBugLinkView',
    'TicketBugsUnlinkView',
    'TicketContextMenu',
    'TicketEditView',
    'TicketMakeBugView',
    'TicketSetContextMenu'
    ]

from zope.component import getUtility
from zope.event import notify
from zope.interface import providedBy
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.launchpad.interfaces import (
    ILaunchBag, ITicket, ITicketSet, CreateBugParams)
from canonical.launchpad import _
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.buglinktarget import (
    BugLinkView, BugsUnlinkView)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import (
    ContextMenu, Link, canonical_url, enabled_with_permission, Navigation,
    GeneralFormView, LaunchpadView)
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.webapp.snapshot import Snapshot

class TicketSetNavigation(Navigation):

    usedfor = ITicketSet


class TicketView(LaunchpadView):

    __used_for__ = ITicket

    def initialize(self):
        self.notices = []
        self.is_owner = self.user == self.context.owner

        if not self.user or self.request.method != "POST":
            # No post, nothing to do
            return

        # XXX: all this crap should be moved to a method; having it here
        # means that any template using TicketView (including
        # -listing-detailed, which many other pages do) have to go
        # through millions of queries.
        #   -- kiko, 2006-03-17

        ticket_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        modified_fields = set()

        form = self.request.form
        # establish if a subscription form was posted
        newsub = form.get('subscribe', None)
        if newsub is not None:
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this request.")
                modified_fields.add('subscribers')
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this request.")
                modified_fields.add('subscribers')

        # establish if the user is trying to reject the ticket
        reject = form.get('reject', None)
        if reject is not None:
            if self.context.reject(self.user):
                self.notices.append("You have rejected this request.")
                modified_fields.add('status')

        # establish if the user is trying to reopen the ticket
        reopen = form.get('reopen', None)
        if reopen is not None:
            if self.context.reopen(self.user):
                self.notices.append("You have reopened this request.")
                modified_fields.add('status')

        if len(modified_fields) > 0:
            notify(SQLObjectModifiedEvent(
                self.context, ticket_unmodified, list(modified_fields)))

    @property
    def subscription(self):
        """establish if this user has a subscription"""
        if self.user is None:
            return False
        return self.context.isSubscribed(self.user)


class TicketAddView(SQLObjectAddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, title=None, description=None, owner=None):
        """Create a new Ticket."""
        ticket = self.context.newTicket(owner, title, description)
        self._nextURL = canonical_url(ticket)
        return ticket

    def nextURL(self):
        return self._nextURL


class TicketEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class TicketMakeBugView(GeneralFormView):
    """Browser class for adding a bug from a ticket."""

    def initialize(self):
        ticket = self.context
        if ticket.bugs:
            # we can't make a bug when we have linked bugs
            self.request.response.addErrorNotification(
                _('You cannot create a bug report from a support request'
                    'that already has bugs linked to it.'))
            self.request.response.redirect(canonical_url(ticket))
            return

    @property
    def initial_values(self):
        ticket = self.context
        return {'title': '',
                'description': ticket.description}

    def process_form(self):
        # Override GeneralFormView.process_form because we don't
        # want form validation when the cancel button is clicked
        ticket = self.context
        if self.request.method == 'GET':
            self.process_status = ''
            return ''
        if 'cancel' in self.request.form:
            self.request.response.redirect(canonical_url(ticket))
            return ''
        return GeneralFormView.process_form(self)

    def process(self, title, description):
        ticket = self.context

        unmodifed_ticket = Snapshot(ticket, providing=providedBy(ticket))
        params = CreateBugParams(
            owner=self.user, title=title, comment=description)
        bug = ticket.target.createBug(params)
        ticket.linkBug(bug)
        bug.subscribe(ticket.owner)
        bug_added_event = SQLObjectModifiedEvent(
            ticket, unmodifed_ticket, ['bugs'])
        notify(bug_added_event)
        self.request.response.addNotification(
            _('Thank you! Bug #%d created.') % bug.id)
        self._nextURL = canonical_url(bug)

    def submitted(self):
        return 'create' in self.request


class TicketBugLinkView(BugLinkView):
    """Customize BugLinkView to use a different template for ITicket."""

    label = _('Link support request to a bug report')

    template = ViewPageTemplateFile('../templates/ticket-linkbug.pt')


class TicketBugsUnlinkView(BugsUnlinkView):
    """Customize BugsUnlinkView to use a different template for ITicket."""

    template = ViewPageTemplateFile('../templates/ticket-unlinkbugs.pt')


class TicketContextMenu(ContextMenu):

    usedfor = ITicket
    links = [
        'edit',
        'editsourcepackage',
        'reject',
        'reopen',
        'history',
        'subscription',
        'linkbug',
        'unlinkbug',
        'makebug',
        'administer',
        ]

    def initialize(self):
        self.is_not_resolved = not self.context.is_resolved
        self.has_bugs = bool(self.context.bugs)

    def edit(self):
        text = 'Edit Request'
        return Link('+edit', text, icon='edit')

    def editsourcepackage(self):
        enabled = self.context.distribution is not None
        text = 'Change Source Package'
        return Link('+sourcepackage', text, icon='edit', enabled=enabled)

    def reject(self):
        text = 'Reject Request'
        return Link('+reject', text, icon='edit',
                    enabled=self.context.can_be_rejected)

    def reopen(self):
        text = 'Reopen Request'
        enabled = (
            self.context.can_be_reopened and self.user == self.context.owner)
        return Link('+reopen', text, icon='edit', enabled=enabled)

    def history(self):
        text = 'History'
        return Link('+history', text, icon='list',
                    enabled=bool(self.context.reopenings))

    def subscription(self):
        if self.user is not None and self.context.isSubscribed(self.user):
            text = 'Unsubscribe'
            icon = 'edit'
        else:
            text = 'Subscribe'
            icon = 'mail'
        return Link('+subscribe', text, icon=icon)

    def linkbug(self):
        text = 'Link Existing Bug'
        return Link('+linkbug', text, icon='add')

    def unlinkbug(self):
        text = 'Remove Bug Link'
        return Link('+unlinkbug', text, icon='edit', enabled=self.has_bugs)

    def makebug(self):
        text = 'Create Bug Report'
        summary = 'Create a bug report from this support request.'
        return Link('+makebug', text, summary, icon='add',
                    enabled=not self.has_bugs)

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


class TicketSetContextMenu(ContextMenu):

    usedfor = ITicketSet
    links = ['findproduct', 'finddistro']

    def findproduct(self):
        text = 'Find Upstream Product'
        return Link('/products', text, icon='search')

    def finddistro(self):
        text = 'Find Distribution'
        return Link('/distros', text, icon='search')

