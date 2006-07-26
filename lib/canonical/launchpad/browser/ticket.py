# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket views."""

__metaclass__ = type

__all__ = [
    'TicketSetNavigation',
    'TicketView',
    'TicketAddView',
    'TicketContextMenu',
    'TicketEditView',
    'TicketMakeBugView',
    'TicketSetContextMenu'
    ]

from zope.component import getUtility
from zope.event import notify
from zope.formlib import form

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import InputErrors
from zope.app.form.browser import TextWidget
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.launchpad import _
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.event import (
    SQLObjectCreatedEvent, SQLObjectModifiedEvent)
from canonical.launchpad.interfaces import (
    ILaunchBag, ITicket, ITicketSet, CreateBugParams)
from canonical.launchpad.webapp import (
    ContextMenu, Link, canonical_url, enabled_with_permission, Navigation,
    GeneralFormView, LaunchpadView)
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

        ticket_unmodified = Snapshot(self.context, providing=ITicket)
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


class TicketAddView(form.Form):
    """Multi-page add view.

    The user enters first his ticket summary and then he his shown a list
    of similar results before adding the ticket.
    """
    label = _('Make a support request')

    form_fields = form.Fields(ITicket).select('title', 'description', 'owner')
    form_fields['title'].custom_widget = CustomWidgetFactory(
        TextWidget, displayWidth=40, extra='tabindex="1"')

    search_template = ViewPageTemplateFile('../templates/ticket-add-search.pt')

    add_template = ViewPageTemplateFile('../templates/ticket-add.pt')

    template = search_template

    @form.action(_('Continue'), validator='validate_continue')
    def handle_continue(self, action, data):
        """Search for tickets similar to the entered summary."""
        self.searchResults = self.context.searchTickets(data['title'])
        return self.add_template()

    def validate_continue(self, action, data):
        """Checks that title was submitted."""
        try:
            data['title'] = self.widgets['title'].getInputValue()
        except InputErrors, error:
            return [error]
        return []

    def handle_add_error(self, action, data, errors):
        """Do the search and display the add form."""
        if 'title' not in data:
            self.status = _('You must enter a summary of your problem.')
            return self.search_template()

        self.searchResults = self.context.searchTickets(data['title'])
        return self.add_template()

    # XXX flacoste 2006/07/26 We use the method here instead of
    # using the method name 'handle_add_error' because of Zope issue 573
    # which is fixed in 3.3.0b1 and 3.2.1
    @form.action(_('Add'), failure=handle_add_error)
    def handle_add(self, action, data):
        owner = getUtility(ILaunchBag).user
        ticket = self.context.newTicket(owner, data['title'],
                                        data['description'])

        # XXX flacoste 2006/07/25 This should be moved to database code.
        notify(SQLObjectCreatedEvent(ticket))

        self.request.response.redirect(canonical_url(ticket))
        return ''


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

        unmodifed_ticket = Snapshot(ticket, providing=ITicket)
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
        return Link('+edit', text, icon='edit', enabled=self.is_not_resolved)

    def editsourcepackage(self):
        enabled = (
            self.is_not_resolved and self.context.distribution is not None)
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
            enabled = True
            icon = 'edit'
        else:
            text = 'Subscribe'
            enabled = self.is_not_resolved
            icon = 'mail'
        return Link('+subscribe', text, icon=icon, enabled=enabled)

    def linkbug(self):
        text = 'Link Existing Bug'
        return Link('+linkbug', text, icon='add', enabled=self.is_not_resolved)

    def unlinkbug(self):
        enabled = self.is_not_resolved and self.has_bugs
        text = 'Remove Bug Link'
        return Link('+unlinkbug', text, icon='edit', enabled=enabled)

    def makebug(self):
        enabled = self.is_not_resolved and not self.has_bugs
        text = 'Create Bug Report'
        summary = 'Create a bug report from this support request.'
        return Link('+makebug', text, summary, icon='add', enabled=enabled)

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

