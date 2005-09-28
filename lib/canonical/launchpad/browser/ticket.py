# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket views."""

__metaclass__ = type

__all__ = [
    'TicketView',
    'TicketAddView',
    'TicketEditView',
    ]

from zope.component import getUtility

from canonical.lp.dbschema import TicketStatus

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, ILaunchBag, ITicket, ITicketSet, IBugSet)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, canonical_url)


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
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None


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

