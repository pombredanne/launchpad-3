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
    links = ['attendance', 'workload',
             'approved', 'all', 'declined', 'submitted',
             'table', 'edit']

    def attendance(self):
        text = 'Register Attendance'
        return Link('+attend', text, icon='add')

    def workload(self):
        text = 'Show Workload'
        return Link('+workload', text, icon='info')

    def table(self):
        text = 'Work table'
        return Link('+table', text, icon='info')

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
        self._sprint_spec_links = None
        self._workload = None
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
            self._sprint_spec_links = self.context.specificationLinks(
                status=SprintSpecificationStatus.APPROVED)
        elif self.show == 'all':
            self._sprint_spec_links = self.context.specificationLinks()
        elif self.show == 'declined':
            self._sprint_spec_links = self.context.specificationLinks(
                status=SprintSpecificationStatus.DECLINED)
        elif self.show == 'submitted':
            self._sprint_spec_links = self.context.specificationLinks(
                status=SprintSpecificationStatus.SUBMITTED)
        if len(self._sprint_spec_links) > 5:
            self.listing_detailed = False
            self.listing_compact = True
        return self._sprint_spec_links

    def specifications(self):
        return [sl.specification for sl in self.spec_links()]

    def workload(self):
        """Return a structure that lists people, and for each person, the
        specs at this conference that for which they are the approver, the
        assignee or the drafter."""

        if self._workload is not None:
            return self._workload

        class Group:
            def __init__(self, person):
                self.person = person
                self.approver = []
                self.drafter = []
                self.assignee = []

        class Report:
            def __init__(self):
                self.contents = {}

            def _getGroup(self, person):
                group = self.contents.get(person.name, None)
                if group is not None:
                    return group
                group = Group(person)
                self.contents[person.name] = group
                return group

            def process(self, spec):
                """Make sure that this Report.contents has a Group for each
                person related to the spec, and that Group has the spec in
                the relevant list.
                """
                if spec.assignee is not None:
                    self._getGroup(spec.assignee).assignee.append(spec)
                if spec.drafter is not None:
                    self._getGroup(spec.drafter).drafter.append(spec)
                if spec.approver is not None:
                    self._getGroup(spec.approver).approver.append(spec)

            def results(self):
                return [self.contents[key]
                    for key in sorted(self.contents.keys())]

        report = Report()
        for spec_link in self.spec_links():
            report.process(spec_link.specification)

        self._workload = report.results()
        return self._workload


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

