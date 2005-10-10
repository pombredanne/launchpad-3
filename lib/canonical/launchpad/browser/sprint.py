# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Sprint views."""

__metaclass__ = type
__all__ = [
    'SprintSetNavigation',
    'SprintContextMenu',
    'SprintSetContextMenu',
    'SprintView',
    'SprintAddView',
    'SprintEditView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, ILaunchBag, ISprint, ISprintSet)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation)


class SprintSetNavigation(GetitemNavigation):

    usedfor = ISprintSet


class SprintContextMenu(ContextMenu):

    usedfor = ISprint
    links = ['edit']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')


class SprintSetContextMenu(ContextMenu):

    usedfor = ISprintSet
    links = ['new']

    def new(self):
        text = 'Register New Meeting'
        return Link('+new', text, icon='add')


class SprintView:

    __used_for__ = ISprint

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.review = None
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this spec.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this spec.")


    @property
    def attendance(self):
        """establish if this user is attending"""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None

    def categories(self):
        """This organises the specifications related to this target by
        "category", where a category corresponds to a particular spec
        status. It also determines the order of those categories, and the
        order of the specs inside each category. This is used for the +specs
        view.
        """
        categories = {}
        specs = self.context.specifications
        for spec in specs:
            if categories.has_key(spec.status):
                category = categories[spec.status]
            else:
                category = {}
                category['status'] = spec.status
                category['specs'] = []
                categories[spec.status] = category
            category['specs'].append(spec)
        categories = categories.values()
        return sorted(categories, key=lambda a: a['status'].value)


class SprintAddView(SQLObjectAddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, owner, name, title, time_zone, time_starts, time_ends,
        summary=None, home_page=None):
        """Create a new Sprint."""
        # clean up name
        name = name.strip().lower()
        sprint = getUtility(ISprintSet).new(owner, name, title, 
            time_zone, time_starts, time_ends, summary=summary,
            home_page=home_page)
        self._nextURL = canonical_url(sprint)
        return sprint

    def nextURL(self):
        return self._nextURL


class SprintEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))

