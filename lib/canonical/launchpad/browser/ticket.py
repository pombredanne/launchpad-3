# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket views."""

__metaclass__ = type

__all__ = [
    'TicketSetNavigation',
    'TicketView',
    'TicketAddView',
    'TicketEditView',
    'TicketContextMenu',
    'TicketSetContextMenu'
    ]

from zope.component import getUtility

from canonical.lp.dbschema import TicketStatus

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, ILaunchBag, ITicket, ITicketSet)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ContextMenu, Link, canonical_url,
    enabled_with_permission, GetitemNavigation)


class TicketSetNavigation(GetitemNavigation):

    usedfor = ITicketSet


class TicketView:

    __used_for__ = ITicket

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.is_owner = False
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this request.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this request.")

        # establish if the user is trying to reject the ticket
        reject = request.form.get('reject', None)
        if reject is not None and self.user and request.method == 'POST':
            if self.context.reject(self.user):
                self.notices.append("You have rejected this request.")

        # establish if the user is trying to reopen the ticket
        reopen = request.form.get('reopen', None)
        if reopen is not None and self.user and request.method == 'POST':
            if self.context.reopen(self.user):
                self.notices.append("You have reopened this request.")

        # see if this is the creator, or not
        if self.user == self.context.owner:
            self.is_owner = True

        # see if there has been an attempt to create a bug
        makebug = request.form.get('makebug', None)
        if makebug is not None and self.user is not None and \
            request.method == 'POST':
            if self.context.bugs:
                # we can't make a bug when we have linked bugs
                self.notices.append('You cannot create a bug report from '
                    'a support request that already has bugs linked to it.')
            else:
                bug = self.context.target.newBug(self.user,
                    self.context.title, self.context.description)
                self.context.linkBug(bug)
                bug.subscribe(self.context.owner)
                self.notices.append('Thank you! Bug #%d created.' % bug.id)

    @property
    def subscription(self):
        """establish if this user has a subscription"""
        if self.user is None:
            return False
        return person_has_subscription(self.user, self.context)


def person_has_subscription(person, ticket):
    """Return whether the person has a subscription on the ticket.

    XXX: refactor this into a method on ITicket.
    Steve Alexander, 2005-09-27
    """
    assert person is not None
    for subscription in ticket.subscriptions:
        if subscription.person.id == person.id:
            return True
    return False


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


class TicketContextMenu(ContextMenu):

    usedfor = ITicket
    links = [
        'edit',
        'editsourcepackage',
        'editpriority',
        'reject',
        'reopen',
        'history',
        'subscription',
        'linkbug',
        'unlinkbug',
        'makebug',
        'seeothers',
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
        text = 'Edit Source Package'
        return Link('+sourcepackage', text, icon='edit', enabled=enabled)

    def editpriority(self):
        text = 'Edit Priority & Assignee'
        return Link('+editpriority', text, icon='edit',
                    enabled=self.is_not_resolved)

    def reject(self):
        text = 'Reject Request'
        return Link('+reject', text, icon='edit',
                    enabled=self.context.can_be_rejected)

    def reopen(self):
        text = 'Reopen Request'
        return Link('+reopen', text, icon='edit',
                    enabled=self.context.can_be_reopened)

    def history(self):
        text = 'Show History'
        return Link('+history', text, icon='list',
                    enabled=bool(self.context.reopenings))

    def subscription(self):
        if (self.user is not None and
            person_has_subscription(self.user, self.context)):
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

    def seeothers(self):
        text = 'Other Support Requests'
        linktarget = '%s/%s' % (canonical_url(self.context.target), '+tickets')
        return Link(linktarget, text, icon='ticket')

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

