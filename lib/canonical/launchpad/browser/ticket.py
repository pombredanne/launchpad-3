# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket views."""

__metaclass__ = type

__all__ = [
    'TicketAddView',
    'TicketChangeStatusView',
    'TicketContextMenu',
    'TicketEditView',
    'TicketMakeBugView',
    'TicketSetContextMenu',
    'TicketSetNavigation',
    'TicketRejectView',
    'TicketSubscriptionView',
    'TicketWorkflowView',
    ]

from zope.app.form.browser import TextWidget, TextAreaWidget
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.event import notify
from zope.formlib import form
from zope.interface import providedBy

from canonical.launchpad import _
from canonical.launchpad.event import (
    SQLObjectCreatedEvent, SQLObjectModifiedEvent)
from canonical.launchpad.interfaces import (
    ITicket, ITicketChangeStatusForm, ITicketSet, CreateBugParams)
from canonical.launchpad.webapp import (
    ContextMenu, Link, canonical_url, enabled_with_permission, Navigation,
    GeneralFormView, LaunchpadView, action, LaunchpadFormView,
    LaunchpadEditFormView, custom_widget)
from canonical.launchpad.webapp.snapshot import Snapshot


class TicketSetNavigation(Navigation):

    usedfor = ITicketSet


class TicketWorkflowView(LaunchpadView):
    """View managing the ticket workflow action, i.e. action changing
    its status.
    """

    def initialize(self):
        self.is_owner = self.user == self.context.owner

        if not self.user or self.request.method != "POST":
            # No post, nothing to do
            return

        ticket_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        modified_fields = set()

        form = self.request.form
        response = self.request.response

        # establish if the user is trying to reject the ticket
        reject = form.get('reject', None)
        if reject is not None:
            if self.context.reject(self.user):
                response.addNotification(("You have rejected this request."))
                modified_fields.add('status')

        # establish if the user is trying to reopen the ticket
        reopen = form.get('reopen', None)
        if reopen is not None:
            if self.context.reopen(self.user):
                response.addNotification(_("You have reopened this request."))
                modified_fields.add('status')

        if len(modified_fields) > 0:
            notify(SQLObjectModifiedEvent(
                self.context, ticket_unmodified, list(modified_fields)))

    @property
    def can_reject(self):
        """Whether the current user can reject this ticket."""
        return self.user and self.context.canReject(self.user)

class TicketSubscriptionView(LaunchpadView):
    """View for subscribing and unsubscribing from a ticket."""

    def initialize(self):
        if not self.user or self.request.method != "POST":
            # No post, nothing to do
            return

        ticket_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        modified_fields = set()

        form = self.request.form
        response = self.request.response
        # establish if a subscription form was posted
        newsub = form.get('subscribe', None)
        if newsub is not None:
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                response.addNotification(
                    _("You have subscribed to this request."))
                modified_fields.add('subscribers')
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                response.addNotification(
                    _("You have unsubscribed from this request."))
                modified_fields.add('subscribers')
            response.redirect(canonical_url(self.context))

    @property
    def subscription(self):
        """establish if this user has a subscription"""
        if self.user is None:
            return False
        return self.context.isSubscribed(self.user)


class TicketAddView(LaunchpadFormView):
    """Multi-page add view.

    The user enters first his ticket summary and then he his shown a list
    of similar results before adding the ticket.
    """
    label = _('Make a support request')

    schema = ITicket

    field_names = ['title', 'description']

    custom_widget('title', TextWidget, displayWidth=40)

    search_template = ViewPageTemplateFile('../templates/ticket-add-search.pt')

    add_template = ViewPageTemplateFile('../templates/ticket-add.pt')

    template = search_template

    _MAX_SIMILAR_TICKETS = 10

    # Do not autofocus the title widget
    initial_focus_widget = None

    def setUpWidgets(self):
        # Only setup the widgets that needs validation
        if not self.add_action.submitted():
            fields = self.form_fields.select('title')
        else:
            fields = self.form_fields
        self.widgets = form.setUpWidgets(
            fields, self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    def validate(self, data):
        """Validate hook."""
        if 'title' not in data:
            self.setFieldError(
                'title',_('You must enter a summary of your problem.'))
        if self.widgets.get('description'):
            if 'description' not in data:
                self.setFieldError(
                    'description', _('You must provide details about your '
                                     'problem.'))

    @action(_('Continue'))
    def continue_action(self, action, data):
        """Search for tickets similar to the entered summary."""
        # If the description widget wasn't setup, add it here
        if self.widgets.get('description') is None:
            self.widgets += form.setUpWidgets(
                self.form_fields.select('description'), self.prefix,
                 self.context, self.request, data=self.initial_values,
                 ignore_request=False)

        tickets = self.context.findSimilarTickets(data['title'])
        self.searchResults = tickets[:self._MAX_SIMILAR_TICKETS]

        return self.add_template()

    def handleAddError(self, action, data, errors):
        """Handle errors on new ticket creation submission. Either redirect
        to the search template when the summary is missing or delegate to
        the continue action handler to do the search.
        """
        if 'title' not in data:
            # Remove the description widget
            self.widgets = form.Widgets(
                [(True, self.widgets['title'])], len(self.prefix)+1)
            return self.search_template()
        return self.continue_action.success(data)

    # XXX flacoste 2006/07/26 We use the method here instead of
    # using the method name 'handleAddError' because of Zope issue 573
    # which is fixed in 3.3.0b1 and 3.2.1
    @action(_('Add'), failure=handleAddError)
    def add_action(self, action, data):
        ticket = self.context.newTicket(self.user, data['title'],
                                        data['description'])

        # XXX flacoste 2006/07/25 This should be moved to newTicket().
        notify(SQLObjectCreatedEvent(ticket))

        self.request.response.redirect(canonical_url(ticket))
        return ''


class TicketChangeStatusView(LaunchpadFormView):
    """View for changing a ticket status."""
    schema = ITicketChangeStatusForm

    def validate(self,data):
        if data.get('status') == self.context.status:
            self.setFieldError(
                'status', _("You didn't change the status."))
        if 'message' not in data:
            self.setFieldError(
                'message', _('You must provide an explanation message.'))

    @property
    def initial_values(self):
        return {'status': self.context.status}

    @action(_('Change Status'))
    def change_status_action(self, action, data):
        self.context.setStatus(self.user, data['status'], data['message'])
        self.request.response.addNotification(
            _('Request status updated.'))
        self.request.response.redirect(canonical_url(self.context))
        return ''


class TicketEditView(LaunchpadEditFormView):

    schema = ITicket
    label = 'Edit request'
    field_names = ["title", "description", "sourcepackagename", "priority",
                   "assignee", "whiteboard"]

    custom_widget('title', TextWidget, displayWidth=40)
    custom_widget('whiteboard', TextAreaWidget, height=5)

    def setUpFields(self):
        """Select the subset of fields to display.

        - Exclude the sourcepackagename field when ticket doesn't have a
        distribution.
        - Exclude fields that the user doesn't have permission to modify.
        """
        LaunchpadEditFormView.setUpFields(self)

        if self.context.distribution is None:
            self.form_fields = self.form_fields.omit("sourcepackagename")

        fields_with_permission = []
        for field in self.form_fields:
            if form.canWrite(self.context, field):
                fields_with_permission.append(field.__name__)
        self.form_fields = self.form_fields.select(*fields_with_permission)

    @action(u"Continue", name="change")
    def change_action(self, action, data):
        self.updateContextFromData(data)
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


class TicketRejectView(LaunchpadFormView):
    """View for rejecting a ticket."""
    schema = ITicketChangeStatusForm
    field_names = ['message']

    def validate(self,data):
        if 'message' not in data:
            self.setFieldError(
                'message', _('You must provide an explanation message.'))

    @action(_('Reject'))
    def reject_action(self, action, data):
        self.context.reject(self.user, data['message'])
        self.request.response.addNotification(
            _('You have rejected this request.'))
        self.request.response.redirect(canonical_url(self.context))
        return ''

    def initialize(self):
        if not self.context.canReject(self.user):
            self.request.response.addErrorNotification(
                _('Only support contacts and administrators can reject a '
                  'request.'))
            self.request.response.redirect(canonical_url(self.context))
            return
        LaunchpadFormView.initialize(self)


class TicketContextMenu(ContextMenu):

    usedfor = ITicket
    links = [
        'edit',
        'reject',
        'changestatus',
        'history',
        'subscription',
        'linkbug',
        'unlinkbug',
        'makebug',
        ]

    def initialize(self):
        self.has_bugs = bool(self.context.bugs)

    def edit(self):
        text = 'Edit Request'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def changestatus(self):
        return Link('+change-status', _('Change Status'), icon='edit')

    def reject(self):
        enabled = self.user is not None and self.context.canReject(self.user)
        text = 'Reject Request'
        return Link('+reject', text, icon='edit', enabled=enabled)

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


class TicketSetContextMenu(ContextMenu):

    usedfor = ITicketSet
    links = ['findproduct', 'finddistro']

    def findproduct(self):
        text = 'Find Upstream Product'
        return Link('/products', text, icon='search')

    def finddistro(self):
        text = 'Find Distribution'
        return Link('/distros', text, icon='search')

