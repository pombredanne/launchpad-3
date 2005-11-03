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
    links = ['attendance', 'registration',
             'all', 'confirmed', 'deferred', 'submitted',
             'workload', 'table', 'edit']

    def attendance(self):
        text = 'Register Yourself'
        return Link('+attend', text, icon='add')

    def registration(self):
        text = 'Register Someone'
        return Link('+register', text, icon='add')

    def workload(self):
        text = 'Show Workload'
        return Link('+workload', text, icon='info')

    def table(self):
        text = 'Assignments Table'
        return Link('+specstable', text, icon='info')

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    def confirmed(self):
        text = 'Show confirmed'
        return Link('.', text, icon='info')

    def all(self):
        text = 'Show all'
        return Link('./?show=all', text, icon='info')

    def deferred(self):
        text = 'Show deferred'
        return Link('./?show=deferred', text, icon='info')

    def submitted(self):
        text = 'Show new'
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
        self._sprint_spec_links = None
        self._count = None
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
        if self._sprint_spec_links is not None:
            return self._sprint_spec_links
        if self.show is None:
            spec_links = self.context.specificationLinks(
                status=SprintSpecificationStatus.CONFIRMED)
        elif self.show == 'all':
            spec_links = self.context.specificationLinks()
        elif self.show == 'deferred':
            spec_links = self.context.specificationLinks(
                status=SprintSpecificationStatus.DEFERRED)
        elif self.show == 'submitted':
            spec_links = self.context.specificationLinks(
                status=SprintSpecificationStatus.SUBMITTED)
        self._sprint_spec_links = [
            link for link in spec_links if link.specification.is_incomplete]
        self._count = len(self._sprint_spec_links)
        if self._count > 5:
            self.listing_detailed = False
            self.listing_compact = True
        return self._sprint_spec_links

    @property
    def count(self):
        if self._count is not None:
            return self._count
        # creating list of spec links will set self._count
        spec_links = self.spec_links()
        return self._count

    @property
    def specs(self):
        return [sl.specification for sl in self.spec_links()]


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

