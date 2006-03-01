# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Sprint views."""

__metaclass__ = type
__all__ = [
    'SprintFacets',
    'SprintOverviewMenu',
    'SprintSpecificationsMenu',
    'SprintSetContextMenu',
    'SprintSetNavigation',
    'SprintView',
    'SprintAddView',
    'SprintEditView',
    'SprintTopicSetView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchBag, ISprint, ISprintSet

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.lp.dbschema import SprintSpecificationStatus

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation,
    ApplicationMenu, StandardLaunchpadFacets)


class SprintFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an ISprint."""

    usedfor = ISprint
    enable_only = ['overview', 'specifications']

    def specifications(self):
        target = '+specs'
        text = 'Specifications'
        summary = 'Topics for discussion at %s' % self.context.title
        return Link(target, text, summary)


class SprintOverviewMenu(ApplicationMenu):

    usedfor = ISprint
    facet = 'overview'
    links = ['attendance', 'registration', 'edit']

    def attendance(self):
        text = 'Register Yourself'
        summary = 'Register as an attendee of the meeting'
        return Link('+attend', text, summary, icon='add')

    def registration(self):
        text = 'Register Someone'
        summary = 'Register someone else to attend the meeting'
        return Link('+register', text, summary, icon='add')

    def edit(self):
        text = 'Edit Details'
        summary = 'Modify the meeting description, dates or title'
        return Link('+edit', text, summary, icon='edit')


class SprintSpecificationsMenu(ApplicationMenu):

    usedfor = ISprint
    facet = 'specifications'
    links = ['assignments', 'deferred', 'settopics']

    def assignments(self):
        text = 'Assignments'
        summary = 'View the specification assignments'
        return Link('+assignments', text, summary, icon='info')

    def deferred(self):
        text = 'Deferred Topics'
        summary = 'Show topics that were not accepted for discussion'
        return Link('+specs?show=deferred', text, summary, icon='info')

    def settopics(self):
        text = 'Set Topics'
        summary = 'Approve or defer topics for discussion'
        return Link('+settopics', text, summary, icon='edit')


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
        if self._count is None:
            # creating list of spec links will set self._count as a
            # sideeffect
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


class SprintTopicSetView:

    def __init__(self, context, request):
        """A custom little view class to process the results of this unusual
        page. It is unusual because we want to display multiple objects with
        checkboxes, then process the selected items, which is not the usual
        add/edit metaphor."""
        self.context = context
        self.request = request
        self.process_status = None
        self._count = None
        self._speclinks = None

    @property
    def speclinks(self):
        """Return the specification links with SUBMITTED status this sprint.

        For the moment, we just filter the list in Python.
        """
        if self._speclinks is not None:
            return self._speclinks
        speclinks = list(self.context.specificationLinks())
        self._speclinks = [speclink for speclink in speclinks
            if speclink.status == SprintSpecificationStatus.SUBMITTED]
        return self._speclinks

    @property
    def count(self):
        """Return the number of specifications to be listed."""
        if self._count is not None:
            return self._count
        self._count = len(self.speclinks)
        return self._count

    def process_form(self):
        """Largely copied from webapp/generalform.py, without the
        schema processing bits because we are not rendering the form in the
        usual way. Instead, we are creating our own form in the page
        template and interpreting it here.
        """

        if self.process_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.process_status

        if 'cancel' in self.request:
            self.process_status = 'Cancelled'
            self.request.response.redirect(canonical_url(self.context)+'/+specs')
            return self.process_status

        if "FORM_SUBMIT" not in self.request:
            self.process_status = ''
            return self.process_status

        if self.request.method == 'POST':
            if 'speclink' not in self.request:
                self.process_status = ('Please select specifications '
                                       'to accept or decline.')
                return self.process_status
            # determine if we are accepting or declining
            if self.request.form.get('FORM_SUBMIT', None) == 'Accept':
                action = 'Accepted'
            else:
                action = 'Declined'

        selected_specs = self.request['speclink']
        if isinstance(selected_specs, unicode):
            # only a single item was selected, but we want to deal with a
            # list for the general case, so convert it to a list
            selected_specs = [selected_specs,]
        
        number_done = 0
        for sprintspec_id in selected_specs:
            sprintspec = self.context.getSpecificationLink(sprintspec_id)
            if action == 'Accepted':
                sprintspec.status = SprintSpecificationStatus.CONFIRMED
            else:
                sprintspec.status = SprintSpecificationStatus.DEFERRED
            number_done += 1

        self.process_status = '%s %d specification(s).' % (action, number_done)

        if self.count == 0:
            # they are all done, so redirect back to the spec listing page
            self.request.response.redirect(canonical_url(self.context)+'/+specs')

        return self.process_status

