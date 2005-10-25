# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Sprint views."""

__metaclass__ = type
__all__ = [
    'SprintFacets',
    'SprintContextMenu',
    'SprintSetContextMenu',
    'SprintSetNavigation',
    'SprintView',
    'SprintAddView',
    'SprintEditView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, ILaunchBag, ISprint, ISprintSet)

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.lp.dbschema import SprintSpecificationStatus

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation,
    StandardLaunchpadFacets)


class SprintFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an ISprint."""

    usedfor = ISprint
    enable_only = ['overview',]


class SprintContextMenu(ContextMenu):

    usedfor = ISprint
    links = ['attendance', 'edit', 'approved', 'all', 'declined', 'submitted']

    def attendance(self):
        text = 'Register Attendance'
        return Link('+attend', text, icon='add')

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    def approved(self):
        text = 'Approved specs'
        return Link('.', text, icon='info')

    def all(self):
        text = 'All specs'
        return Link('./?show=all', text, icon='info')

    def declined(self):
        text = 'Declined specs'
        return Link('./?show=declined', text, icon='info')

    def submitted(self):
        text = 'Submitted specs'
        return Link('./?show=submitted', text, icon='info')


class SprintSetNavigation(GetitemNavigation):

    usedfor = ISprintSet


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
        self._sprint_specs = None
        self.show = request.form.get('show', None)
        self.listing_detailed = True
        self.listing_compact = False
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

    def attendance(self):
        """establish if this user is attending"""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None

    def spec_links(self):
        """list all of the SprintSpecifications appropriate for this
        view."""
        if self._sprint_specs is not None:
            return self._sprint_specs
        if self.show is None:
            self._sprint_specs = self.context.specificationLinks(
                status=SprintSpecificationStatus.APPROVED)
        elif self.show == 'all':
            self._sprint_specs = self.context.specificationLinks()
        elif self.show == 'declined':
            self._sprint_specs = self.context.specificationLinks(
                status=SprintSpecificationStatus.DECLINED)
        elif self.show == 'submitted':
            self._sprint_specs = self.context.specificationLinks(
                status=SprintSpecificationStatus.SUBMITTED)
        if len(self._sprint_specs) > 5:
            self.listing_detailed = False
            self.listing_compact = True
        return self._sprint_specs


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

